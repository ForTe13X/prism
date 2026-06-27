"""Phase-B per-bridge nexus_confidence for ONE coupled package — the data the visual renders (METRIC §1).

Each cross-domain candidate (A_i,B_j) gets a confidence tier from the convergence of the two INDEPENDENT
channels: a channel "fires" for a bridge iff its score is in the top FIRE_FRAC of that package's candidates
(a LABEL-FREE, per-package quantile — so the tiering never sees the eval label and cannot be reverse-trap
tuned to it). Both fire → ``high`` (a verified nexus); exactly one → ``medium`` (single-channel, dissent);
neither → ``coincidence`` (a ghost). The honest-sparsity discipline falls out for free: only the
top-of-both bridges light, the rest stay ghosts — and the scorecard reports the counts so the sparsity is
legible, never hidden. ``_truth`` per bridge is included for the view's OWN scoreboard only (precision of
the lit set), clearly separated; the tiering itself never reads it.
"""
from __future__ import annotations

from .data_package_xdom import generate_xdom
from .nexus_chan_fingerprint import fingerprint_score
from .nexus_chan_shape import shape_score
from .nexus_xdom_substrate import candidate_bridges_xdom

FIRE_FRAC = 0.10  # a channel fires for the top 10% of a package's candidates by that channel's score


def _fires(scores: list[float]) -> list[bool]:
    """Top-FIRE_FRAC by score fire (label-free). Ties at the cutoff fire too, so it never splits equals."""
    if not scores:
        return []
    k = max(1, round(len(scores) * FIRE_FRAC))
    cutoff = sorted(scores, reverse=True)[k - 1]
    return [s >= cutoff for s in scores]


def bridge_view(seed: str) -> dict:
    g = generate_xdom(seed)
    bridges, ctx = candidate_bridges_xdom(g)
    sh = [shape_score(b) for b in bridges]
    fp = [fingerprint_score(b) for b in bridges]
    sh_fire, fp_fire = _fires(sh), _fires(fp)

    out, counts = [], {"high": 0, "medium": 0, "coincidence": 0}
    for b, s, f, sfire, ffire in zip(bridges, sh, fp, sh_fire, fp_fire):
        tier = "high" if (sfire and ffire) else ("medium" if (sfire or ffire) else "coincidence")
        counts[tier] += 1
        out.append({
            "a_idx": b["a_idx"], "b_idx": b["b_idx"], "a_id": b["a_id"], "b_id": b["b_id"],
            "shape": round(s, 4), "fingerprint": round(f, 4),
            "shape_fires": sfire, "fingerprint_fires": ffire,
            "confidence": tier, "dissent": (sfire != ffire),  # exactly one channel → single-lens dissent
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
                      "high_tier_precision": lit_precision},
        "caveat": ("跨源 link 原型(双域),非已证跨域 nexus。高亮=两独立渠道(形状⊥指纹)皆入各自 top-"
                   f"{int(FIRE_FRAC * 100)}%;判别力本身在抽样噪声内未稳过 2/2 线(见 METRIC §8d)。光多少=过双渠道的桥多少,稀疏是诚实的。"),
    }
