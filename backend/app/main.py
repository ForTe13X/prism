"""Prism — a semantic-foundation-driven, domain-agnostic cockpit (backend).

The backend is itself domain-agnostic: it serves the declarative spec and deterministically
synthesized data. It knows nothing about pipelines or libraries — the spec does. Run:

    uvicorn backend.app.main:app --port 8200   (from the prism/ root)
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .data_synth import synth_entity_rows
from .specs_loader import list_specs, load_spec

app = FastAPI(title="Prism", description="Semantic-foundation-driven cockpit", version="0.1.0")

# Dev CORS: the Vite dev server (5173) talks to this API (8200). Tighten for any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "prism", "version": "0.1.0"}


@app.get("/api/specs")
def specs() -> dict:
    """Catalogue of available domain specs (drives the domain switcher)."""
    return {"specs": list_specs()}


@app.get("/api/spec/{spec_id}")
def spec(spec_id: str) -> dict:
    """The full semantic foundation for one domain — the renderer builds the whole UI from this."""
    doc = load_spec(spec_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"spec not found: {spec_id}")
    return doc


@app.get("/api/data/{spec_id}/{entity_type}")
def data(spec_id: str, entity_type: str) -> dict:
    """Deterministically synthesized rows for one entity type of one spec."""
    doc = load_spec(spec_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"spec not found: {spec_id}")
    entity = next((e for e in doc.get("entities", []) if e.get("type") == entity_type), None)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"entity '{entity_type}' not in spec '{spec_id}'")
    return {"spec_id": spec_id, "entity_type": entity_type, "rows": synth_entity_rows(entity, spec_id)}
