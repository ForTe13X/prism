"""DP1 discriminability harness — the deterministic proxy for the axiom-gain benchmark.

Three solvers over the OBSERVATION view (never the ground-truth): an ``oracle`` (knows the truth, the
ceiling), a ``naive`` solver (literal exact-key / single-source only), and a ``linked`` solver (a basic
cross-source spatiotemporal + entity join — a deterministic stand-in for what a semantic/axiom layer
would do). On the ``explain_delays`` task this shows the discriminative interval: at low
link-explicitness naive ≈ linked ≈ oracle (trivial join), but as the link is hidden (L4 spatiotemporal,
L5 semantic) naive collapses while linked still recovers — i.e. the task genuinely needs cross-source
reasoning. Dirtiness then degrades ``linked`` (a robustness curve). The LLM-ablation version
(RESEARCH_axiom_gain) swaps naive→naive-RAG and linked→axiom-RAG; this is its deterministic skeleton.

Honest limit: this DETERMINISTIC skeleton only resolves L1 (explicit key) vs L≥2 (non-explicit) — its
``linked`` ORs multiple cues (name/region/port/anomaly-time), and every level L2–L5 leaves at least one
cue, so L2–L5 score the same (~0.8). The finer L2→L5 difficulty gradient (esp. true semantic-only L5)
is what the future LLM/axiom solver is meant to exercise; here it is a stand-in.
"""
from __future__ import annotations


# a solver's delay-attribution tolerance is a DOMAIN PRIOR (a plausible delay SLA window), NOT read
# from the ground-truth — so linked never sees a generation parameter through the observation channel.
_DELAY_TOL = 7


def observation_view(package: dict) -> dict:
    """The stores a solver may see — ONLY observations; ground-truth metadata (``_truth_event``) and the
    truth-side delay window are excluded."""
    sql = package["stores"]["sql"]
    news = [{k: v for k, v in n.items() if not k.startswith("_")} for n in package["stores"]["news"]]
    return {"sql": sql, "timeseries": package["stores"]["timeseries"], "news": news}


def _anomaly_frames(timeseries: dict) -> dict:
    """Detect each warehouse's throughput-dip frame (min well below the series mean)."""
    out = {}
    for wid, series in timeseries["throughput"].items():
        if not series:
            continue
        mean = sum(series) / len(series)
        lo_i = min(range(len(series)), key=lambda i: series[i])
        if series[lo_i] < mean * 0.7:  # a real dip, not normal wiggle
            out[wid] = lo_i
    return out


def oracle_solve(package: dict, task_id: str) -> dict:
    return dict(package["ground_truth"]["answers"].get(task_id, {}))


def naive_solve(obs: dict, task_id: str) -> dict:
    """Literal exact-key / single-source only — no cross-source inference."""
    if task_id != "explain_delays":
        return {}
    delayed = {s["id"]: s for s in obs["sql"]["shipments"] if s.get("status") == "delayed"}
    by_wh: dict[str, list] = {}
    for sid, s in delayed.items():
        by_wh.setdefault(s["warehouse_id"], []).append(sid)
    pred: dict[str, list] = {}
    for n in obs["news"]:
        hits = sorted(sid for sid in delayed if sid in n["body"])  # literal shipment ids
        if not hits:
            for wid, sids in by_wh.items():
                if wid in n["body"]:  # literal warehouse id
                    hits = sorted(sids)
                    break
        if hits:
            pred[n["id"]] = hits
    return pred


def linked_solve(obs: dict, task_id: str) -> dict:
    """Cross-source join: align news ⇄ throughput anomaly ⇄ delayed shipments via region/port/time
    cues (no explicit key needed). Degrades when those cues are corrupted — the robustness signal."""
    if task_id != "explain_delays":
        return {}
    wh = {w["id"]: w for w in obs["sql"]["warehouses"]}
    anomalies = _anomaly_frames(obs["timeseries"])
    tol = 3
    delayed = [s for s in obs["sql"]["shipments"] if s.get("status") == "delayed"]
    pred: dict[str, list] = {}
    for n in obs["news"]:
        best, best_score = None, 0
        for wid, w in wh.items():
            score = 0
            if w["id"] in n["body"] or w["name"] in n["body"]:
                score += 3
            if w["region"] in n["body"]:
                score += 2
            if w["port"] in n["body"]:
                score += 2
            if wid in anomalies and abs(anomalies[wid] - n["frame"]) <= tol:
                score += 2
            if score > best_score:
                best, best_score = wid, score
        if best is None or best_score == 0:
            continue
        hits = sorted(
            s["id"] for s in delayed
            if s["warehouse_id"] == best and abs(s["dispatch_frame"] - n["frame"]) <= _DELAY_TOL
        )
        if hits:
            pred[n["id"]] = hits
    return pred


def _pairs(answer: dict) -> set:
    """Flatten an answer to a set of comparable tuples — shape-aware so dict-valued answers (e.g.
    anomaly_cause's {warehouse: {frame, news}}) compare their VALUES, not just their field names."""
    out: set = set()
    for k, v in answer.items():
        if isinstance(v, dict):
            out.update((k, field, val) for field, val in v.items())
        else:
            out.update((k, item) for item in v)
    return out


def score(pred: dict, truth: dict) -> dict:
    p, t = _pairs(pred), _pairs(truth)
    tp = len(p & t)
    prec = tp / len(p) if p else (1.0 if not t else 0.0)
    rec = tp / len(t) if t else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else (1.0 if not t and not p else 0.0)
    return {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}


def evaluate(package: dict, task_id: str = "explain_delays") -> dict:
    """naive vs linked vs oracle on one package — the with/without-style comparison at fixed knobs."""
    obs = observation_view(package)
    truth = oracle_solve(package, task_id)
    naive = score(naive_solve(obs, task_id), truth)
    linked = score(linked_solve(obs, task_id), truth)
    return {
        "task": task_id, "link_explicitness": package["link_explicitness"], "dirtiness": package["dirtiness"],
        "naive_f1": naive["f1"], "linked_f1": linked["f1"], "oracle_f1": 1.0,
        "gap": round(linked["f1"] - naive["f1"], 3), "naive": naive, "linked": linked,
    }
