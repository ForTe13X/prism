"""Phase-B per-bridge nexus_confidence for ONE coupled package — the data the visual renders (METRIC §1).

GLOW = ABSOLUTE significance under multiple-comparison control (the OBSERVER §13 fix). Earlier this used a
RELATIVE top-decile per channel, which force-lights ~10% of EVERY package's bridges — so a zero-coupling
pair lit ~8 "high" bridges just like a true pair (the count never distinguished real from fake; only the
ranking did). The N-domain blow-up follows: false-high ∝ C(N,2) while true bridges stay sparse ⇒ precision
collapses. CACE (METRIC §2's permutation/FDR lens) is exactly the missing piece.

The fix: build a PERMUTATION NULL from independent cross-pairs (this package's A domain × an unrelated
package's B domain — same machinery, byte-identical channels, but no shared coupling), get each real
bridge's per-channel right-tail p-value against that null, COMBINE the 3 independent channels by Fisher
(χ²_6), then apply Benjamini–Hochberg FDR across the package's candidates at q. ``high`` (the only thing
that glows) = survives BH. A zero-coupling pair now EXTINGUISHES — its scores look like the null, BH rejects
≈ 0 — so "only verified bridges glow" is finally TRUE, not just relatively-brightest. The old relative
≥2/3 vote is kept as ``medium`` (ranked-high-but-not-FDR-significant), shown dim, never glowing.

Deterministic: the null seeds are derived from the package seed; no random, no clock.
"""
from __future__ import annotations

import bisect
import math

from .data_package_xdom import generate_xdom
from .nexus_chan_fingerprint import fingerprint_score
from .nexus_chan_relational import relational_score
from .nexus_chan_shape import shape_score
from .nexus_xdom_substrate import candidate_bridges_xdom, rewired_coupling

FIRE_FRAC = 0.10   # the RELATIVE per-channel top-fraction (now only feeds the dim `medium` tier)
FDR_Q = 0.10       # Benjamini–Hochberg target false-discovery rate among the GLOWING (high) bridges
N_NULL = 8         # independent cross-pair packages pooled for the permutation null (~N_NULL×anchors² samples)
_TINY = 1e-12


def _scores(bridges: list) -> tuple[list, list, list]:
    return ([shape_score(b) for b in bridges], [fingerprint_score(b) for b in bridges],
            [relational_score(b) for b in bridges])


def _fires(scores: list[float]) -> list[bool]:
    """Top-FIRE_FRAC by score (label-free, relative) — feeds the `medium` tier only."""
    if not scores:
        return []
    k = max(1, round(len(scores) * FIRE_FRAC))
    cutoff = sorted(scores, reverse=True)[k - 1]
    return [s >= cutoff for s in scores]


def _null_pools(seed: str) -> tuple[list, list, list]:
    """Permutation null: pair THIS package's A domain with N_NULL UNRELATED packages' B domains (no shared
    coupling) and pool the per-channel scores. These are what a channel scores when there is genuinely no
    nexus — the absolute reference the real bridges are tested against. Sorted for right-tail lookup."""
    gA = generate_xdom(seed)
    nsh: list[float] = []
    nfp: list[float] = []
    nrl: list[float] = []
    for k in range(N_NULL):
        gB = generate_xdom(f"{seed}~null{k}")
        cross = {"A": gA["A"], "B": gB["B"], "coupling": [], "seed": seed}  # independent A×B ⇒ zero coupling
        nb, _ = candidate_bridges_xdom(cross)
        s, f, r = _scores(nb)
        nsh += s; nfp += f; nrl += r
    return sorted(nsh), sorted(nfp), sorted(nrl)


def _right_p(score: float, null_sorted: list[float]) -> float:
    """Right-tail p-value of ``score`` against the null ECDF: (1 + #{null ≥ score}) / (1 + N) — never 0."""
    n = len(null_sorted)
    if n == 0:
        return 1.0
    ge = n - bisect.bisect_left(null_sorted, score)
    return (1.0 + ge) / (1.0 + n)


def _fisher_p(ps: list[float]) -> float:
    """Combine independent per-channel p-values (Fisher). X = -2 Σ ln p ~ χ²_{2·k}; closed-form survival
    for even df=2k: exp(-X/2)·Σ_{i<k} (X/2)^i / i!. The 3 channels are designed independent (corr 0.13–0.19),
    so Fisher is appropriate (slight residual dependence ⇒ mildly anti-conservative — disclosed)."""
    k = len(ps)
    x = -2.0 * sum(math.log(max(p, _TINY)) for p in ps)
    half = x / 2.0
    term, acc = 1.0, 1.0
    for i in range(1, k):
        term *= half / i
        acc += term
    return min(1.0, math.exp(-half) * acc)


