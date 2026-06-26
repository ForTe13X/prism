"""Spec-driven heterogeneous data-package generator (DP1) — deterministic, clean-room.

Per docs/DESIGN_data_package.md: emit a cross-source dataset (SQL shipments/carriers/warehouses +
per-warehouse throughput timeseries + port/weather news) whose link
``news event → throughput anomaly → delayed shipments`` is PRE-EMBEDDED as ground-truth. The truth is
built FIRST; every store is then materialized to be consistent with it. Two knobs, BOTH preserving the
truth (they only touch OBSERVATIONS):
  * ``link_explicitness`` 1–5 — how conspicuously the news exposes which warehouse/shipments it hits
    (1 = literal ids, 5 = pure semantic), so a benchmark can sit in the discriminative interval;
  * ``dirtiness`` 0–1 — identity/unit/time/missing/numeric/encoding corruption of observations, with a
    ``corruption_map`` recording variant→canonical so a scorer can still recover the truth.

Deterministic: reuses Prism's own ``_unit``/``_wiggle`` (no clock, no random) → byte-reproducible.
Clean-room: only Prism's own code; no SPI IP. HONEST SCOPE: real-calibration (§4b), the agentic parser
(§5), PDF/NoSQL modalities (§3) and the LLM-ablation benchmark (RESEARCH_axiom_gain) are NOT here — this
is the deterministic substrate they build on. Distributions are hand-set synthetic, not calibrated to
real data.
"""
from __future__ import annotations

import json
from pathlib import Path

from .data_synth import _unit, _wiggle

SOURCES_DIR = Path(__file__).resolve().parent.parent / "data_sources"

_CARRIERS = ["远洋速运", "华联物流", "中际货运", "顺捷供应链", "通达运输", "鹏程冷链"]
_KINDS = ["台风封港", "道路中断"]
# deterministic name aliases used by the dirtiness layer (variant → canonical handled via map)
_ALIAS = {"华东": ["华東", "华东区", "HD"], "华南": ["华南区", "HN", "华南"], "华北": ["华北区", "HB"]}


def _u(seed: str, *parts: object) -> float:
    return _unit(seed, *parts)


def _ri(seed: str, lo: int, hi: int, *parts: object) -> int:
    if hi <= lo:
        return lo
    return lo + int(_u(seed, *parts) * (hi - lo + 1)) % (hi - lo + 1)


def load_source(source_id: str) -> dict | None:
    if not source_id or not source_id.replace("_", "").isalnum():
        return None
    path = SOURCES_DIR / f"{source_id}.json"
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if doc.get("id") == source_id else None


