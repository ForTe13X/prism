"""Nexus eval harness (METRIC_nexus_reality §4) — deterministic, stdlib-only scoring of a bridge scorer
against its eval labels: ROC-AUC (tie-correct Mann–Whitney), average precision, ECE, plus the runners that
sweep the baseline ladder across the link/dirtiness knobs and the negative controls.

This is where the honesty命门 lives: it quantifies the BAR (the time-coincidence baseline's AUC). The M0
finding (METRIC §8): on this substrate time is near-ceiling at EVERY link (real bridge ≡ temporal
coincidence by construction), so "strictly beat time at L4" is unwinnable — that negative IS the result.
The lens's honest room is the TIME-FREE semantic channel (dealiased token↔hub co-occurrence), measured
here by its margin over the NAIVE-string baseline under corruption — not by beating time. (M1.)
"""
from __future__ import annotations

from .nexus_baselines import score_all
from .nexus_substrate import labelled_bridges


def roc_auc(scores: list, labels: list) -> float:
    """AUC via the Mann–Whitney U statistic with AVERAGE ranks for ties (so the many-tied time baseline is
    scored fairly). Returns 0.5 when one class is absent (undefined → chance)."""
    pos = sum(labels)
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return 0.5
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank over the tie block
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    rank_sum_pos = sum(ranks[i] for i in range(len(labels)) if labels[i] == 1)
    return round((rank_sum_pos - pos * (pos + 1) / 2.0) / (pos * neg), 4)


def average_precision(scores: list, labels: list) -> float:
    """Tie-aware AP: process equal-score groups together, crediting each positive with the precision at the
    group's end (a standard convention; deterministic under heavy ties)."""
    pos = sum(labels)
    if pos == 0:
        return 0.0
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    tp = seen = ap = 0
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        group_pos = sum(labels[order[k]] for k in range(i, j + 1))
        tp += group_pos
        seen += (j - i + 1)
        if group_pos:
            ap += group_pos * (tp / seen)  # precision at group end × #positives credited
        i = j + 1
    return round(ap / pos, 4)


def ece(probs: list, labels: list, bins: int = 10) -> float:
    """Expected calibration error over equal-width bins — only meaningful for a CALIBRATED probability
    (the ΔL→p lens); reported for baselines only as a rough diagnostic."""
    if not probs:
        return 0.0
    tot = len(probs)
    err = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(probs) if (lo <= p < hi or (b == bins - 1 and p == 1.0))]
        if not idx:
            continue
        conf = sum(probs[i] for i in idx) / len(idx)
        acc = sum(labels[i] for i in idx) / len(idx)
        err += (len(idx) / tot) * abs(conf - acc)
    return round(err, 4)


def _metrics(scores: list, labels: list) -> dict:
    return {"auc": roc_auc(scores, labels), "ap": average_precision(scores, labels)}


def run_baseline_ladder(source_id: str = "logistics_demo", *, seeds: list[str] | None = None,
                        link: int = 4, dirt: float = 0.0) -> dict:
    """Score every baseline over the labelled bridge set at fixed (link, dirt). The headline is each
    baseline's AUC — the bar a lens must beat (time_coincidence especially)."""
    seeds = seeds or [f"nx-{i}" for i in range(40)]  # >=40: only ~2 positives/package, so pool
    bridges = labelled_bridges(source_id, seeds=seeds, link=link, dirt=dirt)
    labels = [b["y"] for b in bridges]
    scored = score_all(bridges)
    ladder = {name: _metrics(s, labels) for name, s in scored.items()}
    n_real = sum(labels)
    return {
        "source_id": source_id, "link": link, "dirt": dirt, "seeds": len(seeds),
        "n_bridges": len(bridges), "n_real": n_real, "n_coincidence": len(bridges) - n_real,
        "prevalence": round(n_real / len(bridges), 4) if bridges else 0.0,
        "baselines": ladder,
        "bar_to_beat": {"name": "time_coincidence", "auc": ladder.get("time_coincidence", {}).get("auc")},
    }


def discrimination_sweep(source_id: str = "logistics_demo", *, seeds: list[str] | None = None,
                         links: tuple[int, ...] = (1, 2, 3, 4, 5), dirt: float = 0.0) -> dict:
    """Baseline AUC across the link-explicitness knob — shows the string baselines collapsing as the link
    is hidden while time-coincidence persists, i.e. quantifies the interval the lenses must fill."""
    seeds = seeds or [f"nx-{i}" for i in range(40)]  # >=40: only ~2 positives/package, so pool
    rows = []
    for link in links:
        ladder = run_baseline_ladder(source_id, seeds=seeds, link=link, dirt=dirt)
        rows.append({"link": link, "n_bridges": ladder["n_bridges"], "prevalence": ladder["prevalence"],
                     **{name: m["auc"] for name, m in ladder["baselines"].items()}})
    return {"source_id": source_id, "dirt": dirt, "sweep": rows,
            "note": "string baselines should fall toward 0.5 by L4; time_coincidence is the residual bar the lenses must beat."}


def negative_controls(source_id: str = "logistics_demo", *, seeds: list[str] | None = None,
                      link: int = 4, dirt: float = 0.0) -> dict:
    """Sanity: on 'rewire' (real chains broken) every baseline's AUC should fall toward chance; on
    'distractor_only' there are NO real bridges (a correct scorer raises no confident positive)."""
    seeds = seeds or [f"nx-{i}" for i in range(40)]  # >=40: only ~2 positives/package, so pool
    out = {}
    for ctl in ("rewire", "distractor_only"):
        bridges = labelled_bridges(source_id, seeds=seeds, link=link, dirt=dirt, control=ctl)
        labels = [b["y"] for b in bridges]
        scored = score_all(bridges)
        out[ctl] = {"n_bridges": len(bridges), "n_real": sum(labels),
                    "baselines": {name: _metrics(s, labels) for name, s in scored.items()}}
    return {"source_id": source_id, "link": link, "dirt": dirt, "controls": out}
