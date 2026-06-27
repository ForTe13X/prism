"""Cross-domain Sinkhorn alignment (DESIGN_visual_fusion §2 — the animated "money moment" engine).

The two galaxies do not just sit there: they are pulled together by a REAL alignment process. We run a
deterministic entropic optimal transport (Sinkhorn) between the anchor units of domain A and domain B, with
a cost matrix built from the three independent channels (shape / fingerprint / relational dissimilarity).
Each iteration produces a transport plan T_k and a marginal RESIDUAL; the residual drives the inter-galaxy
distance and the bridges ignite as the transport mass concentrates on the true couplings (animation == the
iteration replay, never a scripted keyframe — the honesty bar of §0/§6).

Two products:
  * ``steps`` — the per-iteration residual + the sparse transport, the data the animated visual scrubs;
  * a per-bridge transport mass T[i][j] — a GLOBAL-assignment signal that adds the mutual exclusivity the
    per-bridge channels lack (each A unit's mass sums to one), so it can recover the 1:1 coupling more
    sharply than any single channel. Whether it actually beats them is MEASURED (run_alignment_eval), not
    assumed. Pure-Python, deterministic (no numpy, no random/clock).
"""
from __future__ import annotations

import math

from .data_package_xdom import generate_xdom
from .nexus_chan_fingerprint import fingerprint_score
from .nexus_chan_relational import relational_score
from .nexus_chan_shape import shape_score
from .nexus_eval import roc_auc
from .nexus_xdom_substrate import candidate_bridges_xdom

REG = 0.06        # entropic regularisation (smaller = sharper assignment, slower to converge)
ITERS = 60        # Sinkhorn iterations
SNAPSHOTS = 16    # how many iteration snapshots to return for the animation


def _bridge_cost(b: dict) -> float:
    """Combined channel DISSIMILARITY in [0,1] (low = the three independent channels all say 'coupled')."""
    shape_d = (1.0 - shape_score(b)) / 2.0                 # corr∈[-1,1] → [0,1]
    fp_d = -fingerprint_score(b) / 2.0                     # −L1∈[−2,0] → L1/2∈[0,1]
    rel_d = 1.0 - relational_score(b)                      # jaccard∈[0,1] → [0,1]
    return (shape_d + fp_d + rel_d) / 3.0


def _cost_matrix(g: dict) -> tuple[list, list, list, list]:
    """Cost over (anchor A_i × anchor B_j) + the index lists + the truth set, for one package."""
    bridges, ctx = candidate_bridges_xdom(g)
    ai = sorted(ctx["anA"]); bi = sorted(ctx["anB"])
    pos = {(b["a_idx"], b["b_idx"]): b for b in bridges}
    cost = [[_bridge_cost(pos[(i, j)]) for j in bi] for i in ai]
    return cost, ai, bi, g["coupling"]


def sinkhorn(cost: list[list[float]], reg: float = REG, iters: int = ITERS) -> dict:
    """Entropic OT with uniform marginals. Returns the final transport + per-iteration residuals/snapshots."""
    n, m = len(cost), (len(cost[0]) if cost else 0)
    if n == 0 or m == 0:
        return {"T": [], "residuals": [], "snapshots": []}
    a, b = [1.0 / n] * n, [1.0 / m] * m
    K = [[math.exp(-cost[i][j] / reg) for j in range(m)] for i in range(n)]
    u, v = [1.0] * n, [1.0] * m
    residuals, snaps = [], []
    snap_at = {max(0, round(k * (iters - 1) / max(1, SNAPSHOTS - 1))) for k in range(SNAPSHOTS)}
    for it in range(iters):
        # v then u (standard Sinkhorn updates)
        for j in range(m):
            s = sum(K[i][j] * u[i] for i in range(n)) or 1e-12
            v[j] = b[j] / s
        for i in range(n):
            s = sum(K[i][j] * v[j] for j in range(m)) or 1e-12
            u[i] = a[i] / s
        # convergence residual = how far the COLUMN sums still drift from their target (the u-update just
        # fixed the rows exactly, so the columns are what shrink toward 0 as the plan converges — this is
        # the curve that pulls the two galaxies together in the animation).
        col = [sum(u[i] * K[i][j] * v[j] for i in range(n)) for j in range(m)]
        res = max(abs(col[j] - b[j]) for j in range(m))
        residuals.append(round(res, 6))
        if it in snap_at:
            T = [[round(u[i] * K[i][j] * v[j], 5) for j in range(m)] for i in range(n)]
            snaps.append({"iter": it, "residual": round(res, 6), "transport": T})
    T = [[u[i] * K[i][j] * v[j] for j in range(m)] for i in range(n)]
    return {"T": T, "residuals": residuals, "snapshots": snaps}


def run_alignment(seed: str) -> dict:
    """One package → the cost matrix, the Sinkhorn iteration sequence (for the animation), and the
    per-pair transport tagged real/coincidence (the visual ignites the high-T true pairs as it converges)."""
    g = generate_xdom(seed)
    cost, ai, bi, coupling = _cost_matrix(g)
    sk = sinkhorn(cost)
    truth = set(coupling)
    pairs = []
    for x, i in enumerate(ai):
        for y, j in enumerate(bi):
            pairs.append({"a_idx": i, "b_idx": j, "transport": round(sk["T"][x][y], 5),
                          "cost": round(cost[x][y], 4), "real": (i, j) in truth})
    return {
        "seed": seed, "n_anchor_a": len(ai), "n_anchor_b": len(bi),
        "iters": ITERS, "reg": REG,
        "residuals": sk["residuals"], "snapshots": sk["snapshots"],
        "pairs": pairs,
        "note": ("Sinkhorn 软对齐:残差逐迭代降→星系拉近;真桥按 transport 质量逐条点亮。"
                 "动画=真实对齐回放,非预录关键帧。transport 加了互斥(行和=1),是全局指派信号。"),
    }


def run_alignment_eval(seeds: list[str] | None = None) -> dict:
    """Does the OT transport (with its global mutual-exclusivity) recover the coupling better than the
    per-bridge channels? Pooled AUC of T vs the labels, against each single channel — MEASURED."""
    seeds = seeds or [f"xe-{i}" for i in range(60)]
    t_scores, sh, fp, rl, y = [], [], [], [], []
    for sd in seeds:
        g = generate_xdom(sd)
        bridges, ctx = candidate_bridges_xdom(g)
        cost, ai, bi, coupling = _cost_matrix(g)
        sk = sinkhorn(cost)
        tmap = {(ai[x], bi[yk]): sk["T"][x][yk] for x in range(len(ai)) for yk in range(len(bi))}
        for b in bridges:
            t_scores.append(tmap.get((b["a_idx"], b["b_idx"]), 0.0))
            sh.append(shape_score(b)); fp.append(fingerprint_score(b)); rl.append(relational_score(b))
            y.append(b["y"])
    auc = {"transport": roc_auc(t_scores, y), "shape": roc_auc(sh, y),
           "fingerprint": roc_auc(fp, y), "relational": roc_auc(rl, y)}
    best_single = max(auc["shape"], auc["fingerprint"], auc["relational"])
    return {
        "seeds": len(seeds), "n_candidates": len(y), "n_positives": sum(y), "auc": auc,
        "transport_beats_best_single": auc["transport"] > best_single,
        "margin_over_best_single": round(auc["transport"] - best_single, 4),
        "note": "OT 的互斥(行和=1)若让 transport AUC > 任一单渠道,则全局指派比逐桥打分更准(像 Phase-A 的公理互斥)。",
    }
