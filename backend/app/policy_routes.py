"""Policy-comparison REST router (sequential what-if). The Pydantic models below ARE the typed policy
IR (the schema-validated contract from docs/DESIGN_what_if_sequential.md): an LLM may later fill this
shape (NL → IR), but the engine only ever executes a validated IR. Wired in main.py with one line.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .policy import evaluate

policy_router = APIRouter(prefix="/api/policy", tags=["policy"])


class When(BaseModel):
    op: str = Field(default=">=", description="comparison operator: >= , <= , > , <")
    value: float  # absolute attribute value to compare the (observed) target against


class Do(BaseModel):
    action: str = "shift"  # "shift" = latching setpoint offset; "pulse" = one-time kick
    by: float = 0.0        # signed fraction of the attribute's range span


class Rule(BaseModel):
    when: When
    do: Do
    note: str = ""


class PolicyEvent(BaseModel):
    at_frame: int = 0
    by: float = 0.0  # one-time fraction-of-span kick at a fixed frame


class Policy(BaseModel):
    label: str
    rules: list[Rule] = Field(default_factory=list)
    events: list[PolicyEvent] = Field(default_factory=list)


class Assumptions(BaseModel):
    rate: float | None = None
    trend: float | None = None
    volatility: float | None = None


class PolicyRequest(BaseModel):
    entity_type: str
    attribute: str
    horizon: int = Field(default=16, ge=1, le=96)
    row_index: int | None = None
    policies: list[Policy] = Field(default_factory=list)
    assumptions: Assumptions | None = None


@policy_router.post("/{spec_id}")
def run_policies(spec_id: str, req: PolicyRequest) -> dict:
    """Baseline + candidate policies compared by robustness, with a sensitivity pass.

    The validated IR (nested when/do) is passed straight to the engine, which normalizes it.
    """
    result = evaluate(
        spec_id,
        req.entity_type,
        req.attribute,
        horizon=req.horizon,
        policies=[p.model_dump() for p in req.policies],
        row_index=req.row_index,
        assumptions=req.assumptions.model_dump() if req.assumptions else None,
    )
    if not result.get("ok"):
        error = str(result.get("error", "policy evaluation failed"))
        raise HTTPException(status_code=404 if "spec not found" in error else 400, detail=error)
    return result
