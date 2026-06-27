"""Phase-B §6c PRE-REGISTRATION GATE (channel-blind) — METRIC §5/§6c.

Before any channel scorer exists, prove the substrate's difficulty is well-posed using ONLY lens-independent
quantities, so the later channels cannot have been tuned to the task:
  * ORACLE (sees the latents) must RECOVER the coupling — AUC >= 0.95 (the truth is there to be found);
  * the NAIVE baselines must be ~chance — time-coincidence (|Δanchor-frame|), depth-match, and cross-domain
    string-Jaccard all in [0.40, 0.60] (a null baseline lands either side of 0.5 by noise; timing is
    necessary-but-insufficient; strings can't cross domains).
A pass means: an informed solver wins, dumb proxies don't, and any later channel win is a real discovery —
not a baseline in disguise. Pooled over >=60 seeds (only ~10 positives/package). Deterministic, offline.
"""
from __future__ import annotations

import math

from .data_package_xdom import KNOBS, generate_xdom
from .nexus_eval import roc_auc
from .nexus_substrate import _tokens
from .nexus_xdom_substrate import candidate_bridges_xdom


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    va = math.sqrt(sum((x - ma) ** 2 for x in a)) or 1.0
    vb = math.sqrt(sum((x - mb) ** 2 for x in b)) or 1.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (va * vb)


def _latent_lookup(g: dict) -> tuple[dict, dict]:
    """unit INDEX → its dip latent {prof, theta}, per domain. The coupled incident takes priority over a
    distractor on the same unit (the coupled dip is the one the truth pairing is about)."""
    lat = {"A": {}, "B": {}}
    for dd in g["_latents"]["distractor"]:
        lat[dd["side"]].setdefault(dd["unit"], {"prof": dd["prof"], "theta": dd["theta"]})
    for inc in g["_latents"]["coupled"]:
        lat["A"][inc["i"]] = {"prof": inc["prof"], "theta": inc["theta"]}
        lat["B"][inc["j"]] = {"prof": inc["prof"], "theta": inc["theta"]}
    return lat["A"], lat["B"]


def _depth(series: list[float]) -> float:
    return (sum(series) / len(series)) - min(series)


def _unit_string_tokens(domain: dict, idx: int) -> set:
    u = domain["units"][idx]
    toks = set(_tokens(u["id"]))
    for r in u["records"]:
        toks |= _tokens(r["cat"])
    return toks


def _collect(seeds: list[str]) -> tuple[dict, list]:
    pools = {"oracle": [], "time": [], "depth": [], "string": []}
    labels = []
    for sd in seeds:
        g = generate_xdom(sd)
        latA, latB = _latent_lookup(g)
        bridges, _ = candidate_bridges_xdom(g)
        for b in bridges:
            labels.append(b["y"])
            pools["time"].append(-abs(b["a_frame"] - b["b_frame"]))
            pools["depth"].append(-abs(_depth(b["a_series"]) - _depth(b["b_series"])))
            ta, tb = _unit_string_tokens(g["A"], b["a_idx"]), _unit_string_tokens(g["B"], b["b_idx"])
            pools["string"].append(len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0)
            la, lb = latA.get(b["a_idx"]), latB.get(b["b_idx"])
            if la and lb:
                pools["oracle"].append(_pearson(la["prof"], lb["prof"])
                                       - sum((x - y) ** 2 for x, y in zip(la["theta"], lb["theta"])))
            else:
                pools["oracle"].append(-99.0)
    return pools, labels


def run_gate(seeds: list[str] | None = None) -> dict:
    seeds = seeds or [f"xd-{i}" for i in range(60)]
    pools, labels = _collect(seeds)
    n, npos = len(labels), sum(labels)
    auc = {k: roc_auc(v, labels) for k, v in pools.items()}
    oracle_ok = auc["oracle"] >= 0.95
    baselines_null = all(0.40 <= auc[k] <= 0.60 for k in ("time", "depth", "string"))
    return {
        "seeds": len(seeds), "n_candidates": n, "n_positives": npos,
        "prevalence": round(npos / n, 4) if n else 0.0,
        "oracle_auc": auc["oracle"], "time_auc": auc["time"], "depth_auc": auc["depth"],
        "string_auc": auc["string"],
        "gate_pass": bool(oracle_ok and baselines_null),
        "checks": {"oracle_recoverable(>=0.95)": oracle_ok,
                   "time_chance(0.40-0.60)": 0.40 <= auc["time"] <= 0.60,
                   "depth_chance": 0.40 <= auc["depth"] <= 0.60,
                   "string_chance(cross-domain)": 0.40 <= auc["string"] <= 0.60},
        "note": ("Channel-blind §6c gate: an oracle (sees latents) recovers the coupling while time/depth/"
                 "string are ~chance ⇒ the difficulty is real and pre-registered. The shape + fingerprint "
                 "CHANNELS (Phase-B.1) are then a genuine test, not a baseline relabelled."),
    }
