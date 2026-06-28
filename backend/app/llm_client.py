"""LLM compiler client — NL operating policy → typed policy IR. Env-driven, stdlib-only.

The architectural line (docs/DESIGN_what_if_sequential.md §1): the LLM is a COMPILER, not an oracle.
It turns a human-language policy into the schema-validated IR the deterministic engine already runs —
it NEVER predicts numbers or outcomes. So this module:
  * targets an OpenAI-compatible endpoint (LM Studio by default) via PRISM_LLM_BASE / PRISM_LLM_MODEL;
  * asks for STRUCTURED OUTPUT (json_schema) — which is exactly why a small local model (qwen3-8b /
    gemma) can do this reliably (§6): a narrow schema, not open-ended reasoning;
  * STRICTLY validates/normalizes whatever comes back (bad ops/values dropped, ``by`` clamped) before
    it ever reaches the engine or the user;
  * FAILS OBSERVABLY — on any error it returns ``{ok: False, error}`` and bumps a counter exposed at
    /api/llm/health. It NEVER fabricates a template IR and passes it off as a real compile (the
    explicit anti-pattern in docs/DEMANDS.md §1).

The compiled IR is a SUGGESTION for the human to confirm/edit; the numbers still come only from the
deterministic policy engine. (Stdlib urllib keeps this dependency-free; the route is a sync def so
FastAPI runs the blocking call in a threadpool.)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import re
import urllib.error
import urllib.request

# frozen, versioned LLM-output fixtures (RESEARCH_axiom_gain §7): the benchmark records each call here
# so re-scoring is byte-reproducible and never calls the model live.
_FIX = pathlib.Path(__file__).resolve().parent.parent / "benchmark_fixtures" / "llm_cache.json"

_OPS = {">=", "<=", ">", "<"}
_ACTIONS = {"shift", "pulse"}
_TIMEOUT = 90

# observable health (no persistence — process-lifetime counters)
_stats = {"compile_calls": 0, "compile_failures": 0, "last_error": None, "last_model": None}


def _base() -> str:
    # explicit 127.0.0.1 (not "localhost") to dodge localhost→IPv6(::1) resolution when LM Studio
    # listens on IPv4 only. Override with PRISM_LLM_BASE.
    return os.environ.get("PRISM_LLM_BASE", "http://127.0.0.1:1234/v1").rstrip("/")


def _headers(extra: dict | None = None) -> dict:
    # local LM Studio needs no key; a remote OpenAI-compatible endpoint (e.g. Volcengine Ark) needs a Bearer
    # token — supplied out-of-band via PRISM_LLM_KEY so no secret is ever committed.
    h = {"Content-Type": "application/json", **(extra or {})}
    key = os.environ.get("PRISM_LLM_KEY")
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def _post(path: str, payload: dict, timeout: int = _TIMEOUT) -> dict:
    req = urllib.request.Request(
        _base() + path, data=json.dumps(payload).encode("utf-8"),
        headers=_headers(), method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(path: str, timeout: int = 5) -> dict:
    req = urllib.request.Request(_base() + path, headers=_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _chat_post(payload: dict, timeout: int) -> dict:
    """POST /chat/completions; if the provider rejects response_format with a 400 (some models — e.g. Ark's
    deepseek-v4-pro — support NO response_format, neither json_schema nor json_object), retry ONCE without it.
    The task prompt already embeds the JSON shape, so _extract_json still recovers the answer — a prompt-JSON
    fallback (a disclosed construction difference vs strict-schema models, not a silent one)."""
    try:
        return _post("/chat/completions", payload, timeout=timeout)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 — best-effort body read to decide the fallback
            pass
        if e.code == 400 and "response_format" in body and "response_format" in payload:
            return _post("/chat/completions", {k: v for k, v in payload.items() if k != "response_format"}, timeout=timeout)
        raise


def list_models() -> list[str]:
    return [m.get("id", "") for m in (_get("/models").get("data") or [])]


def resolve_model() -> str:
    """Configured model, else the first non-embedding model the server reports, else a placeholder."""
    env = os.environ.get("PRISM_LLM_MODEL")
    if env:
        return env
    try:
        for mid in list_models():
            if mid and "embed" not in mid.lower():
                return mid
    except Exception:  # noqa: BLE001 — health is best-effort
        pass
    return "local-model"


def health() -> dict:
    base = _base()
    try:
        models = list_models()
        reachable = True
    except Exception as e:  # noqa: BLE001
        models, reachable = [], False
        _stats["last_error"] = f"models probe: {e}"
    return {
        "reachable": reachable, "base_url": base, "model": resolve_model() if reachable else os.environ.get("PRISM_LLM_MODEL", ""),
        "models": models, **{k: _stats[k] for k in ("compile_calls", "compile_failures", "last_error")},
    }


def normalize_rules(obj: dict, lo: float | None = None, hi: float | None = None) -> list[dict]:
    """Strictly coerce a model's JSON into valid engine rules. Drop anything malformed; cap at 4.

    Every rule must have a known op, a known action, a FINITE numeric trigger, and a FINITE ``by``.
    ``by`` is clamped to [-1, 1] (a fraction of the value's span); when the attribute's [lo, hi] is
    given, the trigger ``value`` is clamped into range too. Non-finite (NaN/±Infinity) values are
    DROPPED, never silently turned into a maximal shift — failing observably beats a plausible lie.
    """
    out: list[dict] = []
    for r in (obj.get("rules") or [])[:8]:
        try:
            when = r.get("when") or {}
            do = r.get("do") or {}
            op = str(when.get("op", ">="))
            action = str(do.get("action", "shift"))
            if op not in _OPS or action not in _ACTIONS:
                continue
            value = float(when.get("value"))
            by = float(do.get("by"))
            if not (math.isfinite(value) and math.isfinite(by)):  # NaN / ±Infinity → drop, don't guess
                continue
            if lo is not None and hi is not None:
                value = max(float(lo), min(float(hi), value))  # trigger must sit inside the attr range
            by = max(-1.0, min(1.0, by))
            rule = {"when": {"op": op, "value": value}, "do": {"action": action, "by": by}}
            note = r.get("note")
            if isinstance(note, str) and note.strip():
                rule["note"] = note.strip()[:120]
            out.append(rule)
        except (TypeError, ValueError):
            continue
        if len(out) >= 4:
            break
    return out


def _extract_json(text: str) -> str:
    """Strip reasoning ``<think>…</think>`` blocks and ```` ```json ```` fences some models add, then
    fall back to the outermost {…} — so a clean-JSON contract survives a chatty model, while genuine
    non-JSON still raises downstream (the observable-failure contract holds)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE).strip()
    if not text.startswith("{"):
        i, j = text.find("{"), text.rfind("}")
        if i != -1 and j > i:
            text = text[i : j + 1]
    return text


_SCHEMA = {
    "name": "policy_ir",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "when": {
                            "type": "object",
                            "properties": {"op": {"type": "string", "enum": [">=", "<=", ">", "<"]}, "value": {"type": "number"}},
                            "required": ["op", "value"],
                        },
                        "do": {
                            "type": "object",
                            "properties": {"action": {"type": "string", "enum": ["shift", "pulse"]}, "by": {"type": "number"}},
                            "required": ["action", "by"],
                        },
                        "note": {"type": "string"},
                    },
                    "required": ["when", "do"],
                },
            }
        },
        "required": ["rules"],
    },
}


def _system_prompt(attr: dict) -> str:
    lo, hi = (list(attr.get("range", [0, 100])) + [0, 1])[:2]
    th = attr.get("threshold") or {}
    label = attr.get("label", attr.get("name", "target"))
    unit = attr.get("unit", "")
    return (
        "You COMPILE a natural-language operating policy into a strict JSON IR. You do NOT predict "
        "numbers, trajectories, or outcomes — you only translate the user's rules into the schema.\n"
        f"Target quantity: '{label}'{f' ({unit})' if unit and unit != '—' else ''}, range [{lo}, {hi}]"
        + (f", warn={th['warn']}" if th.get('warn') is not None else "")
        + (f", limit={th['limit']}" if th.get('limit') is not None else "")
        + ".\n"
        "Each rule: when the target's current value satisfies `when` (op one of >=,<=,>,<; `value` is "
        f"an ABSOLUTE value within [{lo}, {hi}]), apply `do`: action 'shift' = a persistent setpoint "
        "change held thereafter; 'pulse' = a one-time change. `by` is a SIGNED FRACTION OF THE RANGE "
        "SPAN (e.g. -0.15 = lower by 15% of the span; +0.2 = raise by 20%). Use 1–3 rules. Output ONLY "
        "JSON matching the schema, no prose.\n"
        'Example — "if it gets near the limit, ease off ~15%": '
        f'{{"rules":[{{"when":{{"op":">=","value":{th.get("warn", round((lo+hi)/2,1))}}},'
        '"do":{"action":"shift","by":-0.15},"note":"near warn → ease off"}]}'
    )


def _fix_load() -> dict:
    try:
        return json.loads(_FIX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _fix_save(cache: dict) -> None:
    _FIX.parent.mkdir(parents=True, exist_ok=True)
    _FIX.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def _fix_key(model: str, system: str, user: str, schema: dict) -> str:
    blob = json.dumps([model, system, user, schema], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _json_schema_block(schema: dict) -> dict:
    """Normalize a caller's schema into LM Studio's ``response_format.json_schema`` block. LM Studio requires
    a ``name``; a BARE JSON Schema (just type/properties) 400s. Callers are inconsistent — some pass a
    pre-wrapped ``{name, schema, ...}`` (e.g. benchmark), others a bare schema (e.g. compile). A wrapper
    passes through as-is; a bare schema is wrapped with a name. The fixture key hashes the ORIGINAL ``schema``
    arg (not this block), so this normalization never invalidates existing fixtures."""
    return schema if ("schema" in schema and "name" in schema) else {"name": "response", "schema": schema}


def structured_complete(system: str, user: str, schema: dict, model: str | None = None, *,
                        use_fixture: bool = True, allow_live: bool = True, max_tokens: int = 700,
                        timeout: int = _TIMEOUT) -> dict:
    """Generic structured-output completion with token instrumentation + a frozen fixture cache.

    Returns {ok, content (raw JSON str), usage {in,out}, model, cached} or {ok: False, error}. With a
    fixture hit, NO live call is made (deterministic re-runs). Set allow_live=False to require fixtures.

    ``max_tokens`` caps the completion (default 700 — fits the logistics task; raise it for tasks with a
    larger structured answer so the JSON is not truncated). NOTE: max_tokens is NOT part of the fixture key
    (which hashes model/system/user/schema), so two calls that differ ONLY in max_tokens share a cache entry
    — re-populate with use_fixture=False to refresh after changing it.
    """
    mdl = model or resolve_model()
    key = _fix_key(mdl, system, user, schema)
    if use_fixture:
        hit = _fix_load().get(key)
        if hit:
            return {"ok": True, "content": hit["content"], "usage": hit["usage"], "model": hit["model"], "cached": True}
    if not allow_live:
        return {"ok": False, "error": "no fixture and live disabled", "cached": False}
    payload = {
        "model": mdl,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0, "max_tokens": max_tokens,
        "response_format": {"type": "json_schema", "json_schema": _json_schema_block(schema)},
    }
    try:
        resp = _chat_post(payload, timeout)
        _msg = (resp.get("choices") or [{}])[0].get("message", {})
        _raw = _msg.get("content") or ""
        if not _raw.strip():  # some reasoning models (e.g. qwen3.6 in LM Studio) route the json_schema answer
            _raw = _msg.get("reasoning_content") or ""  # into reasoning_content, leaving content empty
        content = _extract_json(_raw)
        usage = resp.get("usage") or {}
        u = {"in": int(usage.get("prompt_tokens", 0)), "out": int(usage.get("completion_tokens", 0))}
        rmodel = resp.get("model", mdl)
        cache = _fix_load()
        cache[key] = {"content": content, "usage": u, "model": rmodel}
        _fix_save(cache)
        return {"ok": True, "content": content, "usage": u, "model": rmodel, "cached": False}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError, KeyError) as e:
        return {"ok": False, "error": str(e), "cached": False}


def compile_policy(attr: dict, nl: str) -> dict:
    """NL → validated policy IR. Returns {ok, rules, model, raw} or {ok: False, error}. Observable."""
    _stats["compile_calls"] += 1
    model = resolve_model()
    _stats["last_model"] = model
    lo, hi = (list(attr.get("range", [0, 100])) + [0, 1])[:2]
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": _system_prompt(attr)}, {"role": "user", "content": nl.strip()[:600]}],
        "temperature": 0,
        "max_tokens": 600,
        "response_format": {"type": "json_schema", "json_schema": _SCHEMA},
    }
    try:
        resp = _post("/chat/completions", payload)
        content = (resp.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        obj = json.loads(_extract_json(content))
        rules = normalize_rules(obj, float(lo), float(hi))
        if not rules:
            raise ValueError("model returned no usable rules")
        return {"ok": True, "rules": rules, "model": resp.get("model", model), "raw": content[:1000]}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        _stats["compile_failures"] += 1
        _stats["last_error"] = f"LLM unreachable: {e}"
        return {"ok": False, "error": f"LLM 不可达({_base()}):{e}"}
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        _stats["compile_failures"] += 1
        _stats["last_error"] = f"bad compile: {e}"
        return {"ok": False, "error": f"LLM 输出无法解析为合法 IR:{e}"}
