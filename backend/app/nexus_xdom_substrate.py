"""Phase-B cross-domain bridge enumeration (METRIC §4 Phase B). A candidate is a pair (A_i, B_j) where BOTH
units show an in-band metric dip (a neutral candidacy prior, mirroring Phase-A's _CAND_TOL). The eval label
(real iff (i,j) is in the coupling table) is derived from ground truth and NEVER placed on the bridge a
scorer sees — bridges carry only OBSERVATIONS (the two series, the two attribute histograms, the two anchor
frames). Negative controls (rewire / distractor-only) relabel or restrict WITHOUT changing observations, so
a correct metric collapses toward chance where the coupling is broken or absent.
"""
from __future__ import annotations

from .data_package_xdom import KNOBS, generate_xdom
from .data_synth import _unit


def _histogram(unit: dict) -> list[float]:
    """The observed attribute distribution: fraction of the unit's records in each category position
    (index-aligned across domains; the category NAMES are domain-specific and never compared)."""
    nc = KNOBS["n_cats"]
    h = [0] * nc
    for r in unit["records"]:
        h[r["cat_index"]] += 1
    n = len(unit["records"]) or 1
    return [c / n for c in h]


def _anchors(domain: dict) -> dict:
    """Each unit INDEX → its in-band anchor frame, iff the band minimum dips below frac*mean (a real dip)."""
    lo, span, frac = KNOBS["band_lo"], KNOBS["band_span"], KNOBS["candidacy_dip_frac"]
    out = {}
    for idx, unit in enumerate(domain["units"]):
        s = domain["series"][unit["id"]]
        mean = sum(s) / len(s)
        win = s[lo:lo + span]
        li = min(range(len(win)), key=lambda i: win[i])
        if win[li] < frac * mean:
            out[idx] = lo + li
    return out


def candidate_bridges_xdom(g: dict, *, coupling: list | None = None) -> tuple[list, dict]:
    """Enumerate (A_i, B_j) over anchor units of each domain. ``coupling`` overrides the truth set (used by
    the controls to relabel). Returns (bridges, ctx)."""
    A, B = g["A"], g["B"]
    anA, anB = _anchors(A), _anchors(B)
    truth = set(g["coupling"] if coupling is None else coupling)
    histA = {idx: _histogram(A["units"][idx]) for idx in anA}
    histB = {idx: _histogram(B["units"][idx]) for idx in anB}
    bridges = []
    for i, fa in sorted(anA.items()):
        for j, fb in sorted(anB.items()):
            bridges.append({
                "a_idx": i, "b_idx": j, "a_id": A["units"][i]["id"], "b_id": B["units"][j]["id"],
                "a_frame": fa, "b_frame": fb,
                "a_series": A["series"][A["units"][i]["id"]], "b_series": B["series"][B["units"][j]["id"]],
                "a_hist": histA[i], "b_hist": histB[j],
                "a_tag_idx": A["units"][i].get("tag_idx", []), "b_tag_idx": B["units"][j].get("tag_idx", []),
                "y": 1 if (i, j) in truth else 0,
                "label": "real" if (i, j) in truth else "coincidence",
            })
    return bridges, {"anA": anA, "anB": anB, "n_anchor_a": len(anA), "n_anchor_b": len(anB)}


def rewired_coupling(g: dict) -> list:
    """NEGATIVE CONTROL — deterministically re-point each true pair's B endpoint to a DIFFERENT coupled B
    unit, breaking the real chains while leaving every observation byte-identical."""
    pairs = sorted(g["coupling"])
    js = [j for _i, j in pairs]
    n = len(js)
    out = []
    for k, (i, _j) in enumerate(pairs):
        if n < 2:
            out.append((i, _j))
            continue
        shifted = js[(k + 1 + int(_unit(g["seed"], "rewire", k) * (n - 1))) % n]
        if shifted == _j:
            shifted = js[(k + 1) % n]
        out.append((i, shifted))
    return out


def labelled_bridges_xdom(seeds: list[str], *, control: str | None = None, cal: dict | None = None) -> list:
    """Pool candidate bridges over seeds. ``control`` ∈ {None, 'rewire', 'distractor_only'}:
    'rewire' breaks the coupling (channels should fall to chance); 'distractor_only' keeps only bridges whose
    BOTH endpoints are non-coupled anchors → a set with NO real bridges (any confident positive is false).
    ``cal`` (Track 1, §4b): optional real-data-calibrated marginals; None ⇒ frozen substrate."""
    out = []
    for sd in seeds:
        g = generate_xdom(sd, cal)
        if control == "rewire":
            bridges, _ = candidate_bridges_xdom(g, coupling=rewired_coupling(g))
        elif control == "distractor_only":
            coupled_a = {i for i, _j in g["coupling"]}
            coupled_b = {j for _i, j in g["coupling"]}
            bridges, _ = candidate_bridges_xdom(g)
            bridges = [b for b in bridges if b["a_idx"] not in coupled_a and b["b_idx"] not in coupled_b]
        else:
            bridges, _ = candidate_bridges_xdom(g)
        for b in bridges:
            b["seed"] = sd
        out.extend(bridges)
    return out
