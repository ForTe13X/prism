"""Cross-domain Sinkhorn alignment — the money-moment engine + a global-assignment signal. These pin: the
residual converges monotonically (the curve that pulls the galaxies together), the transport plan respects
the mutual-exclusivity marginals, and that exclusivity lets the transport recover the coupling MORE sharply
than any per-bridge channel (measured, like Phase-A's axiom exclusivity). Deterministic."""
from __future__ import annotations

from backend.app.nexus_xdom_align import REG, run_alignment, run_alignment_eval, sinkhorn


def test_residual_converges_monotonically():
    a = run_alignment("xe-0")
    r = a["residuals"]
    assert len(r) == a["iters"]
    assert all(r[i] >= r[i + 1] - 1e-9 for i in range(len(r) - 1))   # monotone non-increasing
    assert r[0] > r[-1] and r[-1] < 0.01                             # it actually converges
    assert len(a["snapshots"]) >= 8 and a["snapshots"][0]["iter"] == 0


def test_transport_respects_exclusivity_marginals():
    # the u-update makes every row (each A anchor) sum to the uniform marginal 1/n — that's the mutual
    # exclusivity a per-bridge score lacks.
    a = run_alignment("xe-1")
    n = a["n_anchor_a"]
    by_a: dict = {}
    for p in a["pairs"]:
        by_a.setdefault(p["a_idx"], 0.0)
        by_a[p["a_idx"]] += p["transport"]
    for total in by_a.values():
        assert abs(total - 1.0 / n) < 1e-3                           # each A unit's mass ≈ 1/n


def test_transport_recovers_coupling_better_than_single_channels():
    e = run_alignment_eval()
    assert e["auc"]["transport"] > 0.9                               # the global assignment is sharp
    assert e["transport_beats_best_single"] is True                  # ...beating every per-bridge channel
    assert e["margin_over_best_single"] > 0.05
    assert e["n_positives"] >= 100


def test_sinkhorn_basic_and_deterministic():
    # a tiny hand cost: the diagonal is cheap → transport concentrates on the diagonal
    cost = [[0.0, 1.0], [1.0, 0.0]]
    sk = sinkhorn(cost, reg=REG, iters=40)
    assert sk["T"][0][0] > sk["T"][0][1] and sk["T"][1][1] > sk["T"][1][0]
    assert sinkhorn(cost) == sinkhorn(cost)                          # deterministic
    assert run_alignment("xe-2") == run_alignment("xe-2")
    assert sinkhorn([], iters=5) == {"T": [], "residuals": [], "snapshots": []}  # empty guard


def test_api_align():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    r = client.get("/api/nexus_xdom/align?seed=xe-0")
    assert r.status_code == 200
    body = r.json()
    assert "residuals" in body and "snapshots" in body and "pairs" in body
    e = client.get("/api/nexus_xdom/align_eval")
    assert e.status_code == 200 and e.json()["transport_beats_best_single"] is True
