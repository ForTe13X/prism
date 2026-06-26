"""DP1 cross-source data package — the invariants the axiom-gain benchmark depends on: deterministic
generation, ground-truth preserved under the dirtiness/link knobs, the link-explicitness knob actually
hides the keys, the discriminative interval (naive << linked once links are non-explicit), and the
dirtiness robustness curve. Plus the SQL store materializes to a real, queryable SQLite db."""
from __future__ import annotations

import json
import os
import tempfile

from fastapi.testclient import TestClient

from backend.app.data_package import _build_truth, _throughput, generate, to_sqlite
from backend.app.data_package_eval import (
    _anomaly_frames, evaluate, linked_solve, naive_solve, observation_view, oracle_solve, score,
)
from backend.app.main import app

client = TestClient(app)
SID = "logistics_demo"


def _canon(pkg):
    return json.dumps(pkg, ensure_ascii=False, sort_keys=True)


def test_deterministic_byte_identical():
    assert _canon(generate(SID, dirtiness=0.4, link_explicitness=3)) == _canon(generate(SID, dirtiness=0.4, link_explicitness=3))


def test_ground_truth_preserved_across_knobs():
    # the ANSWERS (the truth) must not change with dirtiness or link-explicitness — only observations do
    base = generate(SID, dirtiness=0.0, link_explicitness=4)["ground_truth"]["answers"]
    for d in (0.3, 0.8):
        for link in (1, 5):
            assert generate(SID, dirtiness=d, link_explicitness=link)["ground_truth"]["answers"] == base


def test_events_are_non_degenerate():
    evs = generate(SID)["ground_truth"]["events"]
    assert len(evs) >= 2 and all(len(e["shipment_ids"]) >= 1 for e in evs)


def test_link_explicitness_hides_keys():
    # L1 news bodies literally contain warehouse/shipment ids; L4 must NOT
    l1 = " ".join(n["body"] for n in generate(SID, link_explicitness=1)["stores"]["news"])
    l4 = " ".join(n["body"] for n in generate(SID, link_explicitness=4)["stores"]["news"])
    assert ("WH-" in l1 or "SHP-" in l1)
    assert "WH-" not in l4 and "SHP-" not in l4


def test_oracle_recovers_then_naive_fails_but_linked_recovers():
    # discriminative interval: at L4 a literal/single-source solver is helpless; the cross-source
    # solver still recovers most of the truth (the task genuinely needs cross-source reasoning)
    pkg = generate(SID, dirtiness=0.0, link_explicitness=4)
    obs, truth = observation_view(pkg), oracle_solve(pkg, "explain_delays")
    assert score(oracle_solve(pkg, "explain_delays"), truth)["f1"] == 1.0  # oracle = ceiling
    assert score(naive_solve(obs, "explain_delays"), truth)["f1"] == 0.0  # naive collapses
    assert score(linked_solve(obs, "explain_delays"), truth)["f1"] >= 0.6  # linked recovers


def test_explicit_link_is_trivial_for_naive():
    # at L1 the literal-key naive solver is perfect — the fancy reasoner isn't needed when keys are explicit
    pkg = generate(SID, dirtiness=0.0, link_explicitness=1)
    obs, truth = observation_view(pkg), oracle_solve(pkg, "explain_delays")
    assert score(naive_solve(obs, "explain_delays"), truth)["f1"] == 1.0


def test_dirtiness_degrades_linked_robustness_curve():
    clean = evaluate(generate(SID, dirtiness=0.0, link_explicitness=4))["linked_f1"]
    dirty = evaluate(generate(SID, dirtiness=0.8, link_explicitness=4))["linked_f1"]
    assert clean > dirty  # accuracy degrades with dirtiness — the robustness signal


def test_dirtiness_records_recovery_map_but_not_truth():
    pkg = generate(SID, dirtiness=0.9, link_explicitness=4)
    cmap = pkg["corruption_map"]
    assert any(cmap[k] for k in ("aliases", "weight_lb_ids", "status_nulled_ids", "news_time_offset", "garbled_news"))
    # a nulled status is an OBSERVATION change; the ground-truth shipment still appears in the answers
    nulled = set(cmap["status_nulled_ids"])
    truth_ships = {s for ships in pkg["ground_truth"]["answers"]["explain_delays"].values() for s in ships}
    obs_ships = {s["id"] for s in pkg["stores"]["sql"]["shipments"]}
    assert truth_ships <= obs_ships  # the rows still exist, only their observed status was nulled
    assert isinstance(nulled, set)


def test_sqlite_materializes_and_queries():
    pkg = generate(SID, dirtiness=0.0, link_explicitness=4)
    import sqlite3

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "pkg.db")
        to_sqlite(pkg, path)
        con = sqlite3.connect(path)
        try:
            n = con.execute("SELECT COUNT(*) FROM shipment").fetchone()[0]
            joined = con.execute(
                "SELECT s.id FROM shipment s JOIN warehouse w ON s.warehouse_id=w.id WHERE s.status='delayed'"
            ).fetchall()
        finally:
            con.close()
        assert n == pkg["manifest"]["counts"]["shipments"]
        assert len(joined) >= 2  # the delayed shipments are queryable via a real SQL join


def test_events_distinct_and_anomalies_materialized_even_when_ngt_equals_nw():
    # the keystone: build truth, then materialize stores consistent with it. Even with one event per
    # warehouse (ngt == nw), event warehouses must be DISTINCT and each event's frame must show a real
    # throughput dip (so no ground-truth row is left unobservable).
    p = {"warehouses": 3, "carriers": 2, "shipments": 18, "frames": 60, "news_events": 5,
         "ground_truth_events": 3, "delay_window": 4}
    wh, _cr, _sh, truth = _build_truth("seedX", p, ["A", "B", "C"], ["P", "Q", "R"])
    wids = [e["warehouse_id"] for e in truth["events"]]
    assert len(wids) == len(set(wids)) == 3  # distinct warehouses, no collision
    anom = _anomaly_frames({"throughput": _throughput("seedX", wh, truth), "frames": truth["frames"]})
    for e in truth["events"]:
        assert e["warehouse_id"] in anom and abs(anom[e["warehouse_id"]] - e["frame"]) <= 2  # dip at the event frame
        assert len(e["shipment_ids"]) >= 1


def test_anomaly_cause_scoring_is_shape_aware():
    # the dict-of-dicts answer must score its VALUES, not just field names
    pkg = generate(SID)
    ans = oracle_solve(pkg, "anomaly_cause")
    assert ans and score(ans, ans)["f1"] == 1.0
    import copy

    wrong = copy.deepcopy(ans)
    k = next(iter(wrong))
    wrong[k] = {"frame": wrong[k]["frame"] + 99, "news": wrong[k]["news"]}
    assert score(wrong, ans)["f1"] < 1.0  # a wrong frame is actually penalized


def test_api_inspect_and_discriminability():
    r = client.get(f"/api/datapackage/{SID}?dirtiness=0&link=4")
    assert r.status_code == 200
    body = r.json()
    assert body["manifest"]["counts"]["ground_truth_events"] >= 2
    assert body["evaluate"]["naive_f1"] == 0.0 and body["evaluate"]["linked_f1"] >= 0.6

    d = client.get(f"/api/datapackage/{SID}/discriminability").json()
    assert len(d["link_sweep"]) == 5 and len(d["dirtiness_sweep"]) == 6
    assert d["link_sweep"][0]["link"] == 1
    # at L>=2 the gap (linked − naive) opens up
    assert all(row["gap"] >= 0.5 for row in d["link_sweep"] if row["link"] >= 2)

    assert client.get("/api/datapackage/nope").status_code == 404
