"""Phase-B.1/B.2 convergence eval (METRIC §8d/§8e) — run the independent channels on the FROZEN substrate
and report the honest verdict against PRE-REGISTERED floors. No constant is tuned here.

Pre-registered (design panel): each channel's standalone AUC must clear POWER_FLOOR=0.78; the channels must
be independent; breaking the coupling (rewire) must collapse them to chance; and — the load-bearing claim —
convergence must beat the best single by CONV_MARGIN_FLOOR=0.05. Phase-B.1 had TWO channels (shape⊥
fingerprint) and the 2-way margin's bootstrap CI STRADDLED 0.05 (indeterminate). Phase-B.2 adds a THIRD
independent channel (relational/tags, from a disjoint latent) — the question it answers: does 3-way
convergence clear 0.05 STABLY (CI entirely above) where 2-way could not?

HONESTY: the margin is reported as a 200× deterministic-bootstrap 95% CI (the project's "report mean±CI,
gain must exceed noise" discipline), for BOTH the 2-way and 3-way convergence. Channels are evaluated on a
HELD-OUT seed namespace (xe-*) disjoint from the tuning/gate seeds (xd-*). Each channel's POWER is
engineered (its constant was tuned with channel visibility); INDEPENDENCE and the margin-vs-floor are not.
"""
from __future__ import annotations

from .data_synth import _unit
from .nexus_chan_fingerprint import fingerprint_score
from .nexus_chan_relational import relational_score
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


def _z_sum(score_lists: list[list[float]]) -> list[float]:
    zs = [_z(s) for s in score_lists]
    return [sum(vals) for vals in zip(*zs)]


def _margins(sh: list, fp: list, rel: list, y: list) -> dict:
    a_sh, a_fp, a_rel = roc_auc(sh, y), roc_auc(fp, y), roc_auc(rel, y)
    conv2, conv3 = roc_auc(_z_sum([sh, fp]), y), roc_auc(_z_sum([sh, fp, rel]), y)
    return {"shape": a_sh, "fp": a_fp, "rel": a_rel, "conv2": conv2, "conv3": conv3,
            "m2": round(conv2 - max(a_sh, a_fp), 4), "m3": round(conv3 - max(a_sh, a_fp, a_rel), 4)}


def _by_seed(seeds: list[str], control: str | None = None, cal: dict | None = None) -> list[tuple]:
    """Per-seed (shape, fingerprint, relational, labels) — scores computed ONCE so the bootstrap re-pools."""
    out = []
    for sd in seeds:
        b = labelled_bridges_xdom([sd], control=control, cal=cal)
        out.append(([shape_score(x) for x in b], [fingerprint_score(x) for x in b],
                    [relational_score(x) for x in b], [x["y"] for x in b]))
    return out


def _pool(groups: list[tuple], idx: list[int]) -> tuple[list, list, list, list]:
    sh, fp, rel, y = [], [], [], []
    for i in idx:
        g = groups[i]
        sh += g[0]; fp += g[1]; rel += g[2]; y += g[3]
    return sh, fp, rel, y


def _call(ci_lo: float, ci_hi: float) -> str:
    return "indeterminate_at_0.05_bar" if ci_lo < CONV_MARGIN_FLOOR < ci_hi \
        else ("clears_0.05" if ci_lo >= CONV_MARGIN_FLOOR else "below_0.05")


