"""Phase B nexus substrate GATE harness (METRIC_nexus_reality §4 Phase B) — a PRE-CHANNEL acceptance test.

Phase A (the current single-domain substrate) self-reported a killer (METRIC §8): the ⭐ time-coincidence
baseline is near-ceiling at every link, because the real bridge IS a perfect time coincidence by
construction (news frame = event frame = anomaly frame). Time is a sufficient statistic, so a lens has no
honest room to beat it. Phase B's design is the INVERSE pre-registration: make time a WEAK-BUT-PRESENT
adversary so a later semantic/structural lens (CH1/CH2/CH3) can earn its keep.

The design hinges on an UNPROVEN acceptance gate. This harness tests it BEFORE any channel code exists:

    Build a two-domain (infra × library) joint space — K latent classes, ~8 anchor hubs per side, W shared
    incident-windows. A candidate BRIDGE is an anchor-A × anchor-B pair that is CO-TIMED: both fire an
    incident in the SAME window (|Δwindow| = 0). Its label is REAL iff the two anchors share a latent class
    (a genuine cross-domain shared cause), COINCIDENCE otherwise. Crucially the latent class is assigned
    INDEPENDENTLY of the window, so within a window real and coincidence pairs are both co-timed and time
    alone cannot separate them — except for a tunable RESIDUAL: same-class anchors fire at a synchronized
    intra-window phase, so real pairs land at a slightly smaller |Δframe| than coincidence pairs.

    GATE (both must hold at a frozen knob point, pooled over ≥40 seeds):
      (a) time-coincidence ROC-AUC ∈ [0.60, 0.75]  — weak-but-present, neither chance nor ceiling;
      (b) the windows genuinely MIX the K classes, so class is not predictable from window membership.

    Sweep the two design knobs — window_load (anchors firing per window per side) and intra-window
    frame_jitter — to find whether ANY point lands in the band while holding (b). If no point holds (a)+(b)
    the substrate self-rejects by kill-criterion (i) [time stays a sufficient statistic / collapses to
    chance] / (iii) [the only way to weaken time also collapses class-mixing], and the Phase B design must
    change before investing in CH1/CH2/CH3.

HOW (b) IS MEASURED — and a non-obvious statistical correction (see METRIC §8c):
    "Per-window class-entropy ≥ 1 bit" cannot be enforced as the WORST window's entropy (`min` over the
    pool). The min is an order statistic over 3·N windows: it is monotonically NON-improving as seeds are
    added, has NO stable large-sample limit, and for THIS substrate (K=4 over 8 anchors) some seed always
    produces an under-mixed window at any non-degenerate load — so a `min ≥ 1 bit` gate merely measures the
    pool size, not the substrate (it PASSES at N=40 and FAILS at N≥80 for the same knob). The gate therefore
    uses CONVERGENT statistics: mean per-window class-entropy (≥ 1 bit) AND the LEAK-RATE
    P(window entropy < 1 bit) ≤ a small pre-registered tolerance. Both converge in N; the leak-rate falls
    monotonically with window_load, so the robust knob is the highest non-degenerate load.

Honest scope: this reads ONLY anchor identities (from generate()) plus the injected latent-class /
incident-window / jitter joint layer. It is deliberately CHANNEL-BLIND — no news bodies, no throughput, no
semantics — because the gate concerns the TIME adversary's strength, not any lens. The latent class here is
an abstract assignment; the *semantic recoverability* a real cross-domain nexus would carry (shared
vocabulary / structure that CH1/CH2/CH3 read) is deferred channel work, NOT exercised by the gate. The gate
is NECESSARY, not sufficient: it shows time is sub-ceiling, NOT that any lens can recover the latent class.

Reuses: generate() (spec mechanism — proves the two domains are real spec-driven packages), _unit
(sha256 seeding), nexus_eval.roc_auc (tie-correct Mann-Whitney), nexus_baselines.time_coincidence (the ⭐
bar, scored verbatim via each bridge's dframe). Fully deterministic: no random, no clock.
"""
from __future__ import annotations

