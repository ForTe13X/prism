"""Tests for the agentic-STYLE heterogeneous parser (§5): raw_render → parser round-trip.

Asserts the welded disciplines:
  * DETERMINISM — same package renders + parses byte-identically across runs.
  * ROUND-TRIP RECOVERY — parsed ids/fields recover the package's REAL structured truth (from
    ``generate()``) at a high rate; we compute an explicit recovery score on the clean package and a
    dirty one, and report both.
  * PROVENANCE — every parsed row carries ``_provenance`` (source + line) and a ``_confidence``.
  * OBSERVABLE FAILURE — the parser reports parsed-vs-failed counts (never a silent drop).
  * ROBUSTNESS — recovery degrades GRACEFULLY as dirtiness rises but stays above a sensible floor.
"""
from __future__ import annotations

import json

from backend.app.data_package import generate
from backend.app.raw_render import render_package
from backend.app.parser import parse_package

SOURCE = "logistics_demo"


def _roundtrip(dirtiness: float, link: int = 2):
    pkg = generate(SOURCE, dirtiness=dirtiness, link_explicitness=link)
    rendered = render_package(pkg)
    parsed = parse_package(rendered)
    return pkg, rendered, parsed


# --------------------------------------------------------------------------------------------------
# determinism
# --------------------------------------------------------------------------------------------------
def test_render_is_deterministic():
    """Same package → byte-identical RAW render (no clock, no random)."""
    a = render_package(generate(SOURCE, dirtiness=0.5, link_explicitness=2))
    b = render_package(generate(SOURCE, dirtiness=0.5, link_explicitness=2))
    assert a["raw"] == b["raw"]


def test_parse_is_deterministic():
    """Same package → byte-identical parse (entities + reports serialize identically)."""
    _, _, a = _roundtrip(0.5)
    _, _, b = _roundtrip(0.5)
    assert json.dumps(a, ensure_ascii=False, sort_keys=True) == json.dumps(b, ensure_ascii=False, sort_keys=True)


# --------------------------------------------------------------------------------------------------
# provenance + confidence on every row
# --------------------------------------------------------------------------------------------------
def test_provenance_present_on_rows():
    _, _, parsed = _roundtrip(0.6)
    ent = parsed["entities"]
    rows = ent["warehouses"] + ent["carriers"] + ent["shipments"] + ent["news"]
    assert rows, "expected parsed rows"
    for r in rows:
        prov = r["_provenance"]
        assert prov["source"] in ("sql", "news")
        assert isinstance(prov["line"], int) and prov["line"] >= 0
        assert 0.0 <= r["_confidence"] <= 1.0
    # throughput points also carry provenance
    for wid, pts in ent["throughput"].items():
        for pt in pts:
            assert pt["_provenance"]["source"] == "throughput"
            assert 0.0 <= pt["_confidence"] <= 1.0


# --------------------------------------------------------------------------------------------------
# observable failure report
# --------------------------------------------------------------------------------------------------
def test_observable_failure_counts_reported():
    """The parser accounts for every line: a parsed/failed tally per source + a rolled-up summary.
    On a clean package nothing should fail; the report structure exists regardless."""
    pkg, _, parsed = _roundtrip(0.0)
    summary = parsed["summary"]
    assert summary["parsed"] > 0
    assert summary["failed"] == 0  # clean package: zero failures, byte-clean round-trip
    for src in ("sql", "news", "throughput"):
        rep = parsed["reports"][src]
        assert "parsed" in rep and "failed" in rep and "failures" in rep
        assert isinstance(rep["failures"], list)
        # every failure entry is OBSERVABLE: carries a reason + provenance
        for f in rep["failures"]:
            assert f["reason"] and "source" in f and "line" in f


def test_no_silent_drop_all_rows_accounted():
    """Parsed entity counts equal the package's own store counts on a clean package (round-trip is
    lossless in count terms) — proving rows are neither invented nor silently dropped."""
    pkg, _, parsed = _roundtrip(0.0)
    sql = pkg["stores"]["sql"]
    ent = parsed["entities"]
    assert len(ent["warehouses"]) == len(sql["warehouses"])
    assert len(ent["carriers"]) == len(sql["carriers"])
    assert len(ent["shipments"]) == len(sql["shipments"])
    assert len(ent["news"]) == len(pkg["stores"]["news"])
    total_tp = sum(len(s) for s in ent["throughput"].values())
    truth_tp = sum(len(s) for s in pkg["stores"]["timeseries"]["throughput"].values())
    assert total_tp == truth_tp


