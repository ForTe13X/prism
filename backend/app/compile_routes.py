"""NL → policy-IR compile router (the P6 generate→confirm pattern applied to policies).

POST /api/compile/{spec} returns a COMPILED IR — it does NOT execute it. The frontend shows the
rules in the editable policy editor (the human-confirm gate); the user reviews/edits, then runs the
deterministic comparison via /api/policy. The LLM never touches the numbers. GET /api/llm/health
exposes reachability + the no-fake-fallback failure counters honestly.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import llm_client
from .specs_loader import load_spec

compile_router = APIRouter(tags=["compile"])

_NUMERIC = {"metric", "gauge", "timeseries"}


class CompileRequest(BaseModel):
    entity_type: str
    attribute: str
    nl: str = Field(min_length=1, max_length=600)


@compile_router.get("/api/llm/health")
def llm_health() -> dict:
    """Is the local LLM reachable, which model, and how have compiles fared (honest counters)."""
    return llm_client.health()


@compile_router.post("/api/compile/{spec_id}")
def compile_policy(spec_id: str, req: CompileRequest) -> dict:
    """Compile NL → a validated policy IR for one numeric attribute. Returns the IR for confirmation."""
    spec = load_spec(spec_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"spec not found: {spec_id}")
    entity = next((e for e in spec.get("entities", []) if e.get("type") == req.entity_type), None)
    if entity is None:
        raise HTTPException(status_code=400, detail=f"entity not in spec: {req.entity_type}")
    attr = next((a for a in entity.get("attributes", []) if a.get("name") == req.attribute), None)
    if attr is None or attr.get("semantic_type") not in _NUMERIC:
        raise HTTPException(status_code=400, detail=f"attribute missing or non-numeric: {req.attribute}")

    result = llm_client.compile_policy(attr, req.nl)
    if not result.get("ok"):
        # observable failure — surface the reason; the client falls back to hand-writing rules
        raise HTTPException(status_code=502, detail=result.get("error", "compile failed"))
    return {
        "ok": True,
        "spec_id": spec_id,
        "entity_type": req.entity_type,
        "attribute": req.attribute,
        "rules": result["rules"],
        "model": result["model"],
        "source": "llm_compiled",  # honest provenance: a suggestion to confirm, not executed
    }
