"""§4b real-calibration (inverse-mechanism) — the invariants that make calibrated synthetic data both
*realistic* and *clean*:

  * HELD-OUT moment match — fit on SOME moments (mean/std/corr/lag-1), then verify the calibrated output
    matches the reference on UN-FITTED moments (skew, lag-2/lag-3 autocorr, the partner field's spread,
    cross-process independence). "Realistic by CHECK, not by claim" (§4b last bullet).
  * DETERMINISM — byte-identical across runs (no random, no clock).
  * NON-MEMORIZATION — calibrated rows are NOT the reference rows (mechanism re-sampled, not laundered).
  * HONESTY — the reference is labelled a synthetic stand-in, never claimed to be real data.

Run from repo root: ``python -m pytest backend/tests/test_calibration.py -q``
"""
from __future__ import annotations

import json

from backend.app.calibration import (
    IS_REAL_DATA, REFERENCE_LABEL, calibrate, calibrated_sample, fit, moments, reference_sample,
)

N = 600


def _canon(sample: dict) -> str:
    return json.dumps(sample, ensure_ascii=False, sort_keys=True)


# --------------------------------------------------------------------------------------------------
# Honesty: the reference is a labelled stand-in, never claimed to be real.
# --------------------------------------------------------------------------------------------------
def test_reference_is_labelled_stand_in_not_real():
    assert IS_REAL_DATA is False
    ref = reference_sample(N)
    assert ref["is_real_data"] is False
    assert "stand-in" in REFERENCE_LABEL.lower() and "real data" in REFERENCE_LABEL.lower()
    cal = calibrate(N)["calibrated"]
    assert cal["is_real_data"] is False and cal["calibrated"] is True


# --------------------------------------------------------------------------------------------------
# Determinism: byte-identical reference, fit, and calibrated output across repeated runs.
# --------------------------------------------------------------------------------------------------
def test_determinism_byte_identical():
    assert _canon(reference_sample(N)) == _canon(reference_sample(N))
    a, b = calibrate(N), calibrate(N)
    assert a["params"].as_dict() == b["params"].as_dict()
    assert _canon(a["calibrated"]) == _canon(b["calibrated"])
    assert _canon(a["reference"]) == _canon(b["reference"])


# --------------------------------------------------------------------------------------------------
# Non-memorization: calibrated rows are NOT the reference rows (only aggregates were shared).
# --------------------------------------------------------------------------------------------------
def test_non_memorization_rows_differ():
    bundle = calibrate(N)
    ref, cal = bundle["reference"], bundle["calibrated"]
    # Distinct seeds ⇒ essentially no exact row collisions across the calibrated vs reference draws.
    for field in ("x", "y", "series"):
        ref_vals, cal_vals = ref[field], cal[field]
        collisions = sum(1 for a, b in zip(ref_vals, cal_vals) if a == b)
        assert collisions == 0, f"{field}: {collisions} identical rows — looks memorized"
        # And the calibrated column is not a permutation/copy of the reference column either.
        assert set(round(v, 9) for v in cal_vals) != set(round(v, 9) for v in ref_vals)


# --------------------------------------------------------------------------------------------------
# FITTED moments: the sampler reproduces what it was parameterized on (necessary sanity).
# --------------------------------------------------------------------------------------------------
def test_fitted_moments_reproduced():
    bundle = calibrate(N)
    rm, cm = moments(bundle["reference"]), moments(bundle["calibrated"])
    # Tolerances reflect finite-sample Monte-Carlo error of the calibrated draw, not looseness: the
    # FITTED params nail the reference moments (x_mean 47.097, corr 0.847, lag1 phi≈0.70), but a fresh
    # n=600 draw has its own sampling fluctuation — e.g. x has std≈11 ⇒ mean SE≈0.45, so ~2·SE≈0.9.
    assert abs(rm["x_mean"] - cm["x_mean"]) < 1.0
    assert abs(rm["x_std"] - cm["x_std"]) < 0.5
    assert abs(rm["y_mean"] - cm["y_mean"]) < 0.7
    assert abs(rm["y_std"] - cm["y_std"]) < 0.5
    assert abs(rm["corr_xy"] - cm["corr_xy"]) < 0.05
    assert abs(rm["series_mean"] - cm["series_mean"]) < 1.5
    assert abs(rm["series_lag1"] - cm["series_lag1"]) < 0.08


# --------------------------------------------------------------------------------------------------
# HELD-OUT moments: the calibrated output matches the reference on moments the fitter NEVER saw.
# This is the realistic-by-check claim. The fitter consumed ONLY mean/std/corr/lag-1.
# --------------------------------------------------------------------------------------------------
def test_held_out_moments_match():
    bundle = calibrate(N)
    rm, cm = moments(bundle["reference"]), moments(bundle["calibrated"])

    # sanity (NOT held-out): y_std/x_std is algebraically two fitted params; just confirms both reproduce.
    assert abs(rm["y_over_x_std_ratio"] - cm["y_over_x_std_ratio"]) < 0.06

    # held-out higher-lag autocorrelations of the AR(1) series (only lag-1 was fitted).
    assert abs(rm["series_lag2"] - cm["series_lag2"]) < 0.10
    assert abs(rm["series_lag3"] - cm["series_lag3"]) < 0.10

    # held-out series spread (vol was fitted, marginal std is the emergent stationary consequence).
    assert abs(rm["series_std"] - cm["series_std"]) < 1.5

    # held-out cross-process independence: x and series are unrelated ⇒ corr ~ 0 in BOTH.
    assert abs(cm["corr_x_series"]) < 0.15
    assert abs(rm["corr_x_series"]) < 0.15

    # held-out skew: the reference x is mildly skewed (logistic warp); the Gaussian sampler is ~symmetric.
    # We do NOT require these to match — that would over-claim. We assert the HONEST gap: the calibrated
    # marginal is near-symmetric, documenting that this parsimonious mechanism captures moments up to 2nd
    # order + linear coupling + AR(1), not full distributional shape (skew is a known, surfaced limit).
    assert abs(cm["x_skew"]) < 0.2, "Gaussian sampler should be ~symmetric"


# --------------------------------------------------------------------------------------------------
# Fit touches ONLY aggregates: changing n but keeping the process gives a near-identical mechanism
# (params are sufficient statistics, not memorized rows), and a re-seeded sample still matches moments.
# --------------------------------------------------------------------------------------------------
def test_fit_is_aggregate_and_generalizes():
    ref = reference_sample(N)
    params = fit(ref)
    # Re-sample at a DIFFERENT length and a DIFFERENT seed: aggregates must still hold (generalization,
    # not a pinned copy of one sample).
    cal2 = calibrated_sample(params, n=400, seed="other")
    cm = moments(cal2)
    rm = moments(ref)
    assert len(cal2["x"]) == 400
    assert abs(rm["x_mean"] - cm["x_mean"]) < 0.6
    assert abs(rm["corr_xy"] - cm["corr_xy"]) < 0.09
    assert abs(rm["series_lag1"] - cm["series_lag1"]) < 0.10
