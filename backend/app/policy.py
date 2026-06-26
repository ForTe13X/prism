"""Sequential what-if / policy comparison (decision-support) — deterministic, domain-agnostic.

Extends the single-shot simulation (simulation.py) with CLOSED-LOOP policies. A *policy* is a small
typed IR of conditional rules — "when the target crosses a trigger, nudge its setpoint" (latching
shift) or "give it a one-time kick" (pulse) — plus optional fixed-frame events. The engine rolls each
policy K deterministic times under the spec's dynamics, forms an uncertainty band, and COMPARES
policies by ROBUSTNESS (breach rate + worst-case terminal), then runs a SENSITIVITY pass under
perturbed assumptions and reports whether the ranking holds.

Design anchor: docs/DESIGN_what_if_sequential.md. This is the deterministic core; an LLM (later, P6)
may compile NL → this same IR and explain results, but NEVER invents numbers — every trajectory comes
from this engine. Fair comparison uses COMMON RANDOM NUMBERS: all policies share the same per-roll
shock sequence, so differences are causal, not luck. No random, no clock → byte-reproducible.

This module is self-contained (its own deterministic hash; imports only specs_loader.load_spec) and
mirrors simulation.py's baseline seed so the two views agree on the same row's starting value.
"""
from __future__ import annotations

import hashlib
import math
from statistics import median

from .specs_loader import load_spec

_NUMERIC = {"metric", "gauge", "timeseries"}
_ROLLS = 9
_MAX_HORIZON = 96
_MAX_POLICIES = 6
_MAX_RULES = 8
_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


