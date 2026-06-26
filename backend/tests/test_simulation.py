"""Trajectory simulation (decision-support). Self-contained: builds a local FastAPI app for the
router test (does NOT import backend.app.main), and calls simulate() directly for logic assertions
with a controlled `baseline` so breach/verdict checks are deterministic regardless of the synthetic
baseline. Target: infra_monitoring / station / pressure (gauge, range [0,12], threshold limit 10)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.sim_routes import sim_router
from backend.app.simulation import simulate

_app = FastAPI()
_app.include_router(sim_router)
client = TestClient(_app)

SPEC, ENT, ATTR = "infra_monitoring", "station", "pressure"


def _sim(**kw):
    return simulate(SPEC, ENT, ATTR, **kw)


def test_deterministic_byte_identical() -> None:
    a = _sim(horizon=12, baseline=8.0, scenarios=[{"label": "cut", "at": 2, "delta": -3.0}])
    b = _sim(horizon=12, baseline=8.0, scenarios=[{"label": "cut", "at": 2, "delta": -3.0}])
    assert a == b


def test_shape_baseline_first_and_frame_axis() -> None:
    r = _sim(horizon=10, baseline=7.0, scenarios=[{"label": "x", "delta": 1.0}])
    assert r["ok"] and len(r["trajectories"]) == 2
    base = r["trajectories"][0]
    assert base["label"] == "baseline"
    # frames 0..horizon; frame 0 collapses to the baseline (every roll starts there)
    assert [f["f"] for f in base["frames"]] == list(range(11))
    f0 = base["frames"][0]
    assert f0["lo"] == f0["mid"] == f0["hi"] == 7.0


def test_band_is_ordered_everywhere() -> None:
    r = _sim(horizon=24, baseline=6.0, scenarios=[{"label": "up", "delta": 4.0}])
    for traj in r["trajectories"]:
        for fr in traj["frames"]:
            assert fr["lo"] <= fr["mid"] <= fr["hi"]


def test_breach_detection_and_verdict_prefers_avoiding_scenario() -> None:
    # baseline target 6.0 stays well under limit 10; a +5 setpoint shift drives it over → breach.
    r = _sim(horizon=20, baseline=6.0, scenarios=[{"label": "spike", "at": 3, "delta": 5.0, "mode": "shift"}])
    breaches = {t["label"]: t["breach_frame"] for t in r["trajectories"]}
    assert breaches["baseline"] is None          # never crosses limit 10
    assert breaches["spike"] is not None          # shifted target 11 crosses it
    assert breaches["spike"] >= 3                  # only after the intervention frame
    assert r["verdict"]["objective"] == "avoid_breach"
    assert r["verdict"]["best_label"] == "baseline"  # the breach-avoiding option wins


def test_shift_diverges_from_baseline() -> None:
    r = _sim(horizon=16, baseline=5.0, scenarios=[{"label": "shift_down", "at": 1, "delta": -3.0}])
    base_term = r["trajectories"][0]["terminal_mid"]
    shift_term = r["trajectories"][1]["terminal_mid"]
    assert shift_term < base_term  # a downward setpoint shift ends lower


def test_no_threshold_attr_uses_min_terminal_objective() -> None:
    # 'throughput' is a metric with no threshold → verdict falls back to min-terminal.
    r = simulate(SPEC, ENT, "throughput", horizon=8, baseline=500.0,
                 scenarios=[{"label": "lower", "delta": -200.0}])
    assert r["ok"] and r["verdict"]["objective"] == "min_terminal"
    assert r["verdict"]["best_label"] == "lower"


def test_row_index_defaults_to_highest_baseline() -> None:
    r = _sim(horizon=4)  # no baseline/row_index → engine picks the most-at-risk row
    assert r["ok"] and isinstance(r["row_index"], int)
    # explicitly requesting that row reproduces the same baseline
    r2 = _sim(horizon=4, row_index=r["row_index"])
    assert r2["baseline"] == r["baseline"]


def test_horizon_is_clamped() -> None:
    assert _sim(horizon=10_000, baseline=5.0)["horizon"] == 96
    assert _sim(horizon=0, baseline=5.0)["horizon"] == 1


def test_errors_unknown_spec_and_non_numeric() -> None:
    assert simulate("nope", ENT, ATTR)["ok"] is False
    assert simulate(SPEC, ENT, "status")["ok"] is False  # status is non-numeric


def test_route_runs_and_maps_errors() -> None:
    ok = client.post(f"/api/sim/{SPEC}", json={
        "entity_type": ENT, "attribute": ATTR, "horizon": 12,
        "scenarios": [{"label": "cut", "at": 2, "delta": -3.0, "mode": "shift"}],
    })
    assert ok.status_code == 200
    body = ok.json()
    assert body["ok"] and len(body["trajectories"]) == 2 and "verdict" in body

    assert client.post("/api/sim/does_not_exist", json={"entity_type": ENT, "attribute": ATTR}).status_code == 404
    assert client.post(f"/api/sim/{SPEC}", json={"entity_type": ENT, "attribute": "status"}).status_code == 400
