"""Track 1 — calibrate the cross-domain nexus substrate to REAL data (DESIGN_data_package §4b), then
re-run the §6c gate + the 3-way convergence on the calibrated substrate. Clean-room, deterministic.

WHY (OBSERVER_NOTES §11): the metric is now rigorous, but the substrate's realism is *claimed, not
verified* — its marginals were hand-set (base=250, wiggle=8 ⇒ coefficient-of-variation 0.03, far cleaner
than any real measurement). The external-validity question: do the honest nexus results SURVIVE when the
substrate's OBSERVABLE marginals are calibrated to a real dataset, or COLLAPSE? Either answer is valuable —
survival means the result isn't an artifact of an unrealistically clean substrate; collapse is an even more
useful honest finding (the frozen win lived on hand-set low noise).

WHAT IS CALIBRATED (the OBSERVABLE marginals only — §4b "只取聚合量"):
  * metric baseline level + spread   → real feature mean μ, std σ   ⇒  base=μ, wiggle=σ·√3
    (the baseline series is uniform on [base±wiggle], whose std is wiggle/√3, so wiggle=σ·√3 ⇒ observable
     std = σ; observable mean = base = μ).
  * attribute category proportions    → a real feature binned into n_cats equal-width bins ⇒ attr base logits
    = log(real proportions)  (replaces the frozen ~uniform base with a realistic, skewed one).

WHAT IS *NOT* CALIBRATED (the deeper external-validity gap stays — honest, not closed here):
  * the COUPLING itself — the dip/profile, the theta shift, the psi/tag shift — is the DESIGNED latent
    signal. We preserve its DESIGNED RELATIVE EFFECT SIZE (the dip is the frozen fraction of the baseline,
    depth = (frozen_depth/frozen_base)·μ ≈ 0.72·μ), so the *signal* scales with the real mean while the
    *noise* scales with the real spread. The consequence is the honest stress: real data's high CV pushes
    the metric channel's SNR — dip depth ÷ baseline-noise std, i.e. depth/(wiggle/√3) — from the frozen
    ≈39 down to ≈ 0.72·(μ/σ) ≈ 2.8 (one convention throughout: the returned ``*_shape_snr`` fields and §8g
    use this same depth/(wiggle/√3) form). The coupling's realism (is a 0.72 dip a realistic effect? is the
    latent structure real?) is NOT addressed — that needs a real *paired* cross-domain source, we have none.

VERIFIED, NOT CLAIMED (§4b "真实要验证非声称"): we fit aggregates on a TRAIN split of the real data and check
the calibrated substrate's OBSERVABLE marginals against the HELD-OUT TEST split's aggregates. The substrate
never sees test aggregates; agreement is a genuine generalization check, not a tautology.

REAL DATA: scikit-learn's bundled ``load_breast_cancer`` — 569 real diagnostic measurements, BSD-licensed,
ships inside the package (no network, version-stable). Only AGGREGATE moments / proportions are read; no
per-row real value is stored in or returned by this module (no laundering of real rows).

Deterministic: the calibrated KNOBS are fixed functions of the (static, bundled) real dataset's aggregates,
rounded to 6 dp; the substrate generation stays Prism's own ``_u`` hashing. No ``random``, no clock.
"""
from __future__ import annotations

import math

from .data_package_xdom import KNOBS, generate_xdom
from .nexus_xdom_eval import run_convergence
from .nexus_xdom_gate import run_gate

# --- pre-registered (lens-independent, set before seeing any convergence number) --------------------
METRIC_FEATURE = 0        # breast_cancer feature index for the metric marginal ("mean radius")
ATTR_FEATURE = 3          # feature index binned into n_cats for the attribute proportions ("mean area")
FROZEN_DROP_FRAC = round(KNOBS["depth"] / KNOBS["base"], 6)   # the designed relative dip (≈0.72), preserved
MOMENT_TOL = 0.12         # held-out agreement tolerance (relative for moments, L1 for proportions)
CHECK_SEEDS = [f"xc-{i}" for i in range(40)]                  # observable-marginal measurement namespace
_EPS = 1e-6
EXPECTED_SHAPE = (569, 30)                                    # breast_cancer dims — guard against upstream drift

# verdict labels (single source of truth; tests import these instead of duplicating the literal)
VERDICT_SURVIVES = "survives_real_calibration"
VERDICT_COLLAPSES = "collapses_under_real_calibration"
VERDICT_INDETERMINATE = "indeterminate_under_real_calibration"

