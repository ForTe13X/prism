"""Track 1 (§4b) — calibrate the substrate's OBSERVABLE marginals to REAL data, verify on HELD-OUT moments,
re-run the gate + convergence. These pin the honesty contract: cal=None is byte-identical to the frozen
substrate; the calibrated marginals match the held-out real aggregates (verified, not claimed); and the
honest external-validity outcome — under real-data noise the time-series channel collapses to chance and
3-way convergence no longer clears, while the gate still passes (the substrate stays well-posed)."""
from __future__ import annotations

import math

import pytest

from backend.app.data_package_xdom import KNOBS, generate_xdom
from backend.app.nexus_xdom_calibrate import (
    FROZEN_DROP_FRAC,
    VERDICT_COLLAPSES,
    _load_real_columns,
    _split,
    calibrated_knobs,
    fit_aggregates,
    run_calibration,
)
from backend.app.nexus_xdom_gate import run_gate

sklearn = pytest.importorskip("sklearn")  # Track 1 needs genuine real data; never fabricated


def test_cal_none_is_byte_identical_to_frozen():
    # the calibration plumbing is additive: with no calibration the substrate must be EXACTLY the frozen one
    for sd in ("xe-0", "xd-3", "xe-17"):
        assert generate_xdom(sd, None) == generate_xdom(sd)


def test_calibrated_knobs_map_aggregates_faithfully():
    agg = {"metric_mean": 14.0, "metric_std": 3.0, "attr_props": [0.5, 0.3, 0.2]}
    cal = calibrated_knobs(agg)
    assert cal["base"] == 14.0
    assert abs(cal["wiggle"] - 3.0 * math.sqrt(3.0)) < 1e-6      # observable baseline std = σ
    assert abs(cal["depth"] - FROZEN_DROP_FRAC * 14.0) < 1e-6    # designed relative dip, scaled by μ
    assert len(cal["attr_logits"]) == 3
    # effect_scale multiplies only the dip (the coupling signal), not the marginal
    assert abs(calibrated_knobs(agg, effect_scale=2.0)["depth"] - 2.0 * cal["depth"]) < 1e-6


def test_effect_scale_leaves_marginals_fixed():
    agg = {"metric_mean": 9.0, "metric_std": 2.0, "attr_props": [0.4, 0.6]}
    a, b = calibrated_knobs(agg, 1.0), calibrated_knobs(agg, 3.0)
    assert a["base"] == b["base"] and a["wiggle"] == b["wiggle"] and a["attr_logits"] == b["attr_logits"]


def test_fitted_aggregates_pinned_to_frozen_real_values():
    # guard against silent upstream drift in the bundled dataset: the calibrated KNOBS are a deterministic
    # function of these exact aggregates, so any change must fail loudly here (not silently re-calibrate).
    m_all, a_all = _load_real_columns()  # also asserts the (569, 30) shape guard internally
    m_tr, a_tr = _split(m_all)[0], _split(a_all)[0]
    agg = fit_aggregates(m_tr, a_tr, KNOBS["n_cats"], min(a_tr), max(a_tr))
    assert agg["metric_mean"] == 14.089084 and agg["metric_std"] == 3.605373
    assert agg["attr_props"] == [0.54386, 0.270175, 0.136842, 0.031579, 0.010526, 0.007018]


def test_gate_actually_runs_on_the_calibrated_substrate():
    # REGRESSION GUARD for the cal= threading on the GATE path: both frozen and calibrated gates PASS (by
    # design, the difficulty holds either way), so gate_pass alone cannot catch a dropped cal=. The candidate
    # count/prevalence DO shift with the calibrated marginals — pin that they differ, so a dropped cal= fails.
    m_all, a_all = _load_real_columns()
    m_tr, a_tr = _split(m_all)[0], _split(a_all)[0]
    cal = calibrated_knobs(fit_aggregates(m_tr, a_tr, KNOBS["n_cats"], min(a_tr), max(a_tr)))
    seeds = [f"xd-{i}" for i in range(20)]
    g_cal, g_frozen = run_gate(seeds, cal=cal), run_gate(seeds)
    assert g_cal["gate_pass"] and g_frozen["gate_pass"]                # both well-posed
    assert g_cal["n_candidates"] != g_frozen["n_candidates"]            # ⇒ the calibrated gate ran on cal


def test_real_calibration_collapses_convergence_but_gate_holds():
    # THE HONEST FINDING: real diagnostic data is ~14× noisier (relative) than the hand-set substrate. At a
    # realistic effect-to-noise the shape channel falls to chance and 3-way convergence no longer clears —
    # but the gate still passes (it is channel POWER that collapses, not the difficulty itself).
    r = run_calibration(gate_seeds=20, conv_seeds=40)
    assert "error" not in r, r
    assert r["is_real_data"] is True

    # (1) calibration is FAITHFUL — held-out real moments match the substrate's observable marginals.
    # The check validates the CLEAN baseline (dips removed); the raw series is wider by the injected signal.
    chk = r["held_out_moment_check"]
    assert chk["held_out_pass"] is True
    assert chk["raw_observable_metric"]["std"] > r["real_test_aggregates"]["metric_std"]  # raw is wider (signal)

    # (2) the real regime is much noisier ⇒ realized SNR far below the frozen design's
    assert r["realized_shape_snr"] < 0.2 * r["frozen_shape_snr"]

    # (3) the substrate is still WELL-POSED under calibration (oracle recovers, naive baselines ~chance)
    assert r["gate_on_calibrated"]["gate_pass"] is True

    # (4) the COLLAPSE: shape channel near chance, 3-way margin CI entirely below the 0.05 bar
    conv = r["convergence_on_calibrated"]
    assert conv["shape_auc"] < 0.65                                  # time-series channel collapsed
    assert conv["relational_auc"] > 0.75                            # categorical/tag channel survives
    assert conv["margin3_bootstrap_ci95"][1] <= 0.05                # upper CI bound below the clean-bar
    assert r["verdict"] == VERDICT_COLLAPSES

    # (5) channels stay independent + rewire still collapses them (structure intact; only power changed)
    assert conv["checks"]["channels_independent"] is True
    assert conv["checks"]["rewire_collapses"] is True


def test_api_calibrate():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    r = client.get("/api/nexus_xdom/calibrate?conv_seeds=40")
    assert r.status_code == 200
    body = r.json()
    assert body["is_real_data"] is True
    assert body["held_out_moment_check"]["held_out_pass"] is True
    assert body["verdict"] == VERDICT_COLLAPSES
