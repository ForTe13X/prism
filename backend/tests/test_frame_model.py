"""P1 time-frame model — the keystone invariants every later time feature relies on.

Covers: determinism (same frame ⇒ byte-identical), evolution (different frames differ for an
``evolves`` attribute), invariance (attributes WITHOUT ``evolves`` — and identifiers — are identical
across all frames), the sliding timeseries window, and boundary / null-safety of the frame helpers.
The asserts are written against the synth layer directly so they hold regardless of the HTTP layer;
``test_api.py`` then checks the same guarantees end-to-end through the endpoints.
"""
from __future__ import annotations

import json

import pytest

from backend.app import data_synth as ds
from backend.app.data_synth import (
    resolve_frame,
    resolve_temporal,
    synth_entity_rows,
    synth_value,
)
from backend.app.specs_loader import load_spec

SPEC_ID = "infra_monitoring"


@pytest.fixture()
def station() -> dict:
    spec = load_spec(SPEC_ID)
    assert spec is not None
    return next(e for e in spec["entities"] if e["type"] == "station")


def _attr(entity: dict, name: str) -> dict:
    return next(a for a in entity["attributes"] if a["name"] == name)


# --- determinism --------------------------------------------------------------------------------

def test_same_frame_is_byte_identical(station: dict) -> None:
    a = synth_entity_rows(station, SPEC_ID, 36)
    b = synth_entity_rows(station, SPEC_ID, 36)
    assert a == b
    # byte-identical once serialized — replay must be reproducible to the byte
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) == json.dumps(b, ensure_ascii=False, sort_keys=True)