REAL_SOURCE = "scikit-learn load_breast_cancer (569 real samples, BSD-licensed, bundled; aggregates only)"


# --------------------------------------------------------------------------------------------------
# Real reference — AGGREGATES ONLY. Rows are read to compute moments and then discarded.
# --------------------------------------------------------------------------------------------------
def _load_real_columns() -> tuple[list[float], list[float]]:
    """Return the two real feature columns used as references. Raises if scikit-learn is unavailable —
    we NEVER fabricate 'real' data (that would break the honesty bar Track 1 exists to defend)."""
    from sklearn.datasets import load_breast_cancer  # local import: optional dependency, fail loud if absent

    d = load_breast_cancer()
    # guard against silent upstream data drift — the calibrated KNOBS are a deterministic function of these
    # exact bundled float64 values, so a changed shape must fail loudly rather than re-calibrate unnoticed.
    if d.data.shape != EXPECTED_SHAPE:
        raise ValueError(f"breast_cancer shape {d.data.shape} != expected {EXPECTED_SHAPE} "
                         "(bundled dataset changed; re-pin the frozen aggregates before trusting calibration)")
    metric = [float(r[METRIC_FEATURE]) for r in d.data]
    attr = [float(r[ATTR_FEATURE]) for r in d.data]
    return metric, attr


def _split(vals: list[float]) -> tuple[list[float], list[float]]:
    """Deterministic 50/50 split by index parity (no RNG): even → train (fit), odd → test (held-out)."""
    train = [v for i, v in enumerate(vals) if i % 2 == 0]
    test = [v for i, v in enumerate(vals) if i % 2 == 1]
    return train, test


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def _bin_proportions(vals: list[float], nc: int, lo: float, hi: float) -> list[float]:
    """Proportion of ``vals`` falling in each of ``nc`` equal-width bins over [lo, hi] (a real categorical
    distribution; naturally non-uniform / skewed). Floored at _EPS so log() is finite."""
    if hi <= lo:
        return [1.0 / nc] * nc
    width = (hi - lo) / nc
    counts = [0] * nc
    for v in vals:
        k = int((v - lo) / width)
        k = max(0, min(nc - 1, k))
        counts[k] += 1
    tot = sum(counts) or 1
    raw = [max(c / tot, _EPS) for c in counts]
    s = sum(raw)
    return [r / s for r in raw]


def fit_aggregates(metric_train: list[float], attr_train: list[float], nc: int,
                   attr_lo: float, attr_hi: float) -> dict:
    """Fit the OBSERVABLE-marginal aggregates from the TRAIN split only (moments + proportions)."""
    return {
        "metric_mean": round(_mean(metric_train), 6),
        "metric_std": round(_std(metric_train), 6),
        "attr_props": [round(p, 6) for p in _bin_proportions(attr_train, nc, attr_lo, attr_hi)],
    }


def calibrated_knobs(agg: dict, effect_scale: float = 1.0) -> dict:
    """Map fitted real aggregates → a ``cal`` override for ``generate_xdom``.

    base = μ; wiggle = σ·√3 (⇒ observable baseline std = σ); depth = effect_scale·(frozen_drop)·μ (preserve
    the designed RELATIVE dip, scaled by the real mean — ``effect_scale`` sweeps it); attr_logits = log(real
    proportions). attr_shift / tag_shift are NOT here ⇒ the substrate keeps its designed logit-space signal
    shifts (the fingerprint/relational coupling), so only the MARGINALS are calibrated."""
    mu, sigma = agg["metric_mean"], agg["metric_std"]
    return {
        "base": round(mu, 6),
        "wiggle": round(sigma * math.sqrt(3.0), 6),
        "depth": round(effect_scale * FROZEN_DROP_FRAC * mu, 6),
        "attr_logits": [round(math.log(max(p, _EPS)), 6) for p in agg["attr_props"]],
    }


