"""Axiom-gain ablation read API. Serves the report from FROZEN fixtures only (no live LLM from the
web); populate fixtures offline by running backend.app.benchmark.run_ablation(allow_live=True)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .amortization import run_amortization
from .axiom_gain_protocol import PROTO_MODELS, run_protocol
from .benchmark import run_ablation
from .data_package import load_source

benchmark_router = APIRouter(prefix="/api/axiomgain", tags=["axiomgain"])

# Off-default H2 capability-axis points (surfaced on request so the H2 visual never hides them, DON'T #4):
#  - qwen3.6-35b-a3b: the committed INTERIOR point (RESEARCH §11d) — a 35B MoE NOT actually more capable than
#    31B-dense here (naive F1 below gemma-31b), whose gain sits above gemma-12b's ⇒ BREAKS strict monotonicity
#    (Spearman −0.80, not the prettier 3-model −1.0).
#  - deepseek-v4-pro-260425: an INDEPENDENT real-API point (RESEARCH §11f). Over the full grid its naive F1
#    (~0.808) is ~TIED with gemma-31b (NOT more capable — the dirt-0.6 slice alone overstated its edge), so it
#    is a cross-model CORROBORATION at the top of the local range, not a frontier extension: a totally different
#    model at the same task-competence shows the same gain (~0.107) and the ~63% saving holds with REAL API
#    token counts (H2b measured on a commercial API). Frozen from a one-time paid Ark run (reproducible from
#    fixtures at serve-time $0); flagged per-row as API/paid/prompt-JSON, never silently mixed in.
_H2_EXTRA_MODELS = ["qwen/qwen3.6-35b-a3b", "deepseek-v4-pro-260425"]


@benchmark_router.get("/{source_id}")
def axiom_gain(source_id: str) -> dict:
    if load_source(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    result = run_ablation(source_id, allow_live=False)  # fixtures only — deterministic, fast
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result.get("error", "no frozen fixtures for this ablation"))
    return result


@benchmark_router.get("/{source_id}/protocol")
def protocol(source_id: str, include_h2_extra: bool = False) -> dict:
    """RESEARCH_axiom_gain full protocol: cross-model matrix × multi-seed mean±CI on quality gain + token
    saving + cost-per-correct Pareto frontier + gain×dirtiness robustness + §5 build break-even. Fixtures
    only (deterministic); un-cached cells are reported in `coverage`, never silently dropped.

    `include_h2_extra=true` adds the off-default H2 capability-axis points (the qwen3.6-35b-a3b interior wobble
    + the deepseek-v4-pro independent real-API corroboration point, capability TIED with gemma-31b) to the model
    set so the H2 "capability×gain" visual renders the honest non-monotone wobble AND the tied-capability
    cross-model corroboration — never hiding either (DON'T #4). The default (no param) response gains only an
    additive per-row `provenance` field; all headline NUMBERS are unchanged, so the tabs that read it are
    unaffected."""
    if load_source(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    models = PROTO_MODELS + _H2_EXTRA_MODELS if include_h2_extra else None
    return run_protocol(source_id, models=models)


@benchmark_router.get("/{source_id}/amortization")
def amortization(source_id: str, dirt: float = 0.6) -> dict:
    """RESEARCH §5: does the axiom layer earn its BUILD cost? A learned resolver with a real, measured
    build cost, amortized to a break-even — deterministic/offline (no live LLM)."""
    if load_source(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    result = run_amortization(source_id, dirt=dirt)
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("error", "amortization unavailable"))
    return result
