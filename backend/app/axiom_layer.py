"""Axiom / canonical layer (clean-room, deterministic) — the thing the axiom-gain ablation measures.

For the explain_delays task it builds two LLM contexts over the OBSERVATION view:
  * naive_context — the raw multi-store facts (aliased/dirty news, delayed-shipment rows, raw throughput
    anomaly hints): everything is present but UNRESOLVED, so the model must canonicalize + cross-source
    join itself;
  * axiom_context — a compact, CANONICAL-resolved + pre-joined view: a resolved entity table (alias→
    canonical, via the layer's own dictionary, NOT the per-package corruption_map) and the aligned
    cross-source facts (news ⇄ warehouse ⇄ anomaly frame ⇄ delayed shipments).

The hypothesis (RESEARCH_axiom_gain H1/H2): axiom-RAG reaches equal-or-better quality at FEWER input
tokens, and the gain is larger for a weaker model / dirtier data. No clock, no random; reuses the
deterministic cross-source join from data_package_eval. Clean-room: Prism's own code.
"""
from __future__ import annotations

from .data_package import _DEFAULT_ROLES
from .data_package_eval import _DELAY_TOL, _anomaly_frames

# the layer's OWN canonical alias dictionary (a resolver maintains aliases) — NOT the package's
# corruption_map. Folds the variant forms the dirtiness layer can introduce back to canonical regions.
_FOLD = str.maketrans({"華": "华", "東": "东", "區": "区"})
_ABBR = {"HD": "华东", "HN": "华南", "HB": "华北"}


def canon(text: str) -> str:
    """Normalize a text fragment toward canonical tokens (variant folding + abbreviation expansion)."""
    t = text.translate(_FOLD).replace("区", "")
    for ab, full in _ABBR.items():
        t = t.replace(ab, full)
    return t


def _resolve(obs: dict, canon_fn=canon) -> list[dict]:
    """Canonical cross-source resolution, ANCHORED ON THE REAL ANOMALY (the observed throughput dip).

    Score every (warehouse-anomaly, news) pair by canonical entity cue then frame proximity, then assign
    MUTUALLY EXCLUSIVELY via greedy max-weight matching — each warehouse-anomaly and each news used at
    most once. Exclusivity stops one news being attributed to two warehouses when two anomalies coincide
    in time (honest about the residual L4 ambiguity); anchoring on the observed anomaly frame (not the
    possibly-time-dirtied news frame) keeps shipment attribution dirt-robust.

    ``canon_fn`` is the canonicalizer (default = the algorithmic ``canon``); a LEARNED resolver injects
    its own mined dictionary here, so the same join measures both layers (see axiom_learn / amortization)."""
    # read stores/fields by ROLE so the join is domain-generic (defaults reproduce logistics verbatim, so
    # the logistics axiom_context — and its frozen fixtures — stay byte-identical).
    r = obs.get("roles", _DEFAULT_ROLES)
    hub_store, rec_store = r["hub_store"], r["record_store"]
    rst, affected, rhf, rfr = r["record_status"], r["affected_status"], r["record_hub_fk"], r["record_frame"]
    wh = {w["id"]: w for w in obs["sql"][hub_store]}
    frame_of = {n["id"]: n["frame"] for n in obs["news"]}
    delayed = [s for s in obs["sql"][rec_store] if s.get(rst) == affected]

    # sort key = (dist, -score, …): TIME-PRIMARY (the news on the dip frame is the cause), entity cue as
    # the tiebreak — so a distractor whose region merely happens to match can't out-vote the dip-frame news.
    scored: list[tuple] = []  # (dist, -score, wid, news_id, anomaly_frame) → sort ascending = best first
    for wid, fa in _anomaly_frames(obs["timeseries"], r.get("metric_store")).items():
        w = wh.get(wid, {})
        for n in obs["news"]:
            dist = abs(n["frame"] - fa)
            if dist > 4:
                continue
            b = canon_fn(n["body"])
            s = 3 if (w.get("id", "") in n["body"] or canon_fn(w.get("name", "")) in b) else 0
            s += 2 if canon_fn(w.get("region", "")) in b else 0
            s += 2 if w.get("port", "") in n["body"] else 0
            scored.append((dist, -s, wid, n["id"], fa))
    scored.sort()

    used_wh: set[str] = set()
    used_news: set[str] = set()
    facts = []
    for _dist, _negs, wid, nid, fa in scored:
        if wid in used_wh or nid in used_news:
            continue
        used_wh.add(wid)
        used_news.add(nid)
        hits = sorted(s["id"] for s in delayed
                      if s[rhf] == wid and abs(s[rfr] - fa) <= _DELAY_TOL)
        if hits:
            facts.append({"news_id": nid, "warehouse_id": wid, "frame": frame_of[nid],
                          "anomaly_frame": fa, "shipment_ids": hits})
    return facts


def task_question() -> str:
    return ("对每条提到港口停摆/封港/中断的新闻,列出它所导致延误的运单 id。"
            "只用给定上下文,不要编造。输出 JSON:{\"answer\":[{\"news_id\":\"...\",\"shipment_ids\":[\"...\"]}]}。")


def naive_context(obs: dict) -> str:
    """Raw multi-store facts — present but unresolved; the model must canonicalize + join itself. Stores
    are read BY ROLE (defaults reproduce logistics ⇒ byte-identical context for the frozen fixtures); the
    Chinese wording stays logistics-flavoured (this builder feeds the logistics LLM run only)."""
    r = obs.get("roles", _DEFAULT_ROLES)
    rst, affected, rhf, rfr = r["record_status"], r["affected_status"], r["record_hub_fk"], r["record_frame"]
    lines = ["[新闻]"]
    for n in obs["news"]:
        lines.append(f"- {n['id']}(第{n['frame']}帧):{n['body']}")
    lines.append("[运单表 · 仅延误]")
    for s in obs["sql"][r["record_store"]]:
        if s.get(rst) == affected:
            lines.append(f"- {s['id']} 仓库={s[rhf]} 发运帧={s[rfr]} 状态={affected}")
    lines.append("[仓库表]")
    for w in obs["sql"][r["hub_store"]]:
        lines.append(f"- {w['id']} 名称={w['name']} 区域={w['region']} 港口={w['port']}")
    lines.append("[吞吐量异常(原始信号)]")
    for wid, fr in _anomaly_frames(obs["timeseries"], r.get("metric_store")).items():
        lines.append(f"- {wid} 在第{fr}帧吞吐量骤降")
    return "\n".join(lines)


def axiom_context(obs: dict, canon_fn=canon) -> str:
    """Canonical-resolved + pre-joined facts — compact; the model just reads the answer off."""
    facts = _resolve(obs, canon_fn)
    hub_store = obs.get("roles", _DEFAULT_ROLES)["hub_store"]
    lines = ["[已解析跨源事实 · 新闻→仓库→异常→延误运单]"]
    for f in facts:
        w = next((w for w in obs["sql"][hub_store] if w["id"] == f["warehouse_id"]), {})
        lines.append(
            f"- {f['news_id']}(第{f['frame']}帧)→ {f['warehouse_id']}({w.get('name','')},{w.get('region','')}/"
            f"{w.get('port','')});吞吐量异常@{f['anomaly_frame']};延误运单={','.join(f['shipment_ids'])}"
        )
    if len(lines) == 1:
        lines.append("- (无可解析的跨源关联)")
    return "\n".join(lines)