# --------------------------------------------------------------------------------------------------
# Held-out verification — measure the calibrated substrate's OBSERVABLE marginals (latent-aware, eval-side)
# and compare to the real TEST aggregates the substrate never saw.
# --------------------------------------------------------------------------------------------------
def _dipped_frames(g: dict) -> dict:
    """(dk → {(unit, frame)}) covered by ANY dip (coupled or distractor) — excluded when measuring the
    clean baseline marginal. Uses the eval-only latents (legitimate at verification time, like the gate
    oracle); a SOLVER never gets this."""
    hw = KNOBS["half_width"]
    nf = KNOBS["frames"]
    out = {"A": set(), "B": set()}
    for inc in g["_latents"]["coupled"]:
        for side, unit, f in (("A", inc["i"], inc["fa"]), ("B", inc["j"], inc["fb"])):
            for τ in range(2 * hw + 1):
                fr = f - hw + τ
                if 0 <= fr < nf:
                    out[side].add((unit, fr))
    for dd in g["_latents"]["distractor"]:
        for τ in range(2 * hw + 1):
            fr = dd["f"] - hw + τ
            if 0 <= fr < nf:
                out[dd["side"]].add((dd["unit"], fr))
    return out


def _incident_units(g: dict) -> dict:
    """(dk → {unit}) carrying ANY incident — excluded when measuring the clean baseline attribute mix."""
    out = {"A": set(), "B": set()}
    for inc in g["_latents"]["coupled"]:
        out["A"].add(inc["i"]); out["B"].add(inc["j"])
    for dd in g["_latents"]["distractor"]:
        out[dd["side"]].add(dd["unit"])
    return out


def observable_marginals(cal: dict, seeds: list[str], nc: int, attr_lo: float, attr_hi: float) -> dict:
    """Measure what the calibrated substrate actually EXPOSES: baseline metric mean/std over non-dip frames,
    and the attribute category proportions over non-incident units. These are exactly what a downstream
    analyst would observe (minus the embedded coupling), so matching them to real = realism-by-check."""
    metric_vals: list[float] = []       # clean baseline (dip frames removed) — what the calibration targets
    raw_vals: list[float] = []          # the RAW series an analyst actually sees (signal/dips INCLUDED)
    cat_counts = [0] * nc
    for sd in seeds:
        g = generate_xdom(sd, cal)
        dipped = _dipped_frames(g)
        incid = _incident_units(g)
        for dk in ("A", "B"):
            dom = g[dk]
            for u_i, u in enumerate(dom["units"]):
                s = dom["series"][u["id"]]
                for fr, val in enumerate(s):
                    raw_vals.append(val)
                    if (u_i, fr) not in dipped[dk]:
                        metric_vals.append(val)
                if u_i not in incid[dk]:
                    for r in u["records"]:
                        cat_counts[r["cat_index"]] += 1
    tot = sum(cat_counts) or 1
    return {
        "metric_mean": _mean(metric_vals),
        "metric_std": _std(metric_vals),
        "raw_metric_mean": _mean(raw_vals),    # dips included ⇒ lower mean + inflated variance (disclosed)
        "raw_metric_std": _std(raw_vals),
        "attr_props": [c / tot for c in cat_counts],
        "n_metric": len(metric_vals),
    }


def held_out_check(agg_train: dict, agg_test: dict, observed: dict) -> dict:
    """Compare the calibrated substrate's OBSERVED marginals to the real TEST aggregates (held out from the
    fit). Reports relative moment errors + an L1 proportion distance, and a pass flag at MOMENT_TOL."""
    mu_t, sd_t = agg_test["metric_mean"], agg_test["metric_std"]
    mean_relerr = abs(observed["metric_mean"] - mu_t) / (abs(mu_t) or 1.0)
    std_relerr = abs(observed["metric_std"] - sd_t) / (sd_t or 1.0)
    props_l1 = sum(abs(o - t) for o, t in zip(observed["attr_props"], agg_test["attr_props"]))
    # also report train↔test stability of the real aggregates themselves (is the fit target even stable?)
    real_mean_drift = abs(agg_train["metric_mean"] - mu_t) / (abs(mu_t) or 1.0)
    real_props_l1 = sum(abs(a - b) for a, b in zip(agg_train["attr_props"], agg_test["attr_props"]))
    passed = mean_relerr <= MOMENT_TOL and std_relerr <= MOMENT_TOL and props_l1 <= MOMENT_TOL
    return {
        "checks_the_clean_baseline_marginal": True,  # signal (dips) removed; the RAW series is wider — see below
        "observed_vs_real_test": {
            "metric_mean": [round(observed["metric_mean"], 4), round(mu_t, 4), round(mean_relerr, 4)],
            "metric_std": [round(observed["metric_std"], 4), round(sd_t, 4), round(std_relerr, 4)],
            "attr_props_l1": round(props_l1, 4),
        },
        # for honesty: the RAW (dip-included) observable spread an analyst sees — inflated by the injected
        # signal, so it does NOT match real σ; only the signal-removed baseline does (that is what we calibrate).
        "raw_observable_metric": {"mean": round(observed.get("raw_metric_mean", 0.0), 4),
                                  "std": round(observed.get("raw_metric_std", 0.0), 4),
                                  "note": "signal/dips included ⇒ wider than real σ by design"},
        "real_train_vs_test_stability": {"metric_mean_drift": round(real_mean_drift, 4),
                                          "attr_props_l1": round(real_props_l1, 4)},
        "tolerance": MOMENT_TOL,
        "held_out_pass": bool(passed),
        "n_observed_metric": observed["n_metric"],
    }


