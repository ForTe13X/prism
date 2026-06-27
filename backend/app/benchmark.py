"""Axiom-gain ablation (RESEARCH_axiom_gain) — does an axiom/canonical layer beat naive RAG on the
cross-source explain_delays task, and at what token cost, across models and dirtiness?

Two fairly-matched conditions over the SAME held-out packages, same model, same prompt — only the
context differs: naive-RAG (raw multi-store facts) vs axiom-RAG (canonical-resolved + pre-joined
facts, from axiom_layer). We record quality (F1 vs ground-truth), input/output tokens and calls per
condition, and report the headline cost-per-correct frontier + gain-over-naive and the gain×dirtiness
curve. LLM calls go through the frozen fixture cache (llm_client.structured_complete) so the figures
re-run byte-identically without the model.

Honesty (RESEARCH §10): the naive baseline is a real "give it the raw stores" RAG (not a strawman);
held-out = the axiom layer is ALGORITHMIC (no training, so no overfitting) and the LLM is pinned via
fixtures; build-cost is ~0 LLM tokens here (the resolver is deterministic), so amortization is trivial
and is reported as such — a learned axiom-net would have a real build cost to amortize.
"""
from __future__ import annotations

import json
import pathlib

from . import llm_client
from .axiom_layer import axiom_context, naive_context, task_question
from .data_package import generate
from .data_package_eval import observation_view, oracle_solve, score

# records the config the frozen fixtures were built with, so the API/tests reproduce the exact run
# from fixtures WITHOUT probing a live model.
_MANIFEST = pathlib.Path(__file__).resolve().parent.parent / "benchmark_fixtures" / "manifest.json"