def list_sources() -> list[dict]:
    out = []
    if SOURCES_DIR.exists():
        for p in sorted(SOURCES_DIR.glob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if d.get("id"):
                out.append({"id": d["id"], "title": d.get("title", d["id"]), "scenario": d.get("scenario", "")})
    return out


def _build_truth(seed: str, p: dict, regions: list, ports: list) -> tuple[list, list, list, dict]:
    """Build warehouses/carriers/shipments and the ground-truth events. Truth is authored here; the
    observation stores are made consistent with it afterwards."""
    nw, nc, ns = int(p["warehouses"]), int(p["carriers"]), int(p["shipments"])
    frames, n_gt, win = int(p["frames"]), int(p["ground_truth_events"]), int(p["delay_window"])

    warehouses = [
        {"id": f"WH-{i + 1:03d}", "region": regions[i % len(regions)], "port": ports[i % len(ports)],
         "name": f"{regions[i % len(regions)]}中心仓"}
        for i in range(nw)
    ]
    carriers = [{"id": f"CR-{i + 1:03d}", "name": _CARRIERS[i % len(_CARRIERS)]} for i in range(nc)]
    shipments = []
    for j in range(ns):
        wh = warehouses[_ri(seed, 0, nw - 1, "shipwh", j)]
        cr = carriers[_ri(seed, 0, nc - 1, "shipcr", j)]
        shipments.append({
            "id": f"SHP-{j + 1:04d}", "warehouse_id": wh["id"], "carrier_id": cr["id"],
            "dispatch_frame": _ri(seed, 4, frames - 4, "shipfr", j),
            "weight_kg": round(50 + 950 * _u(seed, "shipwt", j), 1),
            "status": "in_transit", "unit": "kg",
        })

    # ground-truth events: each on a DISTINCT warehouse (capped at nw), each carves a throughput
    # anomaly + delays its shipments. Keeping warehouses distinct is the keystone — one event per
    # warehouse means the warehouse-keyed anomaly/answer maps below never collapse two truths into one.
    events = []
    used_idx: set[int] = set()
    lo_b = max(2, min(14, frames // 4))            # anchor band, derived from frames (not hardcoded)
    hi_b = max(lo_b + 1, frames - 6)
    for e in range(min(n_gt, nw)):
        # pick a free (unused) warehouse via a real search from a hashed start — a modulo fallback
        # could silently re-pick an already-used one, producing duplicate-warehouse events.
        start = _ri(seed, 0, nw - 1, "evtwh", e)
        idx = next(((start + k) % nw for k in range(nw) if (start + k) % nw not in used_idx), None)
        if idx is None:
            break
        used_idx.add(idx)
        wh = warehouses[idx]
        # anchor the event frame to a real shipment of this warehouse so it actually delays cargo
        # (a disruption with no affected cargo is a degenerate ground-truth row)
        band = [s for s in shipments if s["warehouse_id"] == wh["id"] and lo_b <= s["dispatch_frame"] <= hi_b]
        if band:
            f_e = band[_ri(seed, 0, len(band) - 1, "evtpivot", e)]["dispatch_frame"]
        else:
            f_e = _ri(seed, lo_b, hi_b, "evtfr", e)
        f_e = max(2, min(frames - 3, f_e))          # keep the anomaly frame inside the series
        kind = _KINDS[e % len(_KINDS)]
        hit = sorted(
            s["id"] for s in shipments
            if s["warehouse_id"] == wh["id"] and abs(s["dispatch_frame"] - f_e) <= win
        )
        for s in shipments:
            if s["id"] in hit:
                s["status"] = "delayed"
        events.append({"id": f"EVT-{e + 1}", "warehouse_id": wh["id"], "region": wh["region"],
                       "port": wh["port"], "frame": f_e, "kind": kind, "shipment_ids": hit})
    # the rest settle to delivered/on-time (deterministic, harmless filler)
    for s in shipments:
        if s["status"] == "in_transit":
            s["status"] = "on_time" if _u(seed, "settle", s["id"]) > 0.3 else "in_transit"
    return warehouses, carriers, shipments, {"events": events, "frames": frames, "window": win}


def _throughput(seed: str, warehouses: list, truth: dict) -> dict:
    """Per-warehouse throughput series; ground-truth events carve a dip (the anomaly) around their frame."""
    frames = truth["frames"]
    anomaly_frame = {ev["warehouse_id"]: ev["frame"] for ev in truth["events"]}
    out = {}
    for w in warehouses:
        lo, hi = 200.0, 900.0
        base = lo + (hi - lo) * (0.45 + 0.25 * _u(seed, "twbase", w["id"]))
        amp = (hi - lo) * 0.12
        series = []
        af = anomaly_frame.get(w["id"])
        for t in range(frames):
            v = base + amp * _wiggle(t, seed, "tw", w["id"])
            if af is not None and af - 1 <= t <= af + 2:  # the injected anomaly dip
                v -= (hi - lo) * (0.45 - 0.1 * abs(t - af))
            series.append(round(max(0.0, v), 1))
        out[w["id"]] = series
    return out


def _news(seed: str, p: dict, warehouses: list, truth: dict, link: int) -> list:
    """News feed: ground-truth events become news items whose link to the warehouse is exposed at the
    requested explicitness; the rest are distractors. The clean truth is unchanged — only wording varies."""
    frames = truth["frames"]
    by_wh = {w["id"]: w for w in warehouses}
    news = []
    for ev in truth["events"]:
        w = by_wh[ev["warehouse_id"]]
        f = ev["frame"]
        if link <= 1:  # L1: literal ids — trivial join
            body = f"{ev['kind']}影响 {w['id']}({w['name']});受影响运单:{','.join(ev['shipment_ids'])}。"
        elif link == 2:  # L2: fuzzy warehouse name — needs entity resolution
            body = f"{ev['kind']}波及『{w['region']}中心仓』一带,多批货受阻。"
        elif link == 3:  # L3: region + approx time — attribute overlap
            body = f"{ev['kind']}袭{w['region']},约第 {f} 帧前后港区作业受限。"
        elif link == 4:  # L4: time + generic place — spatiotemporal co-occurrence, no key
            body = f"第 {f} 帧前后,某港口因{ev['kind']}临时停摆,吞吐骤降。"
        else:  # L5: port name surfaced in prose (no id/key). NOTE: the deterministic linked solver
               # recovers this by literal containment as a STAND-IN — genuine semantic-only inference
               # (and the true L4→L5 difficulty gap) is the future LLM/axiom layer's job, not this skeleton's.
            body = f"{ev['kind']}逼近{w['port']}所在沿海,航运预计中断数日。"
        news.append({"id": f"NEWS-{len(news) + 1:03d}", "frame": f, "kind": ev["kind"],
                     "headline": f"{ev['kind']}快讯", "body": body, "_truth_event": ev["id"]})
    # distractors: unrelated events at other frames/regions (no ground-truth effect)
    nd = max(0, int(p["news_events"]) - len(news))
    for k in range(nd):
        reg = warehouses[_ri(seed, 0, len(warehouses) - 1, "ndreg", k)]["region"]
        kind = _KINDS[_ri(seed, 0, len(_KINDS) - 1, "ndkind", k)]
        f = _ri(seed, 2, frames - 2, "ndfr", k)
        news.append({"id": f"NEWS-{len(news) + 1:03d}", "frame": f, "kind": kind,
                     "headline": f"{reg}{kind}提示", "body": f"{reg}近日{kind},暂未见明显影响。", "_truth_event": None})
    news.sort(key=lambda n: n["frame"])
    return news


def _apply_dirtiness(seed: str, d: float, warehouses: list, shipments: list, throughput: dict, news: list) -> dict:
    """Corrupt OBSERVATIONS in place at intensity ``d`` (0..1); record variant→canonical so a scorer can
    still recover the truth. The ground-truth (event answers) is never touched here."""
    cmap: dict = {"aliases": {}, "weight_lb_ids": [], "status_nulled_ids": [], "news_time_offset": {}, "garbled_news": []}
    if d <= 0:
        return cmap

    # identity: alias region tokens inside news bodies (entity-resolution pressure)
    for n in news:
        for region, variants in _ALIAS.items():
            if region in n["body"] and _u(seed, "dirtyalias", n["id"]) < d:
                variant = variants[_ri(seed, 0, len(variants) - 1, "dav", n["id"])]
                n["body"] = n["body"].replace(region, variant)
                cmap["aliases"][variant] = region
    # unit drift: some shipment weights stored in lb (schema/unit dirtiness)
    for s in shipments:
        if _u(seed, "dirtylb", s["id"]) < d * 0.5:
            s["weight_kg"] = round(s["weight_kg"] * 2.20462, 1)
            s["unit"] = "lb"
            cmap["weight_lb_ids"].append(s["id"])
    # missing: null some statuses (hurts a solver that reads status='delayed')
    for s in shipments:
        if _u(seed, "dirtynull", s["id"]) < d * 0.3:
            s["status"] = None
            cmap["status_nulled_ids"].append(s["id"])
    # time: shift some news timestamps ±1..2 frames (hurts spatiotemporal alignment)
    for n in news:
        if _u(seed, "dirtytime", n["id"]) < d * 0.4:
            off = (1 + _ri(seed, 0, 1, "dto", n["id"])) * (1 if _u(seed, "dts", n["id"]) > 0.5 else -1)
            n["frame"] = max(0, n["frame"] + off)
            cmap["news_time_offset"][n["id"]] = off
    # numeric: freeze a couple throughput points (sensor glitch)
    for wid, series in throughput.items():
        for t in range(1, len(series)):
            if _u(seed, "dirtyfreeze", wid, t) < d * 0.05:
                series[t] = series[t - 1]
    # encoding: garble a fraction of news bodies (GBK↔UTF mojibake stand-in)
    for n in news:
        if _u(seed, "dirtygarble", n["id"]) < d * 0.25:
            n["body"] = n["body"].encode("utf-8", "replace").decode("latin-1", "replace")
            cmap["garbled_news"].append(n["id"])
    return cmap


def generate(source_id: str, *, dirtiness: float = 0.0, link_explicitness: int = 4, seed: str | None = None) -> dict | None:
    src = load_source(source_id)
    if src is None:
        return None
    d = max(0.0, min(1.0, float(dirtiness)))
    link = max(1, min(5, int(link_explicitness)))
    sd = str(seed) if seed else str(src.get("seed", source_id))
    p = src["params"]
    regions, ports = src.get("regions", ["A", "B", "C"]), src.get("ports", ["P1", "P2", "P3"])

    warehouses, carriers, shipments, truth = _build_truth(sd, p, regions, ports)
    throughput = _throughput(sd, warehouses, truth)
    news = _news(sd, p, warehouses, truth, link)
    corruption_map = _apply_dirtiness(sd, d, warehouses, shipments, throughput, news)

    # task answers are keyed by OBSERVATION-visible ids (news id / warehouse id) so a solver that only
    # sees the stores can be scored against them — the ground-truth event ids stay internal.
    news_of_event = {n["_truth_event"]: n["id"] for n in news if n.get("_truth_event")}
    answers = {
        "explain_delays": {news_of_event[ev["id"]]: ev["shipment_ids"]
                           for ev in truth["events"] if ev["id"] in news_of_event},
        "anomaly_cause": {ev["warehouse_id"]: {"frame": ev["frame"], "news": news_of_event.get(ev["id"])}
                          for ev in truth["events"]},
    }
    return {
        "source_id": source_id, "seed": sd, "dirtiness": d, "link_explicitness": link,
        "stores": {
            "sql": {"warehouses": warehouses, "carriers": carriers, "shipments": shipments},
            "timeseries": {"throughput": throughput, "frames": truth["frames"]},
            "news": news,
        },
        "ground_truth": {"events": truth["events"], "answers": answers, "window": truth["window"]},
        "corruption_map": corruption_map,
        "tasks": src.get("tasks", []),
        "manifest": {
            "source_id": source_id, "title": src.get("title", source_id), "seed": sd,
            "dirtiness": d, "link_explicitness": link,
            "counts": {"warehouses": len(warehouses), "carriers": len(carriers), "shipments": len(shipments),
                       "news": len(news), "frames": truth["frames"], "ground_truth_events": len(truth["events"])},
            "scope": src.get("notes", {}).get("scope", ""), "honesty": src.get("notes", {}).get("honesty", ""),
        },
    }


def to_sqlite(package: dict, path: str) -> str:
    """Materialize the SQL store as a real (queryable) SQLite db — the genuinely-relational modality."""
    import sqlite3

    sql = package["stores"]["sql"]
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        cur.execute("CREATE TABLE warehouse (id TEXT PRIMARY KEY, region TEXT, port TEXT, name TEXT)")
        cur.execute("CREATE TABLE carrier (id TEXT PRIMARY KEY, name TEXT)")
        cur.execute("CREATE TABLE shipment (id TEXT PRIMARY KEY, warehouse_id TEXT, carrier_id TEXT, "
                    "dispatch_frame INT, weight REAL, unit TEXT, status TEXT)")
        cur.executemany("INSERT INTO warehouse VALUES (?,?,?,?)",
                        [(w["id"], w["region"], w["port"], w["name"]) for w in sql["warehouses"]])
        cur.executemany("INSERT INTO carrier VALUES (?,?)", [(c["id"], c["name"]) for c in sql["carriers"]])
        cur.executemany("INSERT INTO shipment VALUES (?,?,?,?,?,?,?)",
                        [(s["id"], s["warehouse_id"], s["carrier_id"], s["dispatch_frame"], s["weight_kg"],
                          s["unit"], s["status"]) for s in sql["shipments"]])
        con.commit()
    finally:
        con.close()
    return path