# --------------------------------------------------------------------------------------------------
# Orchestration.
# --------------------------------------------------------------------------------------------------
def _snr(cal: dict) -> float:
    """Realized shape-channel SNR = dip depth / baseline noise std (= depth / (wiggle/√3))."""
    noise_std = cal["wiggle"] / math.sqrt(3.0)
    return round(cal["depth"] / (noise_std or 1.0), 4)


def run_calibration(gate_seeds: int = 60, conv_seeds: int | None = None,
                    effect_scale: float = 1.0) -> dict:
    """Full Track-1 loop: real reference → fit (train) → calibrated knobs → held-out check (test) →
    re-run §6c gate + 3-way convergence on the calibrated substrate → honest survive/collapse verdict.

    ``conv_seeds`` limits the held-out convergence seed count (None = the eval's full default). The API
    passes a smaller count for latency; the offline/CLI run uses the full set for the headline numbers.
    """
    nc = KNOBS["n_cats"]
    try:
        metric_all, attr_all = _load_real_columns()
    except Exception as exc:  # scikit-learn missing / load failure — be loud, never fabricate
        return {"error": f"real reference unavailable: {exc}",
                "honest_note": "Track 1 requires genuine real data; fabricating it is forbidden by the "
                               "honesty bar. Install scikit-learn (bundled, BSD) to run.",
                "real_source": REAL_SOURCE}

    metric_tr, metric_te = _split(metric_all)
    attr_tr, attr_te = _split(attr_all)
    # equal-width attribute bins are fixed over the TRAIN split ONLY — so the held-out attribute check never
    # sees the test extremes (the test half holds the global min/max). Test rows binned into train-defined
    # edges = a genuinely held-out comparison (out-of-range test values clamp to the edge bins).
    attr_lo, attr_hi = min(attr_tr), max(attr_tr)
    agg_train = fit_aggregates(metric_tr, attr_tr, nc, attr_lo, attr_hi)
    agg_test = fit_aggregates(metric_te, attr_te, nc, attr_lo, attr_hi)

    cal = calibrated_knobs(agg_train, effect_scale=effect_scale)
    observed = observable_marginals(cal, CHECK_SEEDS, nc, attr_lo, attr_hi)
    check = held_out_check(agg_train, agg_test, observed)

    gate = run_gate([f"xd-{i}" for i in range(gate_seeds)], cal=cal)
    conv_kwargs = {} if conv_seeds is None else {"seeds": [f"xe-{i}" for i in range(conv_seeds)]}
    conv = run_convergence(cal=cal, **conv_kwargs)

    floor = conv["preregistered"]["conv_margin_floor"]
    margin3_ci = conv["margin3_bootstrap_ci95"]
    # SURVIVES requires the SAME bar the eval's own positive outcome uses (incl. the power floor), plus the
    # held-out check — so a margin that clears while a channel sits below the power floor is NOT called a win.
    survives = (gate["gate_pass"] and check["held_out_pass"]
                and conv["checks"]["all_three_clear_power_floor"]
                and conv["checks"]["channels_independent"] and conv["checks"]["rewire_collapses"]
                and margin3_ci[0] >= floor)
    verdict = VERDICT_SURVIVES if survives else (
        VERDICT_COLLAPSES if margin3_ci[1] <= floor   # ≤ matches the eval's _call() hi-side convention
        else VERDICT_INDETERMINATE)
    frozen_snr = round(KNOBS["depth"] / (KNOBS["wiggle"] / math.sqrt(3.0)), 4)

    return {
        "real_source": REAL_SOURCE, "is_real_data": True,
        "pre_registered": {"metric_feature": METRIC_FEATURE, "attr_feature": ATTR_FEATURE,
                           "frozen_drop_frac": FROZEN_DROP_FRAC, "effect_scale": effect_scale,
                           "moment_tol": MOMENT_TOL},
        "fitted_aggregates_train": agg_train,
        "real_test_aggregates": agg_test,
        "calibrated_knobs": cal,
        "realized_shape_snr": _snr(cal),
        "frozen_shape_snr": frozen_snr,
        "held_out_moment_check": check,
        "gate_on_calibrated": {"gate_pass": gate["gate_pass"], "oracle_auc": gate["oracle_auc"],
                               "time_auc": gate["time_auc"], "depth_auc": gate["depth_auc"],
                               "string_auc": gate["string_auc"],
                               # candidate count/prevalence shift with the calibrated marginals — proof the
                               # gate ran on the CALIBRATED substrate (a dropped cal= would show frozen values)
                               "n_candidates": gate["n_candidates"], "prevalence": gate["prevalence"]},
        "convergence_on_calibrated": {
            "shape_auc": conv["shape_auc"], "fingerprint_auc": conv["fingerprint_auc"],
            "relational_auc": conv["relational_auc"], "convergence3_auc": conv["convergence3_auc"],
            "convergence3_margin_point": conv["convergence3_margin_point"],
            "margin3_bootstrap_ci95": margin3_ci, "channel_correlations": conv["channel_correlations"],
            "rewire_control": conv["rewire_control"], "checks": conv["checks"]},
        "verdict": verdict,
        "honest_verdict": (
            "把 substrate 的**可观测边缘**(基线均值/方差、类目占比)校准到真实数据(breast_cancer,只取聚合量),"
            "并用 held-out 测试集的矩**验证非声称**(矩拟合于 train,属性分箱也只用 train 端点,test 真未泄);耦合(信号)"
            "保持设计的相对效应量(≈0.72 相对 dip),于是真实数据的高变异(CV≈0.25)把形状渠道 SNR(=depth/(wiggle/√3))"
            "从冻结的≈%s 压到≈%s。再在校准 substrate 上重跑 §6c gate + 三渠道收敛:`verdict` = 结果是否**存活**。"
            "存活⇒冻结结论不是『手设低噪声』的产物;塌缩⇒一个更有价值的诚实发现。注:held-out 检验对的是**去信号的干净基线**"
            "marginal(raw 含 dip 的方差更宽,见 `raw_observable_metric`)。未校准:耦合本身的真实性(0.72 效应量真不真、"
            "latent 结构真不真)——需要真实**配对**跨域源,此处不声称。"
            % (frozen_snr, _snr(cal))),
    }


