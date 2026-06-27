"""Axiom-gain ablation read API. Serves the report from FROZEN fixtures only (no live LLM from the
web); populate fixtures offline by running backend.app.benchmark.run_ablation(allow_live=True)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