import math
from collections import Counter

from .data_package import _DEFAULT_ROLES, generate
from .data_synth import _unit
from .nexus_baselines import time_coincidence
from .nexus_eval import roc_auc

# --- the two domains of the joint space (spec ids; their region/port vocabularies are token-disjoint) ---
DOMAIN_A = "infra_demo"
DOMAIN_B = "library_demo"

# --- FROZEN structural knobs (NOT swept — these define the substrate's shape; only load & jitter sweep) ---
K_CLASSES = 4       # latent classes; real ⇔ same class. P(same) ≈ 1/K ⇒ prevalence ≈ 0.25 (honest imbalance)
W_WINDOWS = 3       # shared incident-windows
WINDOW_SPAN = 16    # frames per window; class phases are spread across this span

# --- the pre-registered acceptance gate (independent of any lens — time-AUC is a dumb baseline) ---
TIME_AUC_BAND = (0.60, 0.75)
ENTROPY_FLOOR_BITS = 1.0   # a window "mixes" iff its class-entropy ≥ this
# pre-registered LEAK-RATE tolerance: fraction of windows allowed to dip below the floor. We gate on this
# (a convergent statistic) NOT on the raw worst window (min), which is an N-unstable order statistic with
# no stable limit on this substrate. 0.01 = "≤1% of windows may under-mix" ≈ essentially no window→class
# channel. Disclosed, not tuned to a verdict; the full leak-rate curve is reported so any τ can be applied.
LEAK_RATE_TOL = 0.01

# --- swept design knobs ---
SWEEP_LOADS = (2, 3, 4, 5, 6, 7)              # anchors firing per window per side (< n_anchors=8; 8 = degenerate)
SWEEP_JITTERS = (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20)  # intra-window frame-jitter span


def anchors(source_id: str) -> list[str]:
    """The anchor-hub ids for a domain, taken from its spec via generate(). Identities are
    seed-independent (hubs are built from the spec, not the seed), so the seed varies only the joint
    latent-class / incident layer below — exactly what the ≥40-seed pool averages over."""
    pkg = generate(source_id, seed=source_id)
    if pkg is None:
        raise ValueError(f"unknown data_source spec: {source_id!r}")
    roles = pkg.get("roles", _DEFAULT_ROLES)
    return [h["id"] for h in pkg["stores"]["sql"][roles["hub_store"]]]


def _latent_class(seed: str, side: str, hub_id: str) -> int:
    """Each anchor's latent class — assigned by hash of (seed, side, id), INDEPENDENTLY of any window.
    This independence is the whole point: it forbids predicting class from window membership."""
    return int(_unit(seed, "class", side, hub_id) * K_CLASSES) % K_CLASSES


def _roster(seed: str, side: str, w: int, hubs: list[str], load: int) -> list[str]:
    """The ``load`` anchors that fire an incident in window ``w`` — the top-``load`` by a hash rank that
    does NOT depend on class, so a window's class mix is unbiased (keeps class ⟂ window)."""
    return sorted(hubs, key=lambda h: _unit(seed, "fire", side, w, h))[:max(0, min(load, len(hubs)))]


def _phase(seed: str, w: int, k: int) -> float:
    """Class ``k``'s incident phase WITHIN window ``w`` — spread across the span by class index plus a
    per-(window,class) wobble. Same-class anchors share this phase (→ they fire synchronously → real pairs
    sit at small |Δframe|); distinct classes sit at distinct phases (→ coincidence pairs sit further apart).
    The span/K spacing vs. the jitter span is what makes time a tunable adversary."""
    slot = (k + 0.5) * (WINDOW_SPAN / K_CLASSES)
    wobble = (_unit(seed, "phase", w, k) - 0.5) * (WINDOW_SPAN / K_CLASSES) * 0.5
    return slot + wobble


