"""P1 endpoints end-to-end: /api/timeline and /api/data?frame=N, including determinism & clamping."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_timeline_returns_axis() -> None:
    r = client.get("/api/timeline/infra_monitoring")
    assert r.status_code == 200
    body = r.json()
    assert body["spec_id"] == "infra_monitoring"
    assert body["frames"] == 48 and body["now"] == 36 and body["step"] == "hour"


def test_timeline_unknown_spec_404() -> None:
    assert client.get("/api/timeline/does_not_exist").status_code == 404


def test_data_echoes_resolved_frame_and_defaults_to_now() -> None:
    # no frame param → backend resolves to `now`
    r = client.get("/api/data/infra_monitoring/station")
    assert r.status_code == 200
    assert r.json()["frame"] == 36


def test_data_frame_is_deterministic() -> None:
    a = client.get("/api/data/infra_monitoring/station?frame=20")
    b = client.get("/api/data/infra_monitoring/station?frame=20")
    assert a.status_code == 200
    assert a.json() == b.json()


def test_data_different_frames_differ() -> None:
    a = client.get("/api/data/infra_monitoring/station?frame=5").json()["rows"]
    b = client.get("/api/data/infra_monitoring/station?frame=45").json()["rows"]
    assert a != b


def test_data_clamps_out_of_range_frame() -> None:
    assert client.get("/api/data/infra_monitoring/station?frame=-3").json()["frame"] == 0
    assert client.get("/api/data/infra_monitoring/station?frame=99999").json()["frame"] == 47


def test_data_non_evolving_attr_stable_across_frames() -> None:
    lo = client.get("/api/data/infra_monitoring/station?frame=0").json()["rows"]
    hi = client.get("/api/data/infra_monitoring/station?frame=47").json()["rows"]
    # 'region' and 'name' carry no evolves → identical row-for-row
    assert [r["region"] for r in lo] == [r["region"] for r in hi]
    assert [r["name"] for r in lo] == [r["name"] for r in hi]


def test_data_unknown_spec_and_entity() -> None:
    assert client.get("/api/data/nope/station").status_code == 404
    assert client.get("/api/data/infra_monitoring/nope").status_code == 404


def test_both_domains_have_a_working_axis() -> None:
    # domain-agnostic: the second domain exposes its own (different) axis with no code change
    lib = client.get("/api/timeline/library_catalog").json()
    assert lib["frames"] == 30 and lib["step"] == "day"
    rows0 = client.get("/api/data/library_catalog/book?frame=0").json()["rows"]
    rows29 = client.get("/api/data/library_catalog/book?frame=29").json()["rows"]
    assert any(a["availability"] != b["availability"] for a, b in zip(rows0, rows29))