def run_effect_sweep(scales: list[float] | None = None, conv_seeds: int = 60) -> dict:
    """Honest robustness curve: vary the coupling's relative effect size (``effect_scale``) and report the
    3-way convergence margin CI at each — locating the survive↔collapse boundary under real-calibrated
    noise. No cherry-picking: the metric channel's SNR at each scale is reported alongside."""
    scales = scales or [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
    nc = KNOBS["n_cats"]
    try:
        metric_all, attr_all = _load_real_columns()
    except Exception as exc:
        return {"error": f"real reference unavailable: {exc}", "real_source": REAL_SOURCE}
    metric_tr, attr_tr = _split(metric_all)[0], _split(attr_all)[0]
    attr_lo, attr_hi = min(attr_tr), max(attr_tr)   # TRAIN-only bin edges (no test leak), same as run_calibration
    agg_train = fit_aggregates(metric_tr, attr_tr, nc, attr_lo, attr_hi)
    seeds = [f"xe-{i}" for i in range(conv_seeds)]
    rows = []
    for sc in scales:
        cal = calibrated_knobs(agg_train, effect_scale=sc)
        conv = run_convergence(seeds=seeds, cal=cal)
        rows.append({"effect_scale": sc, "shape_snr": _snr(cal),
                     "shape_auc": conv["shape_auc"], "convergence3_auc": conv["convergence3_auc"],
                     "margin3_ci95": conv["margin3_bootstrap_ci95"],
                     "call": conv["checks"]["convergence3_margin"]})
    return {"real_source": REAL_SOURCE, "conv_seeds": conv_seeds, "sweep": rows,
            "note": "effect_scale multiplies the designed relative dip; shape_snr = depth/(wiggle/√3). "
                    "Locates where 3-way convergence clears 0.05 under real-calibrated marginal noise."}
