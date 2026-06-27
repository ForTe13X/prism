"""Phase-B.1 — the two independent channels + the honest convergence verdict. These pin: each channel reads
ONLY its own store (shape⊥fingerprint by construction), both clear the pre-registered power floor on
HELD-OUT seeds, they are independent, breaking the coupling collapses them, and — the honest headline — the
convergence margin falls SHORT of the +0.05 'clean 2/2' bar, so the system reports the modest-convergence
outcome rather than an unqualified 2/2."""
from __future__ import annotations

from backend.app.data_package_xdom import generate_xdom
from backend.app.nexus_chan_fingerprint import fingerprint_score
from backend.app.nexus_chan_shape import shape_score
from backend.app.nexus_xdom_eval import run_convergence
from backend.app.nexus_xdom_substrate import candidate_bridges_xdom


def _a_bridge():
    g = generate_xdom("xe-0")
    bridges, _ = candidate_bridges_xdom(g)
    return bridges[0]


def test_shape_channel_reads_only_the_series():
    b = _a_bridge()
    base = shape_score(b)
    # mutate every NON-series field (frames, histograms, ids) — the shape score must not move
    tampered = {**b, "a_frame": 99, "b_frame": -3, "a_hist": [9] * len(b["a_hist"]), "b_hist": [0] * len(b["b_hist"])}
    assert shape_score(tampered) == base


def test_fingerprint_channel_reads_only_the_histograms():
    b = _a_bridge()
    base = fingerprint_score(b)
    tampered = {**b, "a_series": [0.0] * len(b["a_series"]), "b_series": [1.0] * len(b["b_series"]),
                "a_frame": 1, "b_frame": 50}
    assert fingerprint_score(tampered) == base


def test_convergence_margin_is_honestly_indeterminate_on_held_out_seeds():
    # THE HONEST HEADLINE: both channels are informative (engineered) and independent + rewire-collapse
    # (not tuned), convergence beats both singles — but the margin's 95% bootstrap CI STRADDLES the 0.05
    # clean-2/2 floor, so whether it clears the bar is statistically indeterminate (within sampling noise),
    # not a confident near-miss. The system reports that, not a rounded-up 2/2.
    r = run_convergence()
    assert r["shape_auc"] >= 0.78 and r["fingerprint_auc"] >= 0.78      # both informative (engineered)
    assert r["checks"]["channels_independent"] is True                  # corr small (NOT tuned)
    assert r["checks"]["rewire_collapses"] is True                      # break coupling → chance (NOT tuned)
    assert r["convergence_auc"] > max(r["shape_auc"], r["fingerprint_auc"])  # convergence does help...
    lo, hi = r["margin_bootstrap_ci95"]
    assert lo < 0.05 < hi and r["margin_straddles_floor"] is True       # ...but the CI straddles the floor
    assert r["checks"]["convergence_margin"] == "indeterminate_at_0.05_bar"
    assert r["outcome"].endswith("indeterminate_at_0.05_bar")


def test_rewire_control_collapses_both_channels():
    r = run_convergence()
    assert all(v <= 0.60 for v in r["rewire_control"].values())


def test_deterministic():
    assert run_convergence(["xe-0", "xe-1", "xe-2"]) == run_convergence(["xe-0", "xe-1", "xe-2"])


def test_api_xdom_channels():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    r = client.get("/api/nexus_xdom/channels")
    assert r.status_code == 200
    body = r.json()
    assert "outcome" in body and "honest_verdict" in body and body["checks"]["channels_independent"] is True