def test_no_clock_or_random_imported() -> None:
    # The synth module must not reach for wall-clock time or randomness — replay depends on it.
    # Inspect the actual imports (not docstring prose, which legitimately mentions "no random").
    import ast
    import inspect

    imported: set[str] = set()
    for node in ast.walk(ast.parse(inspect.getsource(ds))):
        if isinstance(node, ast.Import):
            imported |= {n.name.split(".")[0] for n in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported.isdisjoint({"random", "time", "datetime", "secrets"})


# --- evolution ----------------------------------------------------------------------------------

def test_evolving_attributes_change_across_frames(station: dict) -> None:
    early = synth_entity_rows(station, SPEC_ID, 4)
    late = synth_entity_rows(station, SPEC_ID, 44)
    # pressure (gauge, evolves) and status (status, evolves) should differ for at least one row
    assert any(e["pressure"] != l["pressure"] for e, l in zip(early, late))
    assert any(e["status"] != l["status"] for e, l in zip(early, late))


def test_evolution_is_deterministic_per_frame(station: dict) -> None:
    pressure = _attr(station, "pressure")
    seq1 = [synth_value(pressure, SPEC_ID, "station", 0, f) for f in range(48)]
    seq2 = [synth_value(pressure, SPEC_ID, "station", 0, f) for f in range(48)]
    assert seq1 == seq2
    # and it actually moves (not a constant) — drift > 0
    assert len(set(seq1)) > 1


# --- invariance ---------------------------------------------------------------------------------

def test_non_evolving_attribute_is_frame_invariant(station: dict) -> None:
    # 'region' is a category WITHOUT evolves → identical across every frame
    region = _attr(station, "region")
    values = {synth_value(region, SPEC_ID, "station", 0, f) for f in range(48)}
    assert len(values) == 1


def test_identifier_never_evolves(station: dict) -> None:
    name = _attr(station, "name")
    values = {synth_value(name, SPEC_ID, "station", 3, f) for f in range(48)}
    assert values == {"STN-004"}


def test_non_evolving_equals_v0_baseline(station: dict) -> None:
    # drift==0 path must return exactly the frame-independent baseline _unit(*seed) — this is the
    # backward-compat guarantee: an un-annotated spec renders identically to v0.
    region = _attr(station, "region")
    seed = (SPEC_ID, "station", 0, "region")
    expected = region["values"][int(ds._unit(*seed) * len(region["values"])) % len(region["values"])]
    assert synth_value(region, SPEC_ID, "station", 0, 12) == expected


def test_evolve_unit_drift_zero_returns_base() -> None:
    seed = ("a", "b", 0, "c")
    assert ds._evolve_unit(7, 0.0, *seed) == ds._unit(*seed)


# --- timeseries sliding window ------------------------------------------------------------------

def test_timeseries_window_slides_when_evolving(station: dict) -> None:
    h2s = _attr(station, "h2s")  # evolves: true
    points = int(h2s.get("points", 24))
    win_a = synth_value(h2s, SPEC_ID, "station", 0, 10)
    win_b = synth_value(h2s, SPEC_ID, "station", 0, 40)
    assert len(win_a) == points and len(win_b) == points
    assert win_a != win_b
    # overlapping frames share their overlap: window@N and window@N+1 differ by one sample shift
    w0 = synth_value(h2s, SPEC_ID, "station", 0, 20)
    w1 = synth_value(h2s, SPEC_ID, "station", 0, 21)
    assert w0[1:] == w1[:-1]


def test_timeseries_window_static_when_not_evolving() -> None:
    # a timeseries WITHOUT evolves stays on the v0 window regardless of frame
    attr = {"name": "s", "semantic_type": "timeseries", "range": [0, 10], "points": 12}
    assert synth_value(attr, "x", "e", 0, 0) == synth_value(attr, "x", "e", 0, 99)


# --- temporal / frame resolution: boundaries & null-safety --------------------------------------

def test_resolve_temporal_reads_spec() -> None:
    spec = load_spec(SPEC_ID)
    assert resolve_temporal(spec) == {"frames": 48, "now": 36, "step": "hour"}


def test_resolve_temporal_defaults_when_absent() -> None:
    assert resolve_temporal({}) == {"frames": 1, "now": 0, "step": "frame"}


@pytest.mark.parametrize("bad", [{"frames": "x"}, {"frames": -5}, {"now": "y"}, {"frames": 10, "now": 999}])
def test_resolve_temporal_is_null_safe(bad: dict) -> None:
    t = resolve_temporal({"temporal": bad})
    assert t["frames"] >= 1
    assert 0 <= t["now"] <= t["frames"] - 1


def test_resolve_frame_clamps_and_defaults() -> None:
    spec = load_spec(SPEC_ID)  # frames=48, now=36
    assert resolve_frame(spec, None) == 36          # default → now
    assert resolve_frame(spec, -100) == 0           # clamp low
    assert resolve_frame(spec, 10_000) == 47        # clamp high
    assert resolve_frame(spec, 12) == 12            # in range


def test_synth_is_null_safe_on_sparse_attrs() -> None:
    # missing values / range must not crash; empty category → None
    assert synth_value({"name": "c", "semantic_type": "category", "values": []}, "x", "e", 0, 5) is None
    assert synth_value({"name": "m", "semantic_type": "metric"}, "x", "e", 0, 5) is not None
    assert synth_value({"name": "u", "semantic_type": "mystery"}, "x", "e", 0, 5) is None


def test_malformed_numeric_spec_fields_degrade_to_defaults() -> None:
    # spec files are author-controlled and unvalidated — a stray non-numeric points/count/frame must
    # fall back to a default, never 500 the data endpoint.
    bad_points = {"name": "s", "semantic_type": "timeseries", "range": [0, 10], "points": "oops"}
    assert len(synth_value(bad_points, "x", "e", 0, 3)) == 24  # default points
    bad_count = {"type": "e", "count": None, "attributes": [{"name": "m", "semantic_type": "metric"}]}
    assert len(synth_entity_rows(bad_count, "x")) == 5  # default count
    assert resolve_frame(load_spec(SPEC_ID), "not-an-int") == 36  # → now