def _u(*parts: object) -> float:
    """Stable float in [0,1] from a seed (sha256 → first 8 hex digits). No random, no clock."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def _span(attr: dict) -> tuple[float, float, float]:
    lo, hi = (list(attr.get("range", [0, 100])) + [0, 1])[:2]
    return float(lo), float(hi), (float(hi) - float(lo)) or 1.0


def _baseline_value(spec_id: str, etype: str, attr: dict, idx: int) -> float:
    # SAME seed as simulation._baseline_value so single-shot sim and policy view share a starting value
    lo, _hi, span = _span(attr)
    return lo + span * _u(spec_id, etype, attr["name"], idx, "baseline")


def _dynamics(attr: dict, override: dict | None = None) -> dict:
    d = dict(attr.get("dynamics") or {})
    o = override or {}
    lo, hi, span = _span(attr)

    def pick(key: str, default: float) -> float:
        return float(o[key]) if key in o and o[key] is not None else float(d.get(key, default))

    return {
        "model": str(d.get("model", "mean_revert")),
        "rate": max(0.0, min(1.0, pick("rate", 0.15))),
        "trend": pick("trend", 0.0) * span,
        "vol": max(0.0, pick("volatility", 0.12)) * span,
        "lo": lo, "hi": hi, "span": span,
    }


def _norm_rule(r: dict) -> dict:
    """Accept either the nested IR rule ({when:{op,value}, do:{action,by}}) or the flat form."""
    if "when" in r or "do" in r:
        w, d = r.get("when") or {}, r.get("do") or {}
        op, value, action, by = w.get("op", ">="), w.get("value", 0), d.get("action", "shift"), d.get("by", 0.0)
    else:
        op, value, action, by = r.get("op", ">="), r.get("value", 0), r.get("action", "shift"), r.get("by", 0.0)
    try:
        return {"op": str(op), "value": float(value), "action": str(action), "by": float(by)}
    except (TypeError, ValueError):
        return {"op": str(op), "value": 0.0, "action": "shift", "by": 0.0}


def _roll_policy(spec_id: str, etype: str, attr: dict, idx: int, baseline: float, horizon: int,
                 rules: list[dict], events: list[dict], dyn: dict, k: int) -> list[float]:
    """One deterministic closed-loop trajectory (roll k): values for frames 0..horizon (0 == now).

    Rules observe the current value and LATCH on first satisfaction: a ``shift`` rule then holds its
    setpoint offset (``by`` × span) for the rest of the horizon; a ``pulse`` rule adds ``by`` × span
    once at its fire frame. The shock seed omits the policy label → COMMON RANDOM NUMBERS across
    policies for a fair comparison.
    """
    span = dyn["span"]
    x = baseline
    out = [round(x, 3)]
    fired: dict[int, int] = {}
    for f in range(1, horizon + 1):
        for ri, r in enumerate(rules):  # latch on first time the condition holds
            if ri not in fired and _OPS.get(r["op"], lambda a, b: False)(x, r["value"]):
                fired[ri] = f
        offset = sum(r["by"] * span for ri, r in enumerate(rules) if r["action"] == "shift" and ri in fired)
        target = baseline + offset
        shock = dyn["vol"] * (_u(spec_id, etype, attr["name"], idx, k, f) - 0.5)  # no policy label → CRN
        x = x + dyn["rate"] * (target - x) + dyn["trend"] + shock
        for ri, r in enumerate(rules):  # one-time pulses at their fire frame
            if r["action"] == "pulse" and fired.get(ri) == f:
                x += r["by"] * span
        for ev in events:
            if int(ev.get("at_frame", -1)) == f:
                x += float(ev.get("by", 0.0)) * span
        x = min(dyn["hi"], max(dyn["lo"], x))
        out.append(round(x, 3))
    return out


def _evaluate_policy(spec_id: str, etype: str, attr: dict, idx: int, baseline: float, horizon: int,
                     policy: dict, dyn: dict, limit: float | None) -> dict:
    rules = [_norm_rule(r) for r in policy.get("rules", [])]
    events = policy.get("events", [])
    rolls = [_roll_policy(spec_id, etype, attr, idx, baseline, horizon, rules, events, dyn, k) for k in range(_ROLLS)]
    frames: list[dict] = []
    breach_frame: int | None = None
    for f in range(horizon + 1):
        col = sorted(r[f] for r in rolls)
        lo, mid, hi = col[0], float(median(col)), col[-1]
        frames.append({"f": f, "lo": round(lo, 3), "mid": round(mid, 3), "hi": round(hi, 3)})
        if breach_frame is None and limit is not None and mid >= limit:
            breach_frame = f
    terminals = [r[-1] for r in rolls]
    breach_rate = (
        round(sum(1 for r in rolls if any(v >= limit for v in r)) / len(rolls), 3) if limit is not None else 0.0
    )
    return {
        "label": str(policy.get("label", "policy")),
        "frames": frames,
        "breach_frame": breach_frame,
        "breach_rate": breach_rate,
        "terminal_mid": round(float(median(terminals)), 3),
        "worst_terminal": round(max(terminals), 3),  # higher = worse (toward an upper limit)
        "rule_count": len(rules),
    }


def _dedupe_labels(candidates: list[dict]) -> list[dict]:
    """Make every policy label unique (so the label-keyed metrics dict can't collapse) — baseline is
    first, so it keeps "baseline"; a user policy colliding with it (or another) gets a numeric suffix."""
    seen: dict[str, int] = {}
    out: list[dict] = []
    for c in candidates:
        label = str(c.get("label", "policy")) or "policy"
        if label in seen:
            seen[label] += 1
            label = f"{label} ({seen[label]})"
        seen.setdefault(label, 1)
        out.append({**c, "label": label})
    return out


def _rank(policies: list[dict], limit: float | None) -> str:
    """Most-robust label: fewest breaches, then lowest worst-case terminal (or lowest terminal)."""
    if limit is not None:
        best = min(policies, key=lambda p: (p["breach_rate"], p["worst_terminal"]))
    else:
        best = min(policies, key=lambda p: p["terminal_mid"])
    return best["label"]


def evaluate(spec_id: str, entity_type: str, attribute: str, *, horizon: int = 16,
             policies: list[dict] | None = None, row_index: int | None = None,
             baseline: float | None = None, assumptions: dict | None = None) -> dict:
    """Compare a baseline + N candidate policies for one numeric attribute. Deterministic.

    Returns ``{ok, ...}``; ``ok=False`` with ``error`` for unknown spec / missing or non-numeric
    attribute. A ``baseline`` policy (no rules) is always prepended. The sensitivity pass re-runs
    everything under harsher assumptions (weaker reversion, higher volatility) and reports whether the
    most-robust policy is unchanged — the load-bearing honesty signal.
    """
    spec = load_spec(spec_id)
    if spec is None:
        return {"ok": False, "error": f"spec not found: {spec_id}"}
    entity = next((e for e in spec.get("entities", []) if e.get("type") == entity_type), None)
    if entity is None:
        return {"ok": False, "error": f"entity not in spec: {entity_type}"}
    attr = next((a for a in entity.get("attributes", []) if a.get("name") == attribute), None)
    if attr is None or attr.get("semantic_type") not in _NUMERIC:
        return {"ok": False, "error": f"attribute missing or non-numeric: {attribute}"}

    horizon = max(1, min(int(horizon), _MAX_HORIZON))
    count = max(1, int(entity.get("count", 1)))
    if row_index is None:
        row_index = max(range(count), key=lambda i: _baseline_value(spec_id, entity_type, attr, i))
    row_index = max(0, min(count - 1, int(row_index)))
    base = float(baseline) if baseline is not None else _baseline_value(spec_id, entity_type, attr, row_index)
    if not math.isfinite(base):
        return {"ok": False, "error": "baseline must be finite"}

    threshold = attr.get("threshold") or {}
    limit = threshold.get("limit")
    limit = float(limit) if limit is not None else None
    objective = "avoid_breach" if limit is not None else "min_terminal"

    candidates = _dedupe_labels([{"label": "baseline", "rules": [], "events": []}] + list(policies or [])[:_MAX_POLICIES])

    dyn = _dynamics(attr, assumptions)
    evald = [_evaluate_policy(spec_id, entity_type, attr, row_index, base, horizon, p, dyn, limit) for p in candidates]
    best_label = _rank(evald, limit)

    # sensitivity: harsher world (weaker control reversion, +50% volatility) — does the winner hold?
    harsh = dict(dyn)
    harsh["rate"] = max(0.0, dyn["rate"] * 0.6)
    harsh["vol"] = dyn["vol"] * 1.5
    evald_harsh = [_evaluate_policy(spec_id, entity_type, attr, row_index, base, horizon, p, harsh, limit) for p in candidates]
    best_harsh = _rank(evald_harsh, limit)
    stable = best_harsh == best_label

    metrics = {p["label"]: {"breach_rate": p["breach_rate"], "worst_terminal": p["worst_terminal"],
                            "terminal_mid": p["terminal_mid"]} for p in evald}
    if limit is not None:
        reason = f"{best_label} 越限率最低({metrics[best_label]['breach_rate']})"
    else:
        # no threshold ⇒ ranking hangs on an unstated "lower is better" direction — disclose it
        reason = (
            f"{best_label} 终值最低({metrics[best_label]['terminal_mid']})"
            " —— 无阈值,按「越低越好」假设排序;若该量越高越好,结论反转"
        )

    return {
        "ok": True,
        "spec_id": spec_id, "entity_type": entity_type, "attribute": attribute,
        "row_index": row_index, "baseline": round(base, 3),
        "now": int((spec.get("temporal") or {}).get("now", 0)),
        "horizon": horizon, "range": attr.get("range"), "unit": attr.get("unit", ""),
        "threshold": attr.get("threshold"),
        "dynamics": {"model": dyn["model"], "rate": round(dyn["rate"], 3),
                     "trend": round(dyn["trend"], 4), "volatility": round(dyn["vol"], 4)},
        "policies": evald,
        "verdict": {"objective": objective, "best_label": best_label, "reason": reason, "metrics": metrics},
        "sensitivity": {
            "perturbed": {"rate": round(harsh["rate"], 3), "volatility": round(harsh["vol"], 4)},
            "best_label_perturbed": best_harsh,
            "stable": stable,
            "note": (
                f"在更严苛假设(回复×0.6、波动×1.5)下,最优仍为 {best_label} —— 排名稳健"
                if stable else
                f"排名对假设敏感:更严苛假设下最优变为 {best_harsh}(基准假设下为 {best_label})"
            ),
        },
        "confidence": {
            "rolls": _ROLLS,
            "note": "band/越限率 = 跨确定性 roll 统计;策略共用同一扰动序列(公共随机数)以公平对比;基线为独立合成,接 live 前非实测",
        },
    }
