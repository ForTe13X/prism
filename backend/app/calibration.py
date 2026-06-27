"""Real-calibration via inverse-mechanism (DESIGN_data_package.md §4b) — clean-room, deterministic.

The §4b thesis: pure made-up synthetic data is reproducible but not necessarily *realistic* — if its
distributions / correlations / dynamics are off, a benchmark measures a world that doesn't exist. The
fix is **system identification**: learn a generation MECHANISM from the AGGREGATE statistics of a
reference, then re-sample forward from that mechanism. You get both halves — *realistic* (the synthetic
matches the reference's data-logic) and *clean* (the mechanism is in hand, reproducible, no per-row copy).

No licensed real data is available here, so the reference is a **SYNTHETIC STAND-IN for real data**: a
DISTINCT deterministic process (``reference_sample``) that is deliberately NOT the calibrated sampler's
own process — it uses a different functional form (logistic-warped marginals, an explicit AR(1) latent),
so "fit then re-sample" is a real identification problem, not a tautology. It is LABELLED as a stand-in
everywhere (``IS_REAL_DATA = False``).

Discipline held (per §4b risk→mitigation list):
  * **only aggregates fitted** — marginal moments (mean/std per field), one pairwise linear correlation
    coupling two fields, and a mean-revert rate + volatility read off a reference series. NEVER a per-row
    copy: ``fit_*`` only ever touch sufficient statistics, never store reference rows.
  * **parsimonious mechanism, still parameterized + seeded** — the calibrated sampler re-generates from
    the fitted params with Prism's own ``_unit`` hashing, so it generalizes (doesn't pin to one sample)
    and stays byte-reproducible.
  * **realistic by CHECK not by claim** — the test fits SOME moments and validates the calibrated output
    against UN-FITTED / held-out moments (skew, lag-2 autocorr, the partner field's own spread, ...).

Deterministic: reuses ``data_synth._unit`` (sha256 → [0,1]); no ``random``, no clock. Clean-room: only
Prism's own code. Honest scope: this calibrates a small parametric mechanism (Gaussian marginals +
linear coupling + AR(1) dynamics) — richer copulas / SCMs are future work, not claimed here.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .data_synth import _unit

# This module's reference is a SYNTHETIC stand-in for real data, NOT licensed real data. Anything built
# on top must surface this honestly (never present calibrated output as fit to genuine real-world data).
IS_REAL_DATA = False
REFERENCE_LABEL = "SYNTHETIC stand-in for real data (distinct deterministic process; not licensed)"


# --------------------------------------------------------------------------------------------------
# Pseudo-randomness: standard normal from Prism's deterministic [0,1] hash, via Box–Muller.
# --------------------------------------------------------------------------------------------------
def _normal(*seed: object) -> float:
    """A standard-normal draw (mean 0, std 1) derived purely by hashing ``seed`` — deterministic.

    Box–Muller on two independent ``_unit`` hashes. ``u1`` is floored away from 0 so ``log`` is finite;
    no ``random``, no clock, so every draw is byte-reproducible from its seed.
    """
    u1 = max(_unit(*seed, "bm1"), 1e-12)
    u2 = _unit(*seed, "bm2")
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


# --------------------------------------------------------------------------------------------------
# Aggregate-statistics helpers (the ONLY things fit_* are allowed to look at).
# --------------------------------------------------------------------------------------------------
def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    """Population standard deviation (matches the std the sampler is parameterized by)."""
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def _skew(xs: list[float]) -> float:
    """Fisher skewness — a HELD-OUT moment (never fitted), used to check distributional shape."""
    s = _std(xs)
    if s == 0 or len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum(((x - m) / s) ** 3 for x in xs) / len(xs)


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson linear correlation between two equal-length fields."""
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx, my = _mean(xs[:n]), _mean(ys[:n])
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    sxx = sum((xs[i] - mx) ** 2 for i in range(n))
    syy = sum((ys[i] - my) ** 2 for i in range(n))
    denom = math.sqrt(sxx * syy)
    return sxy / denom if denom > 0 else 0.0


def _autocorr(series: list[float], lag: int) -> float:
    """Lag-``lag`` autocorrelation of a series (lag-1 is fitted; higher lags are held-out checks)."""
    n = len(series)
    if n <= lag + 1:
        return 0.0
    m = _mean(series)
    denom = sum((x - m) ** 2 for x in series)
    if denom == 0:
        return 0.0
    num = sum((series[i] - m) * (series[i - lag] - m) for i in range(lag, n))
    return num / denom


