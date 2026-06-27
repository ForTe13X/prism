"""Nexus metric read API (METRIC_nexus_reality Phase A). M0 serves the BASELINE LADDER — the bar a lens
must beat — plus the link sweep and negative controls. All deterministic/offline (no LLM). The full
3-lens metric + nexus_confidence lands at /api/nexus/{a}/{b} once the lenses (M1/M2) clear the bar."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .data_package import load_source
from .nexus_eval import discrimination_sweep, negative_controls, run_baseline_ladder

nexus_router = APIRouter(prefix="/api/nexus", tags=["nexus"])

_CAVEAT = ("Phase A = 跨源 link 原型(单域多源),非跨域 nexus。M0 只给『笨 baseline 阶梯』作标杆;"
           "诚实发现:time-coincidence 在本 substrate 各 link/脏度均近天花板(真桥按构造即时间巧合),"
           "故 lens 仅在引入『时间不可分的硬负例』后才有空间(见 METRIC §8)。")


def _require_source(source_id: str) -> None:
    if load_source(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")


@nexus_router.get("/{source_id}/baselines")
def baselines(source_id: str, link: int = 4, dirt: float = 0.0) -> dict:
    _require_source(source_id)
    return {**run_baseline_ladder(source_id, link=link, dirt=dirt), "caveat": _CAVEAT}


@nexus_router.get("/{source_id}/sweep")
def sweep(source_id: str, dirt: float = 0.0) -> dict:
    _require_source(source_id)
    return {**discrimination_sweep(source_id, dirt=dirt), "caveat": _CAVEAT}


@nexus_router.get("/{source_id}/controls")
def controls(source_id: str, link: int = 4, dirt: float = 0.0) -> dict:
    _require_source(source_id)
    return {**negative_controls(source_id, link=link, dirt=dirt), "caveat": _CAVEAT}
