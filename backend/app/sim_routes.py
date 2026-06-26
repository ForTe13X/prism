"""Trajectory-simulation REST router (decision-support). Independent APIRouter — NOT included in
main.py by this module (parallel-dev isolation). To expose it, add ONE line to main.py:

    from .sim_routes import sim_router
    app.include_router(sim_router)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .simulation import simulate

sim_router = APIRouter(prefix="/api/sim", tags=["simulation"])


class Scenario(BaseModel):
    label: str
    at: int = 0
    delta: float = 0.0
    mode: str = "shift"  # "shift" = setpoint change from `at` onward; "pulse" = one-time at `at`


class SimRequest(BaseModel):
    entity_type: str
    attribute: str
    horizon: int = Field(default=12, ge=1, le=96)
    row_index: int | None = None
    scenarios: list[Scenario] = Field(default_factory=list)


@sim_router.post("/{spec_id}")
def run_simulation(spec_id: str, req: SimRequest) -> dict:
    """Baseline + scenario trajectories for one numeric attribute, with band/breach/verdict."""
    result = simulate(
        spec_id,
        req.entity_type,
        req.attribute,
        horizon=req.horizon,
        scenarios=[s.model_dump() for s in req.scenarios],
        row_index=req.row_index,
    )
    if not result.get("ok"):
        error = str(result.get("error", "simulation failed"))
        raise HTTPException(status_code=404 if "spec not found" in error else 400, detail=error)
    return result
