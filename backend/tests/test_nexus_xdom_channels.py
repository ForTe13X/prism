"""Phase-B.1/B.2 — the THREE independent channels + the honest convergence verdict. These pin: each channel
reads ONLY its own store (shape=series ⊥ fingerprint=histograms ⊥ relational=tags, by construction), all
clear the power floor on HELD-OUT seeds, they are pairwise independent, breaking the coupling collapses
them; the 2-way convergence margin's bootstrap CI STRADDLES 0.05 (indeterminate), but adding the third
INDEPENDENT channel pushes the 3-way margin's whole CI ABOVE 0.05 — and a correlated-placebo control proves
that clear is from INDEPENDENCE, not engineered power."""
from __future__ import annotations

from backend.app.data_package_xdom import generate_xdom
from backend.app.nexus_chan_fingerprint import fingerprint_score
from backend.app.nexus_chan_relational import relational_score
from backend.app.nexus_chan_shape import shape_score
from backend.app.nexus_xdom_eval import run_convergence
from backend.app.nexus_xdom_substrate import candidate_bridges_xdom


def _a_bridge():
    g = generate_xdom("xe-0")
    bridges, _ = candidate_bridges_xdom(g)
    return bridges[0]


# each channel must read ONLY its own store — the three failure domains are disjoint BY CONSTRUCTION. With a
# third store (tags) now riding on the same bridge dict, the tamper tests garble EVERY other store.
def test_shape_channel_reads_only_the_series():
    b = _a_bridge()
    base = shape_score(b)
    tampered = {**b, "a_frame": 99, "b_frame": -3, "a_hist": [9] * len(b["a_hist"]), "b_hist": [0] * len(b["b_hist"]),
                "a_tag_idx": [0, 1, 2], "b_tag_idx": [7, 8, 9]}
    assert shape_score(tampered) == base


def test_fingerprint_channel_reads_only_the_histograms():
    b = _a_bridge()
    base = fingerprint_score(b)
    tampered = {**b, "a_series": [0.0] * len(b["a_series"]), "b_series": [1.0] * len(b["b_series"]),
                "a_frame": 1, "b_frame": 50, "a_tag_idx": [0, 1, 2], "b_tag_idx": [7, 8, 9]}
    assert fingerprint_score(tampered) == base


def test_relational_channel_reads_only_the_tags():
    b = _a_bridge()
    base = relational_score(b)
    tampered = {**b, "a_series": [0.0] * len(b["a_series"]), "b_series": [1.0] * len(b["b_series"]),
                "a_hist": [9] * len(b["a_hist"]), "b_hist": [0] * len(b["b_hist"]), "a_frame": 1, "b_frame": 50}
    assert relational_score(tampered) == base


def test_third_channel_pushes_convergence_stably_over_the_bar():
    # THE HEADLINE POSITIVE: 2 independent channels left convergence INDETERMINATE (CI straddled 0.05);
    # a THIRD genuinely-independent channel (relational, disjoint latent) pushes the 3-way convergence
    # margin's whole 95% CI ABOVE 0.05 — a stable clear, not a coin-flip. The convergent-validity
    # architecture works when the channels are truly independent.
    r = run_convergence()
    assert r["shape_auc"] >= 0.78 and r["fingerprint_auc"] >= 0.78 and r["relational_auc"] >= 0.78
    assert r["checks"]["all_three_clear_power_floor"] is True
    assert r["checks"]["channels_independent"] is True                  # all 3 pairwise corr small (NOT tuned)
    assert r["checks"]["rewire_collapses"] is True                      # break coupling → chance (NOT tuned)
    # 2-way stays indeterminate (its CI straddles the floor) — the honest baseline
    lo2, hi2 = r["margin_bootstrap_ci95"]
    assert lo2 < 0.05 < hi2 and r["checks"]["convergence2_margin"] == "indeterminate_at_0.05_bar"
    # 3-way clears: the entire CI sits above the floor
    lo3, hi3 = r["margin3_bootstrap_ci95"]
    assert lo3 >= 0.05 and r["margin3_straddles_floor"] is False
    assert r["checks"]["convergence3_margin"] == "clears_0.05"
    assert r["convergence3_auc"] > r["convergence_auc"]                 # the 3rd vote genuinely adds signal
    assert r["outcome"] == "three_independent_channels__3way_convergence_clears_0.05"
    # ANTI-REVERSE-TRAP CONTROL: a CORRELATED third channel of similar power does NOT clear the bar — so the
    # clear is from INDEPENDENCE, not engineered power.
    assert r["correlated_placebo_3way_margin"] < r["convergence3_margin_point"]
    assert r["clear_is_from_independence_not_power"] is True


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
