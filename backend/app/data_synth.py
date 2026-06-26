"""Deterministic data synthesis from a spec.

v0 needs no real data source: each value is derived by HASHING a stable seed
(spec_id, entity_type, row_index, attr_name[, sub-key]) into [0,1) — so every run is byte-identical
(no `random`, no clock). Each attribute's ``semantic_type`` decides how that hash becomes a value
(a category pick, an in-range number, a thresholded gauge, a 24-point series, …). Swap to a real
backing store later by replacing ``synth_entity_rows`` — the API + renderer don't change.
"""
from __future__ import annotations

import hashlib
import math


def _unit(*parts: object) -> float:
    """Stable float in [0,1) from a seed (sha256 → first 8 hex digits)."""
    seed = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def _pick(values: list, *seed: object):
    if not values:
        return None
    return values[int(_unit(*seed) * len(values)) % len(values)]


def _in_range(rng: list, *seed: object) -> float:
    lo, hi = (rng + [0, 1])[:2]
    return round(lo + (hi - lo) * _unit(*seed), 2)


def synth_value(attr: dict, spec_id: str, etype: str, idx: int):
    """Synthesize one attribute value, deterministically, per its semantic_type."""
    st = attr.get("semantic_type")
    seed = (spec_id, etype, idx, attr.get("name"))

    if st == "identifier":
        return f"{attr.get('prefix', 'E')}-{idx + 1:03d}"
    if st in ("category", "status"):
        return _pick(attr.get("values", []), *seed)
    if st in ("metric", "gauge"):
        return _in_range(attr.get("range", [0, 100]), *seed)
    if st == "timeseries":
        lo, hi = (attr.get("range", [0, 100]) + [0, 1])[:2]
        points = int(attr.get("points", 24))
        base = lo + (hi - lo) * (0.3 + 0.4 * _unit(*seed, "base"))
        amp = (hi - lo) * 0.22 * (0.5 + _unit(*seed, "amp"))
        period = max(2, points // 3)
        series = []
        for t in range(points):
            wave = base + amp * math.sin(2 * math.pi * t / period)
            jitter = (hi - lo) * 0.08 * (_unit(*seed, t) - 0.5)
            series.append(round(max(lo, min(hi, wave + jitter)), 2))
        return series
    if st == "text":
        return _pick(["巡检正常", "待复核", "已校准", "信号偶发抖动", "等待备件"], *seed)
    return None


def synth_entity_rows(entity: dict, spec_id: str) -> list[dict]:
    """All rows for one entity type — `count` rows, each a {_id, ...attribute values}."""
    etype = entity["type"]
    rows: list[dict] = []
    for idx in range(int(entity.get("count", 5))):
        row: dict = {"_id": f"{etype}-{idx + 1:03d}"}
        for attr in entity.get("attributes", []):
            row[attr["name"]] = synth_value(attr, spec_id, etype, idx)
        rows.append(row)
    return rows