# --------------------------------------------------------------------------------------------------
# round-trip recovery score (parsed ↔ generate()'s structured truth)
# --------------------------------------------------------------------------------------------------
def _normalize_weight_kg(weight, unit):
    """Recover canonical kg from a parsed weight + unit (the dirtiness layer stored some in lb)."""
    if weight is None:
        return None
    if unit == "lb":
        return round(weight / 2.20462, 1)
    return round(weight, 1)


def recovery_score(pkg: dict, parsed: dict, truth_pkg: dict | None = None) -> dict:
    """Fraction of the package's REAL structured truth recovered by the parse. Computed per field so
    we can see which dimensions dirtiness erodes (status nulls, lb weights, news time offsets) vs the
    id/structure backbone that should stay near-perfect.

    ``truth_pkg`` is the CLEAN (dirtiness=0) package = the round-trip ground truth. When the parse came
    from a dirty package, scoring its ids/struct against the CLEAN truth makes degradation OBSERVABLE
    (e.g. a news frame shifted by the time-offset dirtiness no longer matches the clean frame). When
    omitted, ``pkg`` itself is the truth (clean self-round-trip)."""
    truth_pkg = truth_pkg or pkg
    truth_sql = truth_pkg["stores"]["sql"]
    ent = parsed["entities"]

    # warehouses: id → (region, port, name) exact recovery
    twh = {w["id"]: w for w in truth_sql["warehouses"]}
    pwh = {w["id"]: w for w in ent["warehouses"]}
    wh_ok = sum(1 for wid, w in twh.items()
                if wid in pwh and (pwh[wid]["region"], pwh[wid]["port"], pwh[wid]["name"]) == (w["region"], w["port"], w["name"]))

    # shipments: id present + structural fields (warehouse/carrier/frame) + weight (unit-normalized)
    tsh = {s["id"]: s for s in truth_sql["shipments"]}
    psh = {s["id"]: s for s in ent["shipments"]}
    id_ok = sum(1 for sid in tsh if sid in psh)
    struct_ok = sum(1 for sid, s in tsh.items()
                    if sid in psh and psh[sid]["warehouse_id"] == s["warehouse_id"]
                    and psh[sid]["carrier_id"] == s["carrier_id"]
                    and psh[sid]["dispatch_frame"] == s["dispatch_frame"])
    # weight: CLEAN truth is canonical kg. The dirty parse may carry an lb value; normalizing it by the
    # parsed unit must recover the clean kg within rounding — the unit-resolution win. (lb→kg→back loses
    # a touch of precision, hence the small tolerance.)
    weight_ok = 0
    for sid, s in tsh.items():
        if sid not in psh:
            continue
        truth_kg = round(s["weight_kg"], 1)  # clean truth weight is always kg
        got_kg = _normalize_weight_kg(psh[sid]["weight"], psh[sid]["unit"])
        if got_kg is not None and abs(truth_kg - got_kg) <= 1.0:
            weight_ok += 1

    # news: id present + frame recovered. Scoring against the CLEAN truth frame means the dirtiness
    # time-offsets become OBSERVABLE recovery loss (a shifted stamp no longer matches the true frame).
    tnews = {n["id"]: n for n in truth_pkg["stores"]["news"]}
    pnews = {n["id"]: n for n in ent["news"] if n["id"]}
    news_id_ok = sum(1 for nid in tnews if nid in pnews)
    news_frame_ok = sum(1 for nid, n in tnews.items() if nid in pnews and pnews[nid]["frame"] == n["frame"])

    # throughput: every (frame,value) point recovered exactly (against the CLEAN truth series, so
    # frozen-point sensor-glitch dirtiness shows up as point-level recovery loss)
    ttp = truth_pkg["stores"]["timeseries"]["throughput"]
    ptp = ent["throughput"]
    tp_total = sum(len(s) for s in ttp.values())
    tp_ok = 0
    for wid, series in ttp.items():
        got = {pt["frame"]: pt["value"] for pt in ptp.get(wid, [])}
        tp_ok += sum(1 for t, v in enumerate(series) if got.get(t) == v)

    n_wh, n_sh, n_news = len(twh), len(tsh), len(tnews)
    # overall id-backbone recovery (the headline round-trip number) = ids recovered across all sources
    backbone_total = n_wh + n_sh + n_news + tp_total
    backbone_ok = wh_ok + id_ok + news_id_ok + tp_ok
    return {
        "warehouse_full": wh_ok / n_wh if n_wh else 1.0,
        "shipment_id": id_ok / n_sh if n_sh else 1.0,
        "shipment_struct": struct_ok / n_sh if n_sh else 1.0,
        "shipment_weight": weight_ok / n_sh if n_sh else 1.0,
        "news_id": news_id_ok / n_news if n_news else 1.0,
        "news_frame": news_frame_ok / n_news if n_news else 1.0,
        "throughput_point": tp_ok / tp_total if tp_total else 1.0,
        "backbone": backbone_ok / backbone_total if backbone_total else 1.0,
    }


