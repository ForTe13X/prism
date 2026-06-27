"""Axiom-gain ablation read API. Serves the report from FROZEN fixtures only (no live LLM from the
web); populate fixtures offline by running backend.app.benchmark.run_ablation(allow_live=True)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .amortization import run_amortization
from .benchmark import run_ablation
from .data_package import load_source

benchmark_router = APIRouter(prefix="/api/axiomgain", tags=["axiomgain"])


@benchmark_router.get("/{source_id}")
def axiom_gain(source_id: str) -> dict:
    if load_source(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    result = run_ablation(source_id, allow_live=False)  # fixtures only — deterministic, fast
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result.get("error", "no frozen fixtures for this ablation"))
    return result


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
