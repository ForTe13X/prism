"""Axiom-gain ablation read API. Serves the report from FROZEN fixtures only (no live LLM from the
web); populate fixtures offline by running backend.app.benchmark.run_ablation(allow_live=True)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .amortization import run_amortization
from .axiom_gain_protocol import PROTO_MODELS, run_protocol
from .benchmark import run_ablation
from .data_package import load_source

benchmark_router = APIRouter(prefix="/api/axiomgain", tags=["axiomgain"])

# The committed interior point (RESEARCH §11d): a 35B MoE that is NOT actually more capable than 31B-dense on
# this task (naive F1 below gemma-31b) and BREAKS strict monotonicity (its gain sits above gemma-12b's). Adding
# it makes the H2 capability axis show the honest wobble (Spearman −0.80, not the cleaner 3-model −1.0) instead
# of a prettier-than-reality monotone line — surfaced on request so the H2 visual never hides the off-line point.
_FRONTIER_INTERIOR_MODEL = "qwen/qwen3.6-35b-a3b"


@benchmark_router.get("/{source_id}")
def axiom_gain(source_id: str) -> dict:
    if load_source(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    result = run_ablation(source_id, allow_live=False)  # fixtures only — deterministic, fast
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result.get("error", "no frozen fixtures for this ablation"))
    return result


@benchmark_router.get("/{source_id}/protocol")
def protocol(source_id: str, include_frontier_interior: bool = False) -> dict:
    """RESEARCH_axiom_gain full protocol: cross-model matrix × multi-seed mean±CI on quality gain + token
    saving + cost-per-correct Pareto frontier + gain×dirtiness robustness + §5 build break-even. Fixtures
    only (deterministic); un-cached cells are reported in `coverage`, never silently dropped.

    `include_frontier_interior=true` adds the committed qwen3.6-35b-a3b interior point to the model set so the
    H2 capability axis renders the honest monotonicity-breaking wobble (Spearman −0.80) instead of the cleaner
    3-model −1.0 — used by the H2 "capability×gain" visual so it never hides the off-line point (DON'T #4)."""
    if load_source(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    models = PROTO_MODELS + [_FRONTIER_INTERIOR_MODEL] if include_frontier_interior else None
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