def _bh_reject(pvals: list[float], q: float) -> list[bool]:
    """Benjamini–Hochberg: reject the p_(k) with the largest k where p_(k) ≤ (k/m)·q, and all below it."""
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    kmax = 0
    for rank, idx in enumerate(order, start=1):
        if pvals[idx] <= (rank / m) * q:
            kmax = rank
    keep = set(order[:kmax])
    return [i in keep for i in range(m)]


def _tier_bridges(bridges: list, null: tuple[list, list, list], q: float) -> tuple[list, list]:
    """Return (per-bridge combined p, per-bridge tier). high = BH-significant (glows); medium = relative
    ≥2/3 vote but NOT FDR-significant (dim); coincidence = neither."""
    sh, fp, rl = _scores(bridges)
    nsh, nfp, nrl = null
    pcomb = [_fisher_p([_right_p(s, nsh), _right_p(f, nfp), _right_p(r, nrl)]) for s, f, r in zip(sh, fp, rl)]
    reject = _bh_reject(pcomb, q)
    votes = [a + b + c for a, b, c in zip(_fires(sh), _fires(fp), _fires(rl))]
    tiers = ["high" if reject[i] else ("medium" if votes[i] >= 2 else "coincidence") for i in range(len(bridges))]
    return pcomb, tiers


def bridge_view(seed: str) -> dict:
    g = generate_xdom(seed)
    bridges, ctx = candidate_bridges_xdom(g)
    null = _null_pools(seed)
    sh, fp, rl = _scores(bridges)
    sh_fire, fp_fire, rl_fire = _fires(sh), _fires(fp), _fires(rl)
    pcomb, tiers = _tier_bridges(bridges, null, FDR_Q)

    out, counts = [], {"high": 0, "medium": 0, "coincidence": 0}
    for idx, b in enumerate(bridges):
        votes = sh_fire[idx] + fp_fire[idx] + rl_fire[idx]
        tier = tiers[idx]
        counts[tier] += 1
        out.append({
            "a_idx": b["a_idx"], "b_idx": b["b_idx"], "a_id": b["a_id"], "b_id": b["b_id"],
            "shape": round(sh[idx], 4), "fingerprint": round(fp[idx], 4), "relational": round(rl[idx], 4),
            "shape_fires": sh_fire[idx], "fingerprint_fires": fp_fire[idx], "relational_fires": rl_fire[idx],
            "votes": votes, "p_combined": round(pcomb[idx], 5), "fdr_significant": tier == "high",
            "confidence": tier, "dissent": (0 < votes < 3),
            "_truth": b["y"],   # view scoreboard ONLY — the tiering above never reads it
        })

    high = [o for o in out if o["confidence"] == "high"]
    lit_precision = round(sum(o["_truth"] for o in high) / len(high), 3) if high else None
    return {
        "seed": seed,
        "A": {"prefix": g["A"]["prefix"], "metric": g["A"]["metric"],
              "units": [{"idx": i, "id": u["id"], "anchor": i in ctx["anA"]} for i, u in enumerate(g["A"]["units"])]},
        "B": {"prefix": g["B"]["prefix"], "metric": g["B"]["metric"],
              "units": [{"idx": j, "id": u["id"], "anchor": j in ctx["anB"]} for j, u in enumerate(g["B"]["units"])]},
        "bridges": out,
        "scorecard": {"candidates": len(out), **counts, "true_couplings": sum(o["_truth"] for o in out),
                      "high_tier_precision": lit_precision, "fdr_q": FDR_Q, "null_samples": len(null[0]),
                      "expected_false_high": round(FDR_Q * counts["high"], 2)},
        "caveat": ("跨源 link 原型(双域)。高亮=三独立渠道(形状⊥指纹⊥关系)Fisher 合并 p 过 Benjamini–Hochberg "
                   f"FDR(q={FDR_Q})——**绝对显著阈 + 多重比较控制(CACE,§13 修复)**,非相对 top-decile;故零耦合对"
                   "**会熄灭**(光真区分真假)。dim「medium」=相对排名高但未过 FDR。期望假高桥≈q×高桥数。"),
    }


