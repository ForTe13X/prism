"""Sequential what-if / policy comparison engine. Self-contained: calls evaluate() directly with a
controlled baseline for deterministic robustness checks, and exercises the wired route via the real
app. Target: infra_monitoring / station / pressure (gauge, range [0,12], threshold limit 10)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.policy import evaluate

client = TestClient(app)
SPEC, ENT, ATTR = "infra_monitoring", "station", "pressure"

# a relief policy: when pressure reaches 9, latch a setpoint cut of 30% of span
RELIEF = {"label": "relief", "rules": [{"when": {"op": ">=", "value": 9}, "do": {"action": "shift", "by": -0.3}}]}


def _ev(**kw):
    return evaluate(SPEC, ENT, ATTR, **kw)


def test_deterministic_byte_identical() -> None:
    a = _ev(horizon=20, baseline=8.0, policies=[RELIEF])
    b = _ev(horizon=20, baseline=8.0, policies=[RELIEF])
    assert a == b


def test_baseline_prepended_and_shape() -> None:
    r = _ev(horizon=12, baseline=7.0, policies=[RELIEF])
    assert r["ok"] and [p["label"] for p in r["policies"]] == ["baseline", "relief"]
    base = r["policies"][0]
    assert [f["f"] for f in base["frames"]] == list(range(13))
    f0 = base["frames"][0]
    assert f0["lo"] == f0["mid"] == f0["hi"] == 7.0  # frame 0 collapses to baseline


def test_band_ordered_everywhere() -> None:
    r = _ev(horizon=24, baseline=8.5, policies=[RELIEF])
    for p in r["policies"]:
        for fr in p["frames"]:
            assert fr["lo"] <= fr["mid"] <= fr["hi"]


def test_relief_policy_lowers_breach_rate_vs_baseline() -> None:
    # start above the warn line so the rule fires; a latched -30% cut should breach less than no policy
    r = _ev(horizon=24, baseline=9.5, policies=[RELIEF])
    base = next(p for p in r["policies"] if p["label"] == "baseline")
    relief = next(p for p in r["policies"] if p["label"] == "relief")
    assert relief["breach_rate"] <= base["breach_rate"]
    assert relief["worst_terminal"] <= base["worst_terminal"]


def test_common_random_numbers_baseline_no_rules_equals_plain_roll() -> None:
    # two policies that never fire (impossible trigger) must match baseline exactly (shared shocks)
    never = {"label": "never", "rules": [{"when": {"op": ">=", "value": 999}, "do": {"action": "shift", "by": -0.5}}]}
    r = _ev(horizon=16, baseline=6.0, policies=[never])
    base = next(p for p in r["policies"] if p["label"] == "baseline")
    nev = next(p for p in r["policies"] if p["label"] == "never")
    assert [f["mid"] for f in base["frames"]] == [f["mid"] for f in nev["frames"]]


def test_verdict_picks_lowest_breach_rate() -> None:
    r = _ev(horizon=24, baseline=9.5, policies=[RELIEF])
    metrics = r["verdict"]["metrics"]
    best = r["verdict"]["best_label"]
    assert r["verdict"]["objective"] == "avoid_breach"
    assert metrics[best]["breach_rate"] == min(m["breach_rate"] for m in metrics.values())


def test_sensitivity_reports_stability() -> None:
    r = _ev(horizon=24, baseline=9.5, policies=[RELIEF])
    s = r["sensitivity"]
    assert isinstance(s["stable"], bool)
    assert s["best_label_perturbed"] in {p["label"] for p in r["policies"]}
    assert s["perturbed"]["rate"] <= r["dynamics"]["rate"]  # harsher world = weaker reversion


def test_no_threshold_uses_min_terminal_objective() -> None:
    r = evaluate(SPEC, ENT, "throughput", horizon=8, baseline=500.0,
                 policies=[{"label": "lower", "rules": [{"when": {"op": ">=", "value": 400}, "do": {"action": "shift", "by": -0.4}}]}])
    assert r["ok"] and r["verdict"]["objective"] == "min_terminal"


def test_assumptions_override_changes_dynamics() -> None:
    r = _ev(horizon=8, baseline=8.0, policies=[RELIEF], assumptions={"rate": 0.5})
    assert r["dynamics"]["rate"] == 0.5


def test_duplicate_and_reserved_labels_are_deduped() -> None:
    # two user policies named the same — and one colliding with the reserved "baseline" — must NOT
    # collapse the label-keyed metrics; each gets a unique label and the winner is attributed right
    r = _ev(horizon=12, baseline=9.5, policies=[
        {"label": "baseline", "rules": [{"when": {"op": ">=", "value": 9}, "do": {"action": "shift", "by": -0.4}}]},
        {"label": "plan", "rules": []},
        {"label": "plan", "rules": [{"when": {"op": ">=", "value": 9}, "do": {"action": "shift", "by": -0.5}}]},
    ])
    labels = [p["label"] for p in r["policies"]]
    assert labels[0] == "baseline" and len(set(labels)) == len(labels)  # all unique, real baseline kept
    assert len(r["verdict"]["metrics"]) == len(r["policies"])  # nothing collapsed


def test_no_threshold_reason_discloses_direction_assumption() -> None:
    r = evaluate(SPEC, ENT, "throughput", horizon=8, baseline=500.0,
                 policies=[{"label": "lower", "rules": [{"when": {"op": ">=", "value": 400}, "do": {"action": "shift", "by": -0.4}}]}])
    assert r["verdict"]["objective"] == "min_terminal"
    assert "越低越好" in r["verdict"]["reason"]  # the unstated direction assumption is disclosed


def test_non_finite_baseline_rejected() -> None:
    assert evaluate(SPEC, ENT, ATTR, baseline=float("nan"))["ok"] is False
    assert evaluate(SPEC, ENT, ATTR, baseline=float("inf"))["ok"] is False


def test_errors_unknown_spec_and_non_numeric() -> None:
    assert evaluate("nope", ENT, ATTR)["ok"] is False
    assert evaluate(SPEC, ENT, "status")["ok"] is False


def test_route_runs_and_maps_errors() -> None:
    ok = client.post(f"/api/policy/{SPEC}", json={
        "entity_type": ENT, "attribute": ATTR, "horizon": 16,
        "policies": [{"label": "relief", "rules": [{"when": {"op": ">=", "value": 9}, "do": {"action": "shift", "by": -0.3}}]}],
    })
    assert ok.status_code == 200
    body = ok.json()
    assert body["ok"] and body["policies"][0]["label"] == "baseline" and "sensitivity" in body and "verdict" in body

    assert client.post("/api/policy/does_not_exist", json={"entity_type": ENT, "attribute": ATTR}).status_code == 404
    assert client.post(f"/api/policy/{SPEC}", json={"entity_type": ENT, "attribute": "status"}).status_code == 400
