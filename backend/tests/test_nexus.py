"""Nexus M0 (METRIC_nexus_reality Phase A foundation) — the eval primitives are correct, and the baseline
ladder honestly QUANTIFIES THE BAR. The headline finding this pins: on the current substrate the
time-coincidence baseline is near-ceiling at every link level (the real bridge IS a temporal coincidence
by construction), while the string baselines collapse as the link is hidden. That bar is what any future
lens must strictly beat — and these tests make the bar a regression-guarded fact, not a hope."""
from __future__ import annotations

from backend.app.nexus_eval import (
    average_precision, discrimination_sweep, ece, negative_controls, roc_auc, run_baseline_ladder,
)
from backend.app.nexus_substrate import candidate_bridges, labelled_bridges
from backend.app.data_package import generate

SEEDS = [f"nx-{i}" for i in range(40)]  # pool: only ~2 positives/package, AUC quantizes in 1/22 steps


# --- eval primitives ---
def test_roc_auc_separation_and_ties():
    assert roc_auc([1, 2, 3, 4], [0, 0, 1, 1]) == 1.0          # perfect separation
    assert roc_auc([4, 3, 2, 1], [0, 0, 1, 1]) == 0.0          # perfectly reversed
    assert roc_auc([1, 1, 1, 1], [0, 1, 0, 1]) == 0.5          # all tied → chance
    assert roc_auc([5, 5, 1, 1], [1, 1, 0, 0]) == 1.0          # tied within class, separated across
    assert roc_auc([1, 2, 3], [0, 0, 0]) == 0.5                # one class absent → chance


def test_average_precision():
    assert average_precision([4, 3, 2, 1], [1, 1, 0, 0]) == 1.0   # all positives ranked first
    assert average_precision([1, 2, 3, 4], [1, 1, 0, 0]) < 1.0    # positives ranked last
    assert average_precision([1, 2, 3], [0, 0, 0]) == 0.0         # no positives


def test_ece_perfectly_calibrated_is_zero():
    probs = [0.0, 0.0, 1.0, 1.0]
    labels = [0, 0, 1, 1]
    assert ece(probs, labels) == 0.0


# --- the bridge substrate ---
def test_candidate_bridges_labelled_and_observation_only():
    pkg = generate("logistics_demo", dirtiness=0.0, link_explicitness=4, seed="nx-0")
    bridges, ctx = candidate_bridges(pkg)
    assert bridges and any(b["label"] == "real" for b in bridges)
    assert any(b["label"] == "coincidence" for b in bridges)     # hard temporal negatives present
    # a scorer must never see ground-truth leakage on a bridge
    for b in bridges:
        assert "_truth_event" not in b and set(b["hub"]) <= {"id", "name", "region", "port"}
        assert b["y"] == (1 if b["label"] == "real" else 0)


# --- the HONEST FINDING: the bar is near-ceiling, strings collapse ---
def test_time_coincidence_is_the_near_ceiling_bar():
    L = run_baseline_ladder("logistics_demo", seeds=SEEDS, link=4, dirt=0.0)
    assert L["bar_to_beat"]["name"] == "time_coincidence"
    assert L["baselines"]["time_coincidence"]["auc"] > 0.9       # time nearly solves it on clean data
    assert 0.2 < L["prevalence"] < 0.45                          # a non-degenerate real/coincidence mix


def test_time_bar_stays_high_even_under_dirt():
    # news-time corruption only nudges frames ±1–2, so time barely degrades — the honest reason the
    # lenses have little room on THIS substrate (the §6c trap, made measurable).
    clean = run_baseline_ladder("logistics_demo", seeds=SEEDS, link=4, dirt=0.0)["baselines"]["time_coincidence"]["auc"]
    dirty = run_baseline_ladder("logistics_demo", seeds=SEEDS, link=4, dirt=0.95)["baselines"]["time_coincidence"]["auc"]
    assert dirty > 0.85 and clean - dirty < 0.15


def test_string_baselines_collapse_as_link_is_hidden():
    sweep = {r["link"]: r for r in discrimination_sweep("logistics_demo", seeds=SEEDS, dirt=0.0)["sweep"]}
    assert sweep[1]["string_jaccard"] > 0.95                     # literal ids → trivial at L1
    assert sweep[4]["string_jaccard"] < 0.5                      # collapses where the link is hidden


def test_negative_controls_behave():
    nc = negative_controls("logistics_demo", seeds=SEEDS, link=4, dirt=0.0)["controls"]
    assert nc["distractor_only"]["n_real"] == 0                  # no real bridges among distractors
    # breaking the real chains (rewire) must drop the time signal below the intact-chain bar
    intact = run_baseline_ladder("logistics_demo", seeds=SEEDS, link=4, dirt=0.0)["baselines"]["time_coincidence"]["auc"]
    assert nc["rewire"]["baselines"]["time_coincidence"]["auc"] < intact


def test_deterministic():
    a = run_baseline_ladder("logistics_demo", seeds=SEEDS, link=4, dirt=0.3)
    b = run_baseline_ladder("logistics_demo", seeds=SEEDS, link=4, dirt=0.3)
    assert a == b


def test_second_domain_also_enumerates():
    # the substrate adapter is role-generic, so energy produces a labelled bridge set too
    br = labelled_bridges("energy_demo", seeds=SEEDS[:8], link=4, dirt=0.0)
    assert br and any(b["label"] == "real" for b in br) and any(b["label"] == "coincidence" for b in br)


def test_api_nexus_baselines_sweep_controls_and_404():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    b = client.get("/api/nexus/logistics_demo/baselines?link=4&dirt=0")
    assert b.status_code == 200
    body = b.json()
    assert body["bar_to_beat"]["name"] == "time_coincidence" and body["bar_to_beat"]["auc"] > 0.9
    assert "caveat" in body                                       # the un-removable honesty caveat
    assert client.get("/api/nexus/logistics_demo/sweep").status_code == 200
    assert client.get("/api/nexus/logistics_demo/controls").status_code == 200
    assert client.get("/api/nexus/nope/baselines").status_code == 404