def _offset(seed: str, side: str, hub_id: str, w: int, k: int, jitter: float) -> int:
    """Integer intra-window position of an anchor's incident: class phase + per-anchor jitter (span
    ``jitter``), rounded. NOT clamped to the window edges: the window is a CATEGORICAL grouping (roster
    membership), and dframe is only ever computed BETWEEN two incidents of the SAME window, so the absolute
    position cancels and only the phase+jitter difference matters. (Clamping to [0, span-1] would crush the
    outer classes' jitter tails against the edges — a class-asymmetric distortion that silently inflated
    time-AUC by ~0.02; removed. See METRIC §8c.)"""
    j = (_unit(seed, "jit", side, hub_id, w) - 0.5) * jitter
    return int(round(_phase(seed, w, k) + j))


def _entropy_bits(classes: list[int]) -> float:
    """Shannon entropy (bits) of a class multiset — 0 when one class dominates, up to log2(K) when even."""
    n = len(classes)
    if n == 0:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in Counter(classes).values())


def candidate_bridges(seed: str, *, window_load: int, frame_jitter: float,
                      anchors_a: list[str], anchors_b: list[str]) -> tuple[list[dict], list[float]]:
    """The co-timed candidate set for ONE seed: for each shared window, every anchor-A × anchor-B pair that
    both fire in it (|Δwindow| = 0). Each bridge carries ``dframe`` (so time_coincidence scores it verbatim)
    and ``y`` (1 = real ⇔ same latent class). Also returns per-window class-entropy (over the anchors that
    fire in the window, both sides) for the gate's mixing constraint."""
    bridges: list[dict] = []
    per_window_entropy: list[float] = []
    for w in range(W_WINDOWS):
        roster_a = _roster(seed, "A", w, anchors_a, window_load)
        roster_b = _roster(seed, "B", w, anchors_b, window_load)
        class_a = {h: _latent_class(seed, "A", h) for h in roster_a}
        class_b = {h: _latent_class(seed, "B", h) for h in roster_b}
        per_window_entropy.append(_entropy_bits(list(class_a.values()) + list(class_b.values())))
        off_a = {h: _offset(seed, "A", h, w, class_a[h], frame_jitter) for h in roster_a}
        off_b = {h: _offset(seed, "B", h, w, class_b[h], frame_jitter) for h in roster_b}
        for ha in roster_a:
            for hb in roster_b:
                y = 1 if class_a[ha] == class_b[hb] else 0
                bridges.append({
                    "seed": seed, "window": w, "a": ha, "b": hb,
                    "class_a": class_a[ha], "class_b": class_b[hb],
                    "dframe": abs(off_a[ha] - off_b[hb]),
                    "y": y, "label": "real" if y else "coincidence",
                })
    return bridges, per_window_entropy


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    return sorted_vals[min(len(sorted_vals) - 1, max(0, int(q * (len(sorted_vals) - 1))))]


def gate_point(seeds: list[str], *, window_load: int, frame_jitter: float,
               anchors_a: list[str] | None = None, anchors_b: list[str] | None = None) -> dict:
    """Pool the co-timed candidate set over ``seeds`` at a fixed (window_load, frame_jitter) and report the
    two gate quantities: time-coincidence ROC-AUC, and the per-window class-mixing statistics. The mixing
    leg is summarized by CONVERGENT stats (mean, leak-rate, 5th-percentile); ``min_entropy`` is included
    only as a diagnostic and is flagged N-unstable (worst-of-pool order statistic)."""
    anchors_a = anchors_a if anchors_a is not None else anchors(DOMAIN_A)
    anchors_b = anchors_b if anchors_b is not None else anchors(DOMAIN_B)
    pooled: list[dict] = []
    entropies: list[float] = []
    for sd in seeds:
        br, pw = candidate_bridges(sd, window_load=window_load, frame_jitter=frame_jitter,
                                   anchors_a=anchors_a, anchors_b=anchors_b)
        pooled.extend(br)
        entropies.extend(pw)
    labels = [b["y"] for b in pooled]
    scores = [time_coincidence(b) for b in pooled]
    n_real = sum(labels)
    es = sorted(entropies)
    n_win = len(es) or 1
    leak = sum(e < ENTROPY_FLOOR_BITS for e in es) / n_win
    return {
        "window_load": window_load, "frame_jitter": frame_jitter, "seeds": len(seeds),
        "n_bridges": len(pooled), "n_real": n_real, "n_coincidence": len(pooled) - n_real,
        "prevalence": round(n_real / len(pooled), 4) if pooled else 0.0,
        "time_auc": roc_auc(scores, labels),
        "mean_entropy": round(sum(es) / n_win, 4),
        "leak_rate": round(leak, 4),                       # P(window entropy < floor) — CONVERGENT
        "p05_entropy": round(_percentile(es, 0.05), 4),    # 5th-percentile window entropy — CONVERGENT
        "min_entropy": round(es[0], 4),                    # diagnostic only: N-UNSTABLE order statistic
        "n_windows": len(es),
    }