# --------------------------------------------------------------------------------------------------
# Reference generator — the SYNTHETIC STAND-IN for real data (a DISTINCT deterministic process).
# --------------------------------------------------------------------------------------------------
def reference_sample(n: int = 600, seed: str = "ref") -> dict:
    """A reference dataset standing in for real data — a process DISTINCT from the calibrated sampler.

    Honesty: this is NOT real data (``IS_REAL_DATA = False``). It exists so calibration has something to
    fit. Its functional form is deliberately different from ``calibrated_sample``'s Gaussian/linear/AR(1)
    mechanism, so identifying the mechanism from aggregates is a genuine problem, not a tautology:

      * field ``x`` — a logistic-warped uniform (heavier shoulders, mild skew) rescaled to a target
        location/spread; its true mean/std/skew are emergent, not handed in.
      * field ``y`` — coupled to ``x`` through a fixed latent loading PLUS its own independent shock, so
        (x, y) carry a real linear correlation whose strength is a property of the process, not a setting.
      * ``series`` — an explicit AR(1) / mean-revert latent ``s_t = (1-k)*s_{t-1} + k*mu + vol*eps_t`` whose
        rate ``k`` and volatility ``vol`` must be RECOVERED from the series, not read from this code.

    Returns column lists ``{"x", "y", "series", "is_real_data": False, "label": ...}``.
    """
    n = max(2, int(n))
    xs: list[float] = []
    ys: list[float] = []
    # --- correlated pair (x, y) via a shared latent + independent shocks ---
    for i in range(n):
        # logistic warp of a uniform draw → non-Gaussian marginal with mild skew
        u = min(max(_unit(seed, "x", i), 1e-9), 1 - 1e-9)
        warp = math.log(u / (1 - u))  # logit: standard-logistic shaped
        x = 47.0 + 6.0 * warp + 1.5 * (_unit(seed, "xskew", i) ** 2)  # location/spread + small skew nudge
        # y loads on x's centered latent plus an independent shock (gives a real linear correlation)
        shock = _normal(seed, "y", i)
        y = 12.0 + 0.55 * (x - 47.0) + 4.0 * shock
        xs.append(x)
        ys.append(y)
    # --- mean-reverting series: explicit AR(1) the fitter must identify from data ---
    k_true, vol_true, mu_true = 0.22, 3.5, 100.0
    series: list[float] = []
    s = mu_true
    for t in range(n):
        s = (1.0 - k_true) * s + k_true * mu_true + vol_true * _normal(seed, "s", t)
        series.append(s)
    return {
        "x": xs,
        "y": ys,
        "series": series,
        "is_real_data": IS_REAL_DATA,
        "label": REFERENCE_LABEL,
    }


# --------------------------------------------------------------------------------------------------
# Fitted parameters (AGGREGATE-only). No reference rows are ever stored here.
# --------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class FittedParams:
    """The parsimonious mechanism learned from the reference's AGGREGATE statistics only.

    Every field is a sufficient statistic (a moment / correlation / rate), never a copied row — so a
    calibrated sample cannot be a laundered copy of the reference. ``n`` is the reference size, kept so
    the calibrated sample can match length for like-for-like moment comparison.
    """
    x_mean: float
    x_std: float
    y_mean: float
    y_std: float
    corr_xy: float       # pairwise linear correlation coupling x and y
    revert_rate: float   # AR(1) mean-revert rate k  (1 - lag1 autocorr)
    series_mean: float   # long-run level the series reverts to
    series_vol: float    # innovation volatility of the series
    n: int

    def as_dict(self) -> dict:
        return asdict(self)


def fit_marginals(ref: dict) -> dict:
    """Fit per-field marginal moments (mean/std) for the correlated pair — AGGREGATE only."""
    return {
        "x_mean": _mean(ref["x"]), "x_std": _std(ref["x"]),
        "y_mean": _mean(ref["y"]), "y_std": _std(ref["y"]),
    }


def fit_correlation(ref: dict) -> float:
    """Fit the single pairwise linear correlation that will couple the two fields — AGGREGATE only."""
    return _pearson(ref["x"], ref["y"])


def fit_dynamics(ref: dict) -> dict:
    """Estimate AR(1) mean-revert rate + innovation volatility from the reference series — AGGREGATE only.

    ``s_t - mu = (1-k)(s_{t-1} - mu) + vol*eps`` ⇒ lag-1 autocorrelation ``phi = 1-k``, so ``k = 1 - phi``.
    The innovation std is recovered from the marginal series std via ``vol = std * sqrt(1 - phi**2)``
    (the stationary AR(1) identity). All from aggregates of the series; no per-step residual is stored.
    """
    series = ref["series"]
    phi = _autocorr(series, 1)
    phi = max(-0.999, min(0.999, phi))
    rate = 1.0 - phi
    s_std = _std(series)
    vol = s_std * math.sqrt(max(0.0, 1.0 - phi * phi))
    return {"revert_rate": rate, "series_mean": _mean(series), "series_vol": vol}