def _manifest() -> dict:
    try:
        return json.loads(_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

# pricing per 1M tokens; local LM Studio models are $0 but tokens are REAL (single honest column).
PRICING = {"_local": {"in": 0.0, "out": 0.0}}

_ANSWER_SCHEMA = {
    "name": "delay_attribution", "strict": True,
    "schema": {
        "type": "object",
        "properties": {"answer": {"type": "array", "items": {
            "type": "object",
            "properties": {"news_id": {"type": "string"}, "shipment_ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["news_id", "shipment_ids"],
        }}},
        "required": ["answer"],
    },
}
_SYSTEM = "你是跨源数据分析助手。只依据【上下文】回答,不得编造任何 id;无法确定就不输出该条。"


def _parse(content: str) -> dict:
    import json

    try:
        obj = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {}
    out: dict = {}
    for row in obj.get("answer", []) or []:
        nid = row.get("news_id")
        ships = row.get("shipment_ids") or []
        if isinstance(nid, str) and isinstance(ships, list):
            out[nid] = sorted(str(s) for s in ships)
    return out


def _ask(context: str, model: str | None, allow_live: bool) -> dict:
    user = f"{task_question()}\n\n【上下文】\n{context}"
    return llm_client.structured_complete(_SYSTEM, user, _ANSWER_SCHEMA, model, allow_live=allow_live)


def run_ablation(source_id: str = "logistics_demo", *, seeds: list[str] | None = None,
                 models: list[str] | None = None, dirts: list[float] | None = None,
                 allow_live: bool = False) -> dict:
    man = _manifest()  # reproduce the fixtured config without probing a live model
    seeds = seeds or man.get("seeds") or [f"ho-{i}" for i in range(4)]  # held-out (algorithmic layer ⇒ no train leak)
    models = models or man.get("models") or [llm_client.resolve_model()]
    dirts = dirts if dirts is not None else (man.get("dirts") or [0.0, 0.6])
    conditions, per_call = [], []
    for model in models:
        for dirt in dirts:
            agg = {"naive": [], "axiom": []}
            tok = {"naive": [0, 0], "axiom": [0, 0]}
            calls = {"naive": 0, "axiom": 0}
            cached_all = True
            for sd in seeds:
                pkg = generate(source_id, dirtiness=dirt, link_explicitness=4, seed=sd)
                obs = observation_view(pkg)
                truth = oracle_solve(pkg, "explain_delays")
                for cond, ctx in (("naive", naive_context(obs)), ("axiom", axiom_context(obs))):
                    r = _ask(ctx, model, allow_live)
                    if not r.get("ok"):
                        return {"ok": False, "error": f"LLM call failed ({r.get('error')}); run with allow_live to populate fixtures"}
                    cached_all = cached_all and r.get("cached", False)
                    f1 = score(_parse(r["content"]), truth)["f1"]
                    agg[cond].append(f1)
                    tok[cond][0] += r["usage"]["in"]
                    tok[cond][1] += r["usage"]["out"]
                    calls[cond] += 1
                    per_call.append({"model": r["model"], "dirt": dirt, "cond": cond, "seed": sd,
                                     "f1": f1, "in": r["usage"]["in"], "out": r["usage"]["out"], "cached": r.get("cached")})
            for cond in ("naive", "axiom"):
                n = len(agg[cond]) or 1
                qual = round(sum(agg[cond]) / n, 3)
                total_tok = tok[cond][0] + tok[cond][1]
                # tokens per unit-correctness (the headline when $=0); guard near-zero quality
                tpc = round(total_tok / max(0.001, sum(agg[cond])), 1)
                conditions.append({
                    "model": models_label(model), "dirtiness": dirt, "condition": f"{cond}-RAG",
                    "quality_f1": qual, "avg_in_tok": round(tok[cond][0] / n, 1),
                    "avg_out_tok": round(tok[cond][1] / n, 1), "calls": calls[cond],
                    "tokens_per_correct": tpc,
                })
    if allow_live:  # freeze the config alongside the fixtures
        _MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        _MANIFEST.write_text(json.dumps({"source_id": source_id, "seeds": seeds, "models": models, "dirts": dirts},
                                        ensure_ascii=False, indent=2), encoding="utf-8")
    gains = _gains(conditions)
    return {
        "ok": True, "source_id": source_id, "models": [models_label(m) for m in models], "dirts": dirts,
        "seeds": seeds, "conditions": conditions, "gains": gains,
        "all_cached": all(c["cached"] for c in per_call) if per_call else False,
        "pricing": PRICING,
        "notes": [
            "naive-RAG = 原始多源事实(未解析);axiom-RAG = canonical 解析 + 预联结事实(axiom_layer)。同模型同 prompt,只换上下文。",
            "本地模型 $=0,故 token 真实但成本列为 0;headline 用 tokens-per-correct(每单位正确所耗 token)。",
            "axiom 层为算法式(无训练)⇒ build 成本≈0 LLM token,摊销平凡;学习式 axiom-net 才有真 build 成本要摊销。",
            "held-out=算法层无过拟合 + LLM 经 frozen fixture 固定;小规模首跑(seeds×models×dirts),非完整多 seed/CI 研究。",
        ],
    }


def models_label(m: str) -> str:
    return m


def _gains(conditions: list[dict]) -> list[dict]:
    """axiom-RAG vs naive-RAG at the same (model, dirtiness)."""
    idx = {(c["model"], c["dirtiness"], c["condition"]): c for c in conditions}
    out = []
    for (model, dirt, cond), c in idx.items():
        if cond != "axiom-RAG":
            continue
        nv = idx.get((model, dirt, "naive-RAG"))
        if not nv:
            continue
        out.append({
            "model": model, "dirtiness": dirt,
            "quality_delta": round(c["quality_f1"] - nv["quality_f1"], 3),
            "input_token_ratio": round(c["avg_in_tok"] / max(1e-9, nv["avg_in_tok"]), 2),
            "tokens_per_correct_ratio": round(c["tokens_per_correct"] / max(1e-9, nv["tokens_per_correct"]), 2),
        })
    return out