def _old_relative_high(bridges: list) -> int:
    """OLD rule: ≥2/3 of the per-channel relative top-decile _fires (no FDR) — for the SAME-construction
    'before' number, so the before→after comparison is apples-to-apples on one control."""
    sh, fp, rl = _scores(bridges)
    votes = [a + b + c for a, b, c in zip(_fires(sh), _fires(fp), _fires(rl))]
    return sum(1 for v in votes if v >= 2)


def fdr_extinction_check(seeds: list[str] | None = None) -> dict:
    """OBSERVER §13/§14 verification with TWO controls measuring TWO failure modes (no construct-swap):
      * CROSS-PAIR zero (this A × an UNRELATED B) — a genuine no-nexus pair; the glow MUST extinguish. The
        before→after is measured SAME-CONSTRUCTION (old relative rule vs new FDR on the SAME cross-pair),
        so the headline is honest (~7.17 → ~0.00), not a swap of the rewire number for the cross-pair one.
      * REWIRE zero (identical observations, only the truth labels permuted) — the coupling signal is still
        physically there, so this is an AUC failure mode (§8e, rewire AUC ≈0.46), NOT a no-nexus pair. It
        stays lit (~4.27, precision ≈0) under the new rule AND SHOULD: extinction is the wrong tool for it.
    """
    seeds = seeds or [f"xe-{i}" for i in range(30)]
    real_high, real_prec = [], []
    cross_new, cross_old = [], []          # extinction control (unrelated A×B), SAME-construction before/after
    rewire_new, rewire_prec = [], []       # AUC control (identical obs, labels permuted) — should stay lit
    for sd in seeds:
        gA = generate_xdom(sd)
        null = _null_pools(sd)
        rb, _ = candidate_bridges_xdom(gA)
        _, rt = _tier_bridges(rb, null, FDR_Q)
        rhi = [i for i, t in enumerate(rt) if t == "high"]
        real_high.append(len(rhi))
        if rhi:
            real_prec.append(sum(rb[i]["y"] for i in rhi) / len(rhi))
        # cross-pair zero: this A × an unrelated B — the no-nexus pair; NEW (FDR) vs OLD (relative)
        gB = generate_xdom(f"{sd}~zero")
        zx = {"A": gA["A"], "B": gB["B"], "coupling": [], "seed": sd}
        zb, _ = candidate_bridges_xdom(zx)
        _, zt = _tier_bridges(zb, null, FDR_Q)
        cross_new.append(sum(1 for t in zt if t == "high"))
        cross_old.append(_old_relative_high(zb))
        # rewire zero: identical observations, only labels permuted — the AUC failure mode (§8e)
        wb, _ = candidate_bridges_xdom(gA, coupling=rewired_coupling(gA))
        _, wt = _tier_bridges(wb, null, FDR_Q)
        whi = [i for i, t in enumerate(wt) if t == "high"]
        rewire_new.append(len(whi))
        if whi:
            rewire_prec.append(sum(wb[i]["y"] for i in whi) / len(whi))
    n = len(seeds)
    avg = lambda xs: round(sum(xs) / len(xs), 3) if xs else None  # noqa: E731
    return {
        "seeds": n, "fdr_q": FDR_Q,
        "real_pair_mean_high": avg(real_high), "real_pair_high_precision": avg(real_prec),
        # extinction control (unrelated domains), measured SAME-CONSTRUCTION:
        "cross_pair_old_mean_high": avg(cross_old), "cross_pair_new_mean_high": avg(cross_new),
        "extinguishes_on_cross_pair": (sum(cross_new) / n) < 1.0,
        # AUC control (rewire): SHOULD stay lit — extinction is the wrong tool here:
        "rewire_new_mean_high": avg(rewire_new), "rewire_high_precision": avg(rewire_prec),
        "verdict": (
            "Extinction is measured SAME-CONSTRUCTION on the cross-pair null (unrelated A×B): "
            f"old relative rule ≈{avg(cross_old)} high → new FDR ≈{avg(cross_new)} high ⇒ extinguishes. "
            f"The REWIRE control (identical observations, labels permuted) stays ≈{avg(rewire_new)} high at "
            f"precision ≈{avg(rewire_prec)} under the new rule — AND SHOULD: rewire keeps the coupling signal "
            "and only randomizes truth, so it is an AUC failure mode (§8e, rewire AUC ≈0.46), not a no-nexus "
            "pair; extinction is the wrong tool for it. Two controls, two failure modes."),
    }