def gate_sweep(seeds: list[str] | None = None, *, loads: tuple[int, ...] = SWEEP_LOADS,
               jitters: tuple[float, ...] = SWEEP_JITTERS, leak_tol: float = LEAK_RATE_TOL) -> dict:
    """Sweep (window_load × frame_jitter) and decide whether the acceptance band is REACHABLE.

    A grid point ACCEPTS iff time-AUC ∈ TIME_AUC_BAND AND the class-mixing leg holds under the CONVERGENT
    reading: mean per-window class-entropy ≥ ENTROPY_FLOOR AND leak-rate ≤ ``leak_tol``. ``reachable`` = at
    least one accepting point exists. If False, the substrate self-rejects (kill-criterion i/iii) and
    Phase B must be redesigned before any channel code. The recommended frozen knob is the accepting point
    with the LOWEST leak-rate (most robust class-mixing), tie-broken by AUC nearest the band centre."""
    # Pool sizing: ≥40 seeds stabilizes the AUC (per seed ~tens of pairs at ~25% prevalence). But the
    # leak-rate is a ~0–2% quantity, so estimating it needs N·W·τ ≫ 1 windows — ≥~200. We default to 400
    # so BOTH legs are converged; at N=40 the leak-rate is too coarse (reads 0% for loads whose true rate
    # is ~1–2%), which would resurrect the very small-sample artifact this gate was corrected to avoid.
    seeds = seeds or [f"pb-{i}" for i in range(400)]
    anchors_a, anchors_b = anchors(DOMAIN_A), anchors(DOMAIN_B)
    lo, hi = TIME_AUC_BAND
    grid: list[dict] = []
    for L in loads:
        for J in jitters:
            pt = gate_point(seeds, window_load=L, frame_jitter=J, anchors_a=anchors_a, anchors_b=anchors_b)
            pt["in_band"] = lo <= pt["time_auc"] <= hi
            pt["entropy_ok"] = pt["mean_entropy"] >= ENTROPY_FLOOR_BITS and pt["leak_rate"] <= leak_tol
            pt["accept"] = pt["in_band"] and pt["entropy_ok"]
            grid.append(pt)
    accepting = sorted((g for g in grid if g["accept"]),
                       key=lambda g: (g["leak_rate"], abs(g["time_auc"] - sum(TIME_AUC_BAND) / 2), g["window_load"]))
    return {
        "domains": [DOMAIN_A, DOMAIN_B], "n_anchors": [len(anchors_a), len(anchors_b)],
        "K_classes": K_CLASSES, "W_windows": W_WINDOWS, "window_span": WINDOW_SPAN,
        "time_auc_band": TIME_AUC_BAND, "entropy_floor_bits": ENTROPY_FLOOR_BITS, "leak_rate_tol": leak_tol,
        "seeds": len(seeds), "reachable": bool(accepting), "n_accepting": len(accepting),
        "accepting_points": accepting, "grid": grid,
    }


