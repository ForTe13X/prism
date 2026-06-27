"""Prism — a semantic-foundation-driven, domain-agnostic cockpit (backend).

The backend is itself domain-agnostic: it serves the declarative spec and deterministically
synthesized data. It knows nothing about pipelines or libraries — the spec does. Run:

    uvicorn backend.app.main:app --port 8200   (from the prism/ root)
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .benchmark_routes import benchmark_router
from .calibration_routes import calibration_router
from .compile_routes import compile_router
from .data_synth import resolve_frame, resolve_temporal, synth_entity_rows, synth_graph
from .datapackage_routes import datapackage_router
from .nexus_routes import nexus_router
from .parse_routes import parse_router
from .policy_routes import policy_router
from .sim_routes import sim_router
from .specs_loader import list_specs, load_spec

app = FastAPI(title="Prism", description="Semantic-foundation-driven cockpit", version="0.1.0")

# Dev CORS: the Vite dev server (5173) talks to this API (8200). Tighten for any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],  # POST for /api/sim (trajectory simulation)
    allow_headers=["*"],
)

# Trajectory simulation (decision-support): POST /api/sim/{spec}. Self-contained engine; see
# backend/app/simulation.py. Wiring is a one-liner by design (the engine has no main.py coupling).
app.include_router(sim_router)

# Policy comparison (sequential what-if): POST /api/policy/{spec}. Typed-IR contract + deterministic
# rollout engine; see backend/app/policy.py and docs/DESIGN_what_if_sequential.md.
app.include_router(policy_router)

# LLM compile (P6 generate→confirm): POST /api/compile/{spec} turns NL → typed policy IR (a
# suggestion to confirm, never executed) + GET /api/llm/health. The LLM never produces numbers.
app.include_router(compile_router)

# Cross-source data package (DP1): GET /api/datapackage[/...] — a deterministic, clean-room generator
# of a heterogeneous multi-store dataset with pre-embedded ground-truth, for the axiom-gain benchmark.
app.include_router(datapackage_router)

# Axiom-gain ablation (DP2): GET /api/axiomgain/{source} — naive-RAG vs axiom-RAG on the cross-source
# task (local LLM), served from frozen fixtures. Plus /{source}/amortization (RESEARCH §5): a learned
# resolver with a real build cost, amortized to a break-even (deterministic). See benchmark.py /
# amortization.py + RESEARCH_axiom_gain.md §11/§11b.
app.include_router(benchmark_router)

# §5 agentic parser: GET /api/parse/{source} — render a package messy, parse it back, report round-trip
# recovery + observable failures. §4b calibration: GET /api/calibration — fit a mechanism from a
# (synthetic-stand-in) reference's aggregates, re-sample, check held-out moments. Both deterministic.
app.include_router(parse_router)
app.include_router(calibration_router)

# Nexus metric (METRIC_nexus_reality, M0): GET /api/nexus/{source}/{baselines|sweep|controls} — the
# dumb-baseline ladder (esp. the lethal time-coincidence bar) the future 3-lens metric must beat.
# Deterministic. See nexus_eval.py + METRIC_nexus_reality.md §11.
app.include_router(nexus_router)


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


@app.get("/api/timeline/{spec_id}")
def timeline(spec_id: str) -> dict:
    """The replay axis for one spec: {frames, now, step}. Drives the cockpit's replay slider.

    A spec with no ``temporal`` block collapses to a single frame (frames=1) — no replay axis.
    """
    doc = load_spec(spec_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"spec not found: {spec_id}")
    return {"spec_id": spec_id, **resolve_temporal(doc)}


@app.get("/api/data/{spec_id}/{entity_type}")
def data(spec_id: str, entity_type: str, frame: int | None = None) -> dict:
    """Deterministically synthesized rows for one entity type of one spec, at ``frame``.

    ``frame`` is clamped into the spec's valid range and defaults to ``now`` (the resolved value is
    echoed back). Same (spec, entity, frame) ⇒ byte-identical rows; non-evolving attributes are
    identical across all frames.
    """
    doc = load_spec(spec_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"spec not found: {spec_id}")
    entity = next((e for e in doc.get("entities", []) if e.get("type") == entity_type), None)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"entity '{entity_type}' not in spec '{spec_id}'")
    resolved = resolve_frame(doc, frame)
    return {
        "spec_id": spec_id,
        "entity_type": entity_type,
        "frame": resolved,
        "rows": synth_entity_rows(entity, spec_id, resolved),
    }


@app.get("/api/graph/{spec_id}")
def graph(spec_id: str, frame: int | None = None) -> dict:
    """The instance graph at ``frame``: nodes = entity rows, edges = deterministic relation mappings.

    Built purely from the spec (domain-agnostic). Topology is identity-stable across frames; only node
    state evolves — so the ontology canvas can replay the network by recolouring nodes via the slider.
    """
    doc = load_spec(spec_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"spec not found: {spec_id}")
    resolved = resolve_frame(doc, frame)
    return {"spec_id": spec_id, "frame": resolved, **synth_graph(doc, spec_id, resolved)}