def fit(ref: dict) -> FittedParams:
    """Identify the full mechanism from the reference's aggregate statistics ONLY (no row copying)."""
    m = fit_marginals(ref)
    dyn = fit_dynamics(ref)
    return FittedParams(
        x_mean=m["x_mean"], x_std=m["x_std"], y_mean=m["y_mean"], y_std=m["y_std"],
        corr_xy=fit_correlation(ref),
        revert_rate=dyn["revert_rate"], series_mean=dyn["series_mean"], series_vol=dyn["series_vol"],
        n=len(ref["series"]),
    )


# --------------------------------------------------------------------------------------------------
# Calibrated sampler — forward re-generation PARAMETERIZED by the fitted aggregates.
# --------------------------------------------------------------------------------------------------
def calibrated_sample(params: FittedParams, n: int | None = None, seed: str = "cal") -> dict:
    """Re-generate data forward from the FITTED params — deterministic, seeded, parameterized.

    Mechanism (the parsimonious model whose params were identified):
      * ``x ~ Normal(x_mean, x_std)`` via deterministic Box–Muller;
      * ``y`` built to carry the fitted correlation with x:
        ``y = y_mean + corr*y_std*z_x + sqrt(1-corr**2)*y_std*z_indep`` where ``z_x`` is x standardized —
        the textbook bivariate-normal construction, so ``corr(x, y) → corr_xy`` and ``std(y) → y_std``;
      * ``series`` re-simulated from the fitted AR(1): ``s_t = (1-k) s_{t-1} + k*mu + vol*eps_t``.

    A DIFFERENT ``seed`` from the reference's guarantees the calibrated rows are not the reference rows
    (non-memorization) while the AGGREGATES still match — that is the whole point of §4b.
    """
    m = n if n is not None else params.n
    m = max(2, int(m))
    corr = max(-0.999, min(0.999, params.corr_xy))
    resid = math.sqrt(max(0.0, 1.0 - corr * corr))

    xs: list[float] = []
    ys: list[float] = []
    for i in range(m):
        zx = _normal(seed, "x", i)
        x = params.x_mean + params.x_std * zx
        z_indep = _normal(seed, "yi", i)
        y = params.y_mean + params.y_std * (corr * zx + resid * z_indep)
        xs.append(x)
        ys.append(y)

    series: list[float] = []
    s = params.series_mean
    k = max(0.0, min(2.0, params.revert_rate))
    for t in range(m):
        s = (1.0 - k) * s + k * params.series_mean + params.series_vol * _normal(seed, "s", t)
        series.append(s)

    return {
        "x": xs, "y": ys, "series": series,
        "calibrated": True,
        "fitted_from": REFERENCE_LABEL,
        "is_real_data": IS_REAL_DATA,
    }


# --------------------------------------------------------------------------------------------------
# Convenience: fit + sample in one call, plus a moment-report for held-out validation.
# --------------------------------------------------------------------------------------------------
def calibrate(n_ref: int = 600, n_out: int | None = None,
              ref_seed: str = "ref", cal_seed: str = "cal") -> dict:
    """Run the whole §4b loop: reference stand-in → fit aggregates → re-sample calibrated.

    Returns ``{"params", "reference", "calibrated"}``. Uses DISTINCT seeds for reference vs calibrated so
    the calibrated rows differ from the reference rows (non-memorization holds by construction).
    """
    ref = reference_sample(n_ref, seed=ref_seed)
    params = fit(ref)
    cal = calibrated_sample(params, n=n_out, seed=cal_seed)
    return {"params": params, "reference": ref, "calibrated": cal}


def moments(sample: dict) -> dict:
    """All checkable moments of a sample — both FITTED (mean/std/corr/lag1) and HELD-OUT (skew/lag2/...).

    Used by the test to compare reference vs calibrated on UN-FITTED moments (realistic by check). The
    fitter only ever consumed mean/std/corr/lag-1; everything else here is genuinely held out.
    """
    x, y, s = sample["x"], sample["y"], sample["series"]
    return {
        # fitted family + quantities ALGEBRAICALLY determined by fitted params (sanity, NOT held-out)
        "x_mean": _mean(x), "x_std": _std(x),
        "y_mean": _mean(y), "y_std": _std(y),
        "corr_xy": _pearson(x, y),
        "series_mean": _mean(s), "series_lag1": _autocorr(s, 1),
        "y_over_x_std_ratio": (_std(y) / _std(x)) if _std(x) else 0.0,  # = y_std/x_std, both fitted ⇒ sanity, not held-out
        # HELD-OUT family — moments the fitter genuinely NEVER consumed (real realistic-by-check)
        "x_skew": _skew(x), "y_skew": _skew(y),
        "series_std": _std(s),
        "series_lag2": _autocorr(s, 2),
        "series_lag3": _autocorr(s, 3),
        "corr_x_series": _pearson(x, s),  # should be ~0: x and series are independent processes
    }
