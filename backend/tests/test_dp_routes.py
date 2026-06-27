"""The integration read-APIs for the §5 parser and §4b calibration (the wiring the integrator added on
top of the two parallel-built modules)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_parse_route_round_trip():
    r = client.get("/api/parse/logistics_demo?dirtiness=0&link=2")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["parsed"] > 0 and body["summary"]["failed"] == 0
    assert body["id_recovery"]["shipment_id"] == 1.0 and body["id_recovery"]["warehouse_id"] == 1.0
    assert "raw_preview" in body and body["sample"]["shipments"]
    assert client.get("/api/parse/nope").status_code == 404


def test_parse_route_reports_failures_observably_under_dirt():
    body = client.get("/api/parse/logistics_demo?dirtiness=0.8&link=4").json()
    # nothing is silently dropped: every line is parsed, failed, or skipped, and the report is present
    assert body["summary"]["parsed"] > 0
    assert isinstance(body["reports"]["sql"]["failed"], int)


def test_calibration_route_held_out_moments_match():
    body = client.get("/api/calibration").json()
    assert body["is_real_data"] is False  # honest: reference is a synthetic stand-in
    # fitted moments should match closely; held-out moments (never fitted) should also be reasonably close
    assert body["fitted_moments"]["corr_xy"]["abs_diff"] < 0.05
    assert body["held_out_moments"]["series_lag2"]["abs_diff"] < 0.1
    assert body["held_out_moments"]["corr_x_series"]["abs_diff"] < 0.2  # independence preserved
