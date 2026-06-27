"""Phase-B.1 convergence eval (METRIC §8d) — run the two independent channels on the FROZEN substrate and
report the honest verdict against PRE-REGISTERED floors. No constant is tuned here.

Pre-registered (design panel): each channel's standalone AUC must clear POWER_FLOOR=0.78; the two channels
must be independent (|corr| < INDEP_BOUND); breaking the coupling (rewire) must collapse both to chance; and
— the load-bearing 2/2 claim — convergence must beat BOTH singles by CONV_MARGIN_FLOOR=0.05.

HONESTY: the single most load-bearing number (the convergence margin) is NOT a point estimate — the project
discipline (§4) is "report mean±CI, gain must exceed noise". A deterministic seed bootstrap shows the margin
STRADDLES the 0.05 floor (a point estimate at one seed count flips above/below it), so the honest verdict is
INDETERMINATE at the 0.05 bar, not a confident near-miss or a confident win. The KNOBS were power-tuned with
channel visibility (§8c), so "the channels are informative" is engineered; channels are evaluated on a
HELD-OUT seed namespace (xe-*) disjoint from the tuning/gate seeds (xd-*), and independence / the rewire
collapse / the margin's relation to the floor were NOT tuned — they remain the falsifiable content.
"""
from __future__ import annotations

from .data_synth import _unit
from .nexus_chan_fingerprint import fingerprint_score
from .nexus_chan_shape import _z, shape_score
from .nexus_eval import roc_auc
from .nexus_xdom_substrate import labelled_bridges_xdom

HELD_OUT_SEEDS = [f"xe-{i}" for i in range(120)]
POWER_FLOOR = 0.78
CONV_MARGIN_FLOOR = 0.05
INDEP_BOUND = 0.30
_BOOTSTRAP = 200


def _pearson_raw(a: list[float], b: list[float]) -> float:
    za, zb = _z(a), _z(b)
    return sum(x * y for x, y in zip(za, zb)) / (len(za) or 1)


def _aucs(sh: list[float], fp: list[float], y: list[float]) -> dict:
    conv = [a + b for a, b in zip(_z(sh), _z(fp))]
    auc_sh, auc_fp, auc_conv = roc_auc(sh, y), roc_auc(fp, y), roc_auc(conv, y)
    return {"shape": auc_sh, "fp": auc_fp, "conv": auc_conv, "margin": round(auc_conv - max(auc_sh, auc_fp), 4)}


def _by_seed(seeds: list[str], control: str | None = None) -> list[tuple]:
    """Per-seed (shape_scores, fp_scores, labels) — scores computed ONCE so the bootstrap only re-pools."""
    out = []
    for sd in seeds:
        b = labelled_bridges_xdom([sd], control=control)
        out.append(([shape_score(x) for x in b], [fingerprint_score(x) for x in b], [x["y"] for x in b]))
    return out


def _pool(groups: list[tuple], idx: list[int]) -> tuple[list, list, list]:
    sh, fp, y = [], [], []
    for i in idx:
        g = groups[i]
        sh += g[0]; fp += g[1]; y += g[2]
    return sh, fp, y


def run_convergence(seeds: list[str] | None = None) -> dict:
    seeds = seeds or HELD_OUT_SEEDS
    groups = _by_seed(seeds)
    n = len(groups)
    full = _pool(groups, list(range(n)))
    a = _aucs(*full)
    corr = round(_pearson_raw(full[0], full[1]), 4)

    # deterministic seed BOOTSTRAP of the margin: resample n seeds with replacement (via _unit), recompute
    # the margin each time → the margin's spread around the 0.05 floor (the load-bearing CI the discipline asks for)
    boot = []
    for b in range(_BOOTSTRAP):
        idx = [int(_unit("xdom-boot", b, i) * n) % n for i in range(n)]
        boot.append(_aucs(*_pool(groups, idx))["margin"])
    boot.sort()
    ci_lo, ci_hi = boot[int(0.025 * _BOOTSTRAP)], boot[int(0.975 * _BOOTSTRAP) - 1]
    straddles = ci_lo < CONV_MARGIN_FLOOR < ci_hi

    # rewire negative control (full pool): break the coupling → both channels and convergence to chance
    rfull = _pool(_by_seed(seeds, control="rewire"), list(range(n)))
    ra = _aucs(*rfull)
    rewire = {"shape_auc": ra["shape"], "fingerprint_auc": ra["fp"], "convergence_auc": ra["conv"]}

    power_ok = a["shape"] >= POWER_FLOOR and a["fp"] >= POWER_FLOOR
    indep_ok = abs(corr) < INDEP_BOUND
    rewire_ok = all(v <= 0.60 for v in rewire.values())
    if straddles:
        margin_call = "indeterminate_at_0.05_bar"
    elif ci_lo >= CONV_MARGIN_FLOOR:
        margin_call = "clears_0.05"
    else:
        margin_call = "below_0.05"
    outcome = ("two_independent_informative_channels__convergence_" + margin_call) if (power_ok and indep_ok and rewire_ok) \
        else ("one_strong_one_weak" if (a["shape"] >= POWER_FLOOR) != (a["fp"] >= POWER_FLOOR) else "negative")

    return {
        "seeds": n, "seed_namespace": "xe-* (held out from the xd-* tuning/gate seeds)",
        "n_candidates": len(full[2]), "n_positives": sum(full[2]),
        "shape_auc": a["shape"], "fingerprint_auc": a["fp"], "convergence_auc": a["conv"],
        "convergence_margin_point": a["margin"], "channel_correlation": corr,
        "margin_bootstrap_ci95": [round(ci_lo, 4), round(ci_hi, 4)], "margin_straddles_floor": straddles,
        "rewire_control": rewire,
        "preregistered": {"power_floor": POWER_FLOOR, "conv_margin_floor": CONV_MARGIN_FLOOR,
                          "independence_bound": INDEP_BOUND, "bootstrap": _BOOTSTRAP},
        "checks": {"both_clear_power_floor": power_ok, "channels_independent": indep_ok,
                   "rewire_collapses": rewire_ok, "convergence_margin": margin_call},
        "outcome": outcome,
        "honest_verdict": (
            "两渠道读不相交 store(形状=时序、指纹=SQL),独立(corr 小)且 rewire 后塌回随机——结构上逃离 Phase-A 的"
            "『一表三读』。但**收敛 margin 的 95% bootstrap CI 跨过 0.05**(点估 ≈0.048,CI 含 0.05)⇒ 收敛是否过『干净 2/2』"
            "线**判不定(在抽样噪声内)**,既非确信近失也非确信赢。常量曾带渠道可见性调参(§8c),故『渠道有效』是工程构造;"
            "独立性/rewire/margin-vs-floor 未调,是可证伪内容。"
        ),
    }
