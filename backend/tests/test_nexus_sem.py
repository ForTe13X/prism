"""Nexus M1 — the time-free SEMANTIC lens (METRIC §8 honest positive). These pin the panel-vetted facts:
the lens is genuinely time-free (never reads a frame), it wins at L1–L3/L5, it concedes L4 (below chance —
the honest negative IS the contribution), and dealiasing beats naive string matching under corruption at
L2/L3 (the real structural content). ΔL is a valid Kraft code; its distinctiveness weighting is a DIFFERENT
ranking from raw overlap (asserted below), so we never claim they coincide."""
from __future__ import annotations

from backend.app.data_package import generate
from backend.app.nexus_lens_sem import run_sem_lens, score_bridges
from backend.app.nexus_substrate import candidate_bridges

SEEDS = [f"nx-{i}" for i in range(40)]


def _rows(source_id="logistics_demo"):
    return {(r["dirt"], r["link"]): r for r in run_sem_lens(source_id, seeds=SEEDS)["rows"]}


def test_lens_is_time_free():
    # the load-bearing honesty: ΔL must not move when EVERY temporal surface the scorer could reach is
    # corrupted — the per-bridge frame fields AND ctx's anomaly/depth maps AND a bogus frame on each hub
    # row. If a future edit leaks time through any of these, this fence fails.
    pkg = generate("logistics_demo", dirtiness=0.3, link_explicitness=2, seed="nx-0")
    bridges, ctx = candidate_bridges(pkg)
    base = [b["delta_l_sem"] for b in score_bridges(bridges, ctx)]
    tampered_bridges = [{**b, "news_frame": 999, "anomaly_frame": -7, "dframe": 123} for b in bridges]
    tampered_ctx = {**ctx, "anomalies": {}, "depth": {},
                    "hubs": {hid: {**h, "frame": 12345, "anomaly_frame": -1} for hid, h in ctx["hubs"].items()}}
    after = [b["delta_l_sem"] for b in score_bridges(tampered_bridges, tampered_ctx)]
    assert base == after


def test_kraft_p_is_valid_probability():
    pkg = generate("logistics_demo", dirtiness=0.0, link_explicitness=1, seed="nx-0")
    bridges, ctx = candidate_bridges(pkg)
    for b in score_bridges(bridges, ctx):
        assert b["delta_l_sem"] >= 0.0
        assert 0.0 <= b["p_sem"] < 1.0
        assert b["sem_overlap"] >= 0


def test_wins_at_explicit_and_semantic_links():
    rows = _rows()
    assert rows[(0.0, 1)]["auc_deltaL_dealias_on"] > 0.95   # literal id → near perfect
    assert rows[(0.0, 2)]["auc_deltaL_dealias_on"] > 0.95
    assert rows[(0.0, 3)]["auc_deltaL_dealias_on"] > 0.7    # region token still discriminates
    assert rows[(0.0, 5)]["auc_deltaL_dealias_on"] > 0.7    # port named (semantic-ish)


def test_l4_is_an_honest_below_chance_negative():
    # L4 names no hub but distractors still name their own region → the lens honestly mis-ranks → AUC<0.5.
    # This negative IS the contribution: the lens measures non-temporal structure, not laundered time.
    r = _rows()[(0.0, 4)]
    assert r["auc_deltaL_dealias_on"] < 0.5
    assert r["time_free_gate_pass"] is False


def test_dealias_beats_naive_string_under_dirt():
    # THE HEADLINE POSITIVE: under corruption, folding alias/garble variants back (dealias ON) recovers
    # co-occurrence that raw substring matching (OFF) loses — a real, non-temporal robustness margin.
    rows = _rows()
    gaps = [rows[(0.5, link)]["dealias_robustness_gap"] for link in (2, 3)]
    assert max(gaps) > 0.05                                # dealias clearly helps where region aliasing bites
    assert rows[(0.5, 2)]["auc_deltaL_dealias_on"] >= rows[(0.5, 2)]["auc_deltaL_dealias_off"]


def test_deltaL_ranking_differs_from_raw_overlap():
    # HONESTY: ΔL (distinctiveness-weighted) is NOT the same ranking as equal-weight overlap. On this
    # substrate raw overlap actually edges ΔL at L3 — we report both rather than claim they coincide.
    r = _rows()[(0.0, 3)]
    assert r["auc_overlap_dealias_on"] > r["auc_deltaL_dealias_on"]


def test_deterministic_and_role_generic():
    a = run_sem_lens("logistics_demo", seeds=SEEDS[:12])
    b = run_sem_lens("logistics_demo", seeds=SEEDS[:12])
    assert a == b
    e = _rows("energy_demo")
    assert e[(0.0, 1)]["auc_deltaL_dealias_on"] > 0.9        # the lens transfers to the 2nd domain
    assert e[(0.0, 4)]["auc_deltaL_dealias_on"] < 0.5        # same honest L4 negative


def test_api_sem_lens():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    r = client.get("/api/nexus/logistics_demo/sem")
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body and "caveat" in body and any(not row["time_free_gate_pass"] for row in body["rows"])
    assert client.get("/api/nexus/nope/sem").status_code == 404