def test_roundtrip_recovery_clean_is_high():
    """On a CLEAN package the parse recovers the real structured truth almost perfectly."""
    pkg, _, parsed = _roundtrip(0.0)
    rec = recovery_score(pkg, parsed)
    # clean: every dimension should be perfect (no dirtiness to erode anything)
    assert rec["backbone"] == 1.0
    assert rec["shipment_id"] == 1.0
    assert rec["shipment_struct"] == 1.0
    assert rec["shipment_weight"] == 1.0
    assert rec["news_frame"] == 1.0
    assert rec["throughput_point"] == 1.0


def test_roundtrip_recovery_dirty_above_floor():
    """On a DIRTY package recovery drops on the dirtied dimensions (news-time offsets, frozen points)
    but the id/structure backbone stays well above a sensible floor — ids/struct survive surface
    scramble; weights recover via unit-normalization."""
    truth = generate(SOURCE, dirtiness=0.0, link_explicitness=2)
    pkg, _, parsed = _roundtrip(0.6)
    rec = recovery_score(pkg, parsed, truth_pkg=truth)
    # the id backbone is robust — surface-form scramble does not lose rows
    assert rec["shipment_id"] == 1.0
    assert rec["shipment_struct"] == 1.0
    # weights recover after unit-normalization (we recover the stored number + its unit)
    assert rec["shipment_weight"] == 1.0
    # the backbone overall stays high even against the clean truth
    assert rec["backbone"] >= 0.9


def test_recovery_degrades_gracefully():
    """Recovery should be MONOTONE-ish: higher dirtiness never *raises* the dirtied-dimension recovery,
    and news-frame recovery (eroded by time offsets) is strictly lower when dirty — yet stays above a
    floor. This is the robustness curve (clean ≥ dirty, both above floor)."""
    pkg0, _, p0 = _roundtrip(0.0)
    pkg1, _, p1 = _roundtrip(0.8)
    r0 = recovery_score(pkg0, p0)
    r1 = recovery_score(pkg1, p1, truth_pkg=pkg0)  # score dirty parse against the CLEAN truth
    # clean recovers all news frames; dirty loses some to time offsets (graceful degradation)
    assert r0["news_frame"] == 1.0
    assert r1["news_frame"] < r0["news_frame"]  # strictly eroded by the time-offset dirtiness
    # but never collapses: ids still fully recovered, so news rows are all still found
    assert r1["news_id"] == 1.0
    # backbone floor across the whole dirtiness range
    assert r1["backbone"] >= 0.85


def test_recovery_report_smoke():
    """Print clean + dirty recovery rates (visible when run with -s) — honest reporting, not a claim."""
    pkg0, _, p0 = _roundtrip(0.0)
    pkg1, _, p1 = _roundtrip(0.6)
    r0, r1 = recovery_score(pkg0, p0), recovery_score(pkg1, p1, truth_pkg=pkg0)
    print("\nCLEAN recovery:", {k: round(v, 3) for k, v in r0.items()})
    print("DIRTY recovery:", {k: round(v, 3) for k, v in r1.items()})
    print("CLEAN failures:", p0["summary"], "| DIRTY failures:", p1["summary"])
    assert r0["backbone"] >= r1["backbone"]  # clean never worse than dirty on the backbone