def run_convergence(seeds: list[str] | None = None, cal: dict | None = None) -> dict:
    seeds = seeds or HELD_OUT_SEEDS
    groups = _by_seed(seeds, cal=cal)
    n = len(groups)
    full = _pool(groups, list(range(n)))
    a = _margins(*full)
    corr = {"shape_fp": round(_pearson_raw(full[0], full[1]), 4),
            "shape_rel": round(_pearson_raw(full[0], full[2]), 4),
            "fp_rel": round(_pearson_raw(full[1], full[2]), 4)}

    # deterministic seed BOOTSTRAP of BOTH margins (2-way and 3-way) → CI around the 0.05 floor
    b2, b3 = [], []
    for b in range(_BOOTSTRAP):
        idx = [int(_unit("xdom-boot", b, i) * n) % n for i in range(n)]
        m = _margins(*_pool(groups, idx))
        b2.append(m["m2"]); b3.append(m["m3"])
    b2.sort(); b3.sort()
    lo2, hi2 = b2[int(0.025 * _BOOTSTRAP)], b2[int(0.975 * _BOOTSTRAP) - 1]
    lo3, hi3 = b3[int(0.025 * _BOOTSTRAP)], b3[int(0.975 * _BOOTSTRAP) - 1]

    rf = _pool(_by_seed(seeds, control="rewire", cal=cal), list(range(n)))
    ra = _margins(*rf)
    rewire = {"shape_auc": ra["shape"], "fingerprint_auc": ra["fp"], "relational_auc": ra["rel"],
              "conv2_auc": ra["conv2"], "conv3_auc": ra["conv3"]}

    # CONTROL for the positive result (the anti-reverse-trap): a third channel of similar POWER that is a
    # CORRELATED copy of fingerprint (corr≈1, not independent) does NOT clear the bar — so the real
    # relational channel's clear is driven by INDEPENDENCE, not by adding power. Deterministic jitter.
    placebo = [v + 0.02 * (_unit("placebo", i) - 0.5) for i, v in enumerate(full[1])]
    placebo_m3 = _margins(full[0], full[1], placebo, full[3])["m3"]

    power3 = all(v >= POWER_FLOOR for v in (a["shape"], a["fp"], a["rel"]))
    indep_ok = all(abs(v) < INDEP_BOUND for v in corr.values())
    rewire_ok = all(v <= 0.60 for v in rewire.values())
    call2, call3 = _call(lo2, hi2), _call(lo3, hi3)
    outcome = (f"three_independent_channels__3way_convergence_{call3}" if (power3 and indep_ok and rewire_ok)
               else "see_checks")

    return {
        "seeds": n, "seed_namespace": "xe-* (held out from the xd-* tuning/gate seeds)",
        "n_candidates": len(full[3]), "n_positives": sum(full[3]),
        "shape_auc": a["shape"], "fingerprint_auc": a["fp"], "relational_auc": a["rel"],
        "convergence_auc": a["conv2"], "convergence3_auc": a["conv3"],
        "convergence_margin_point": a["m2"], "convergence3_margin_point": a["m3"],
        "margin_bootstrap_ci95": [round(lo2, 4), round(hi2, 4)],
        "margin3_bootstrap_ci95": [round(lo3, 4), round(hi3, 4)],
        "margin_straddles_floor": lo2 < CONV_MARGIN_FLOOR < hi2,
        "margin3_straddles_floor": lo3 < CONV_MARGIN_FLOOR < hi3,
        "channel_correlations": corr, "rewire_control": rewire,
        "correlated_placebo_3way_margin": placebo_m3,  # a correlated 3rd channel of similar power does NOT clear
        "clear_is_from_independence_not_power": placebo_m3 < a["m3"] and placebo_m3 < CONV_MARGIN_FLOOR,
        "preregistered": {"power_floor": POWER_FLOOR, "conv_margin_floor": CONV_MARGIN_FLOOR,
                          "independence_bound": INDEP_BOUND, "bootstrap": _BOOTSTRAP},
        "checks": {"all_three_clear_power_floor": power3, "channels_independent": indep_ok,
                   "rewire_collapses": rewire_ok, "convergence2_margin": call2, "convergence3_margin": call3},
        "outcome": outcome,
        "honest_verdict": (
            "三独立渠道(形状=时序、指纹=SQL、关系=tags;两两 corr 小)+ rewire 后全塌回——结构上真三票。"
            "2-way margin CI 跨 0.05(判不定);3-way 加入第三票后:见 `margin3_bootstrap_ci95` / `convergence3_margin`。"
            "若 3-way CI 整体 >0.05 ⇒ 第三独立渠道把收敛**稳过** 2/2 线(真正面结果);若仍跨 0.05 ⇒ 诚实报『仍判不定』。"
            "各渠道 POWER 是工程构造(常量带可见性调参);独立性 / margin-vs-floor 未调,是可证伪内容。"
        ),
    }
