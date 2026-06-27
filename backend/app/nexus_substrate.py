"""Nexus substrate adapter (METRIC_nexus_reality Phase A) — turn a data package into LABELLED candidate
bridges, the unit the nexus metric scores.

Phase A runs on the EXISTING single-domain multi-source substrate (data_package.py), so honestly this is
a *cross-SOURCE link* prototype, NOT yet a cross-DOMAIN nexus (Phase B, deferred). A candidate BRIDGE is a
(news, hub) pair whose hub shows a metric anomaly within a generous temporal tolerance of the news — i.e.
exactly the pairs the lethal TIME-COINCIDENCE baseline would also surface, so the bar is honest. The eval
LABEL (real vs coincidence) comes from the ground-truth (_truth_event + events) and is NEVER exposed to a
scorer: bridges carry only OBSERVATION features (news body, hub row, the observed dip, the affected
records). Three deterministic negative controls (distractor-only, random rewire, copy-domain) let the eval
check that a correct metric collapses toward chance where it should.

Deterministic: anomalies via data_package_eval._anomaly_frames; rewire via Prism's own _unit hash (no
random/clock).
"""
from __future__ import annotations

from .data_package import _DEFAULT_ROLES, generate
from .data_package_eval import _anomaly_frames, observation_view
from .data_synth import _unit

# generous temporal window for *candidacy* (a domain prior, not read from truth): a (news, hub-anomaly)
# pair this close in observed frames is worth scoring. Wide enough to admit hard temporal coincidences.
_CAND_TOL = 8


def _tokens(text: str) -> set:
    """Cheap deterministic tokenization for the string baselines: CJK char shingles + ASCII words."""
    import re

    ascii_words = set(re.findall(r"[A-Za-z0-9]+", text or ""))
    cjk = re.findall(r"[㐀-鿿]", text or "")
    bigrams = {cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)}
    return ascii_words | set(cjk) | bigrams


def bridge_context(package: dict) -> dict:
    """Observation-only context the scorers may read: hub rows by id, the observed anomaly frame per hub,
    delayed (affected) records grouped by hub, news by id, and the metric-dip depth per hub."""
    r = package.get("roles", _DEFAULT_ROLES)
    obs = observation_view(package)
    hubs = {h["id"]: h for h in obs["sql"][r["hub_store"]]}
    anomalies = _anomaly_frames(obs["timeseries"], r.get("metric_store"))
    rst, affected, rhf, rfr = r["record_status"], r["affected_status"], r["record_hub_fk"], r["record_frame"]
    delayed_by_hub: dict[str, list] = {}
    for s in obs["sql"][r["record_store"]]:
        if s.get(rst) == affected:
            delayed_by_hub.setdefault(s[rhf], []).append(s)
    series_map = obs["timeseries"].get(r.get("metric_store")) or next(
        (v for k, v in obs["timeseries"].items() if k != "frames" and isinstance(v, dict)), {})
    depth = {}
    for hid, series in series_map.items():
        if series:
            mean = sum(series) / len(series)
            depth[hid] = round((mean - min(series)) / mean, 4) if mean else 0.0
    return {"roles": r, "hubs": hubs, "anomalies": anomalies, "delayed_by_hub": delayed_by_hub,
            "news_by_id": {n["id"]: n for n in obs["news"]}, "depth": depth,
            "record_frame": rfr, "record_hub_fk": rhf, "all_delayed": [s for v in delayed_by_hub.values() for s in v]}


def _truth_hub_of_news(package: dict) -> dict:
    """EVAL-ONLY: map each REAL news id → the hub its truth event hit (None for distractors). Built from
    _truth_event + events; never handed to a scorer."""
    r = package.get("roles", _DEFAULT_ROLES)
    rhf = r["record_hub_fk"]
    ev_hub = {e["id"]: e[rhf] for e in package["ground_truth"]["events"]}
    out = {}
    for n in package["stores"]["news"]:
        te = n.get("_truth_event")
        out[n["id"]] = ev_hub.get(te) if te else None
    return out


def candidate_bridges(package: dict, tol: int = _CAND_TOL, *, hub_of_news: dict | None = None) -> tuple[list, dict]:
    """Enumerate (news, hub) candidates: every hub with an observed anomaly within ``tol`` observed frames
    of a news. Each bridge carries observation features + the eval label. ``hub_of_news`` overrides the
    real→hub map (used by the negative controls to relabel without changing observations)."""
    ctx = bridge_context(package)
    truth = hub_of_news if hub_of_news is not None else _truth_hub_of_news(package)
    bridges = []
    for nid, n in ctx["news_by_id"].items():
        for hid, afr in ctx["anomalies"].items():
            d = abs(n["frame"] - afr)
            if d > tol:
                continue
            hub = ctx["hubs"].get(hid, {})
            bridges.append({
                "news_id": nid, "hub_id": hid, "news_frame": n["frame"], "anomaly_frame": afr, "dframe": d,
                "label": "real" if truth.get(nid) == hid else "coincidence",
                "y": 1 if truth.get(nid) == hid else 0,
                "news_body": n.get("body", ""), "news_kind": n.get("kind", ""),
                "hub": {k: hub.get(k, "") for k in ("id", "name", "region", "port")},
                "n_delayed_at_hub": len(ctx["delayed_by_hub"].get(hid, [])),
                "anomaly_depth": ctx["depth"].get(hid, 0.0),
            })
    return bridges, ctx


def rewired_hub_of_news(package: dict, seed_tag: str = "rewire") -> dict:
    """NEGATIVE CONTROL — deterministically reassign each real news to a DIFFERENT random hub, so its
    pre-embedded chain is structurally broken. A correct metric's AUC should fall toward chance here."""
    r = package.get("roles", _DEFAULT_ROLES)
    hub_ids = [h["id"] for h in package["stores"]["sql"][r["hub_store"]]]
    real = _truth_hub_of_news(package)
    out = {}
    for nid, hid in real.items():
        if hid is None or len(hub_ids) < 2:
            out[nid] = hid
            continue
        others = [h for h in hub_ids if h != hid]
        out[nid] = others[int(_unit(package["seed"], seed_tag, nid) * len(others)) % len(others)]
    return out


def labelled_bridges(source_id: str, *, seeds: list[str], link: int = 4, dirt: float = 0.0,
                     control: str | None = None) -> list:
    """The eval set: candidate bridges over many seeds at fixed (link, dirt). ``control`` ∈ {None,
    'rewire', 'distractor_only'} selects a negative control. 'distractor_only' keeps only coincidence
    bridges from distractor news (truth_event=None) — a set with NO real bridges, where any high score is
    a false positive."""
    out = []
    for sd in seeds:
        pkg = generate(source_id, dirtiness=dirt, link_explicitness=link, seed=sd)
        if pkg is None:
            continue
        if control == "rewire":
            bridges, _ = candidate_bridges(pkg, hub_of_news=rewired_hub_of_news(pkg))
        elif control == "distractor_only":
            hub_of = _truth_hub_of_news(pkg)
            distractor_news = {nid for nid, h in hub_of.items() if h is None}
            bridges, _ = candidate_bridges(pkg)
            bridges = [b for b in bridges if b["news_id"] in distractor_news]
        else:
            bridges, _ = candidate_bridges(pkg)
        for b in bridges:
            b["seed"] = sd
        out.extend(bridges)
    return out