def _fmt_report(res: dict) -> str:
    """Human-readable verdict for the harness CLI."""
    lo, hi = res["time_auc_band"]
    tol = res["leak_rate_tol"]
    lines = [
        "=" * 84,
        "Phase B nexus substrate — TIME-COINCIDENCE acceptance gate (pre-channel)",
        "=" * 84,
        f"domains      : {res['domains'][0]} × {res['domains'][1]}  (anchors {res['n_anchors'][0]}×{res['n_anchors'][1]})",
        f"structure    : K={res['K_classes']} latent classes · W={res['W_windows']} windows · span={res['window_span']} frames",
        f"pool         : {res['seeds']} frozen seeds   candidate set = co-timed anchor×anchor (|Δwindow|=0)",
        f"GATE (a)     : time-coincidence AUC ∈ [{lo:.2f},{hi:.2f}]   (weak-but-present, neither chance nor ceiling)",
        f"GATE (b)     : windows mix classes — mean entropy ≥ {res['entropy_floor_bits']:.1f} bit AND leak-rate ≤ {tol:.0%}",
        f"               (leak-rate = P(window < {res['entropy_floor_bits']:.0f} bit); CONVERGENT. NOT the worst window —",
        f"                'min' is an N-unstable order statistic, shown only as a diagnostic.)",
        "-" * 84,
        f"{'load':>4} {'jitter':>6} {'bridges':>7} {'prev':>5} {'time_AUC':>8} {'meanH':>6} {'leak%':>6} {'p05H':>5} {'(minH)':>7}  verdict",
    ]
    for g in res["grid"]:
        if g["accept"]:
            v = "ACCEPT ✓"
        elif not g["entropy_ok"]:
            v = f"leak>{tol:.0%}" if g["mean_entropy"] >= res["entropy_floor_bits"] else "meanH<1bit"
        elif g["time_auc"] < lo:
            v = "AUC<band"
        else:
            v = "AUC>band"
        lines.append(
            f"{g['window_load']:>4} {g['frame_jitter']:>6} {g['n_bridges']:>7} {g['prevalence']:>5.2f} "
            f"{g['time_auc']:>8.4f} {g['mean_entropy']:>6.3f} {g['leak_rate'] * 100:>5.1f}% {g['p05_entropy']:>5.2f} "
            f"{g['min_entropy']:>7.2f}  {v}"
        )
    lines.append("-" * 84)
    if res["reachable"]:
        best = res["accepting_points"][0]
        lines += [
            f"VERDICT: BAND REACHABLE — {res['n_accepting']} accepting knob point(s).",
            f"  robust frozen knob (lowest leak-rate): window_load={best['window_load']}, "
            f"frame_jitter={best['frame_jitter']}  → time-AUC={best['time_auc']:.4f}, "
            f"mean entropy={best['mean_entropy']:.3f} bit, leak-rate={best['leak_rate']:.2%}, prevalence={best['prevalence']:.2f}",
            "  ⇒ Phase B substrate is viable on GATE terms: time is weak-but-present and windows mix classes.",
            "",
            "  CAVEAT (load-bearing — see METRIC §7/§8c): the gate is NECESSARY, not SUFFICIENT. It shows only",
            "  that time is SUB-CEILING and windows mix classes — NOT that any lens can beat time. The latent",
            "  class is an abstract sha256 label with NO observable semantics, so right now NOTHING (not a lens,",
            "  not time) can recover it; the gate is deliberately channel-blind. Giving same-class anchors a",
            "  recoverable observable correlate, and showing a time-FREE channel exceeds time, is CH1/CH2/CH3",
            "  work. The 'window_load' threshold is bound to (K=4, 8 anchors/side), not a universal constant.",
        ]
    else:
        lines += [
            f"VERDICT: BAND EMPTY — no (window_load, frame_jitter) holds AUC ∈ [{lo:.2f},{hi:.2f}] with mean",
            f"  entropy ≥ {res['entropy_floor_bits']:.1f} bit and leak-rate ≤ {tol:.0%}.",
            "  ⇒ Substrate self-rejects by kill-criterion (i)/(iii). REDESIGN Phase B before any channel code.",
        ]
    lines.append("=" * 84)
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover — manual harness run
    print(_fmt_report(gate_sweep()))
