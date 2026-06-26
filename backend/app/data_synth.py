"""Deterministic data synthesis from a spec, with a time/frame axis (P1).

v0 needs no real data source: each value is derived by HASHING a stable seed
(spec_id, entity_type, row_index, attr_name[, sub-key]) into [0,1] — so every run is byte-identical
(no ``random``, no clock). Each attribute's ``semantic_type`` decides how that hash becomes a value
(a category pick, an in-range number, a thresholded gauge, a 24-point series, …).

P1 adds a ``frame`` axis. Time enters values ONLY through a smooth, deterministic ``_wiggle(frame)``
signal, and ONLY for attributes the spec marks ``evolves: true``. So:

  * an attribute WITHOUT ``evolves`` is byte-identical across every frame (identity stays put), and
    in fact equals its v0 value — ``frame`` never touches its seed;
  * an attribute WITH ``evolves`` drifts around that same v0 baseline, with amplitude set by
    ``drift`` (a fraction of the value's span; sensible per-type default if omitted).

The whole evolution rule lives here + in the spec (``evolves``/``drift``) — never per-domain. Swap to
a real backing store later by replacing ``synth_entity_rows`` — the API + renderer don't change.
"""
from __future__ import annotations

import hashlib
import math

# Default drift magnitude (fraction of the value's span / value-set spread) when an attribute is
# marked ``evolves: true`` but gives no explicit ``drift``. Keyed by semantic_type, NOT by domain:
# discrete states should be able to traverse their whole value list; numbers wander more gently.
_DEFAULT_DRIFT = {"status": 0.8, "category": 0.8, "text": 1.0}
_DEFAULT_DRIFT_NUMERIC = 0.3  # metric / gauge


def _unit(*parts: object) -> float:
    """Stable float in [0,1] from a seed (sha256 → first 8 hex digits; ``ffffffff`` maps to 1.0)."""
    seed = "|".join(str(p) for p in parts)
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def _as_int(value: object, default: int) -> int:
    """Coerce a spec-author value to int, falling back to ``default`` on anything non-numeric.

    Spec files are author-controlled and unvalidated, so a stray ``"points": "x"`` must degrade to a
    default rather than 500 the data endpoint — matching how every other spec coercion here behaves.
    """
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _wiggle(frame: int, *seed: object) -> float:
    """A smooth, deterministic signal in ~[-1, 1] over the frame axis, mean ≈ 0.

    A slow trend (period ~11–33 frames) plus a small faster ripple, with hash-derived
    frequencies/phases per seed. No randomness, no clock — purely a function of ``frame`` and seed,
    so replay is byte-reproducible. Used to drift evolving attributes around their baseline.
    """
    f1 = 0.03 + 0.09 * _unit(*seed, "wf1")  # slow trend
    p1 = _unit(*seed, "wp1")
    f2 = 0.13 + 0.17 * _unit(*seed, "wf2")  # faster ripple
    p2 = _unit(*seed, "wp2")
    main = math.sin(2 * math.pi * (f1 * frame + p1))
    ripple = 0.3 * math.sin(2 * math.pi * (f2 * frame + p2))
    return (main + ripple) / 1.3


def _drift(attr: dict) -> float:
    """How far an attribute may wander from its baseline, in [0,1]. 0 ⇒ static (frame-invariant)."""
    if not attr.get("evolves"):
        return 0.0
    if "drift" in attr:
        try:
            return max(0.0, min(1.0, float(attr["drift"])))
        except (TypeError, ValueError):
            return 0.0
    return _DEFAULT_DRIFT.get(attr.get("semantic_type"), _DEFAULT_DRIFT_NUMERIC)


def _evolve_unit(frame: int, drift: float, *seed: object) -> float:
    """[0,1] value at ``frame``. ``drift`` scales the wander around the frame-independent baseline.

    With ``drift == 0`` this is exactly the v0 baseline ``_unit(*seed)`` (so non-evolving attributes,
    and identity-only seeds, are unchanged). When it evolves, the baseline is first pulled toward the
    centre in proportion to ``drift`` — that gives the wiggle headroom so values don't pin flat against
    a range edge — then the smooth ``_wiggle`` displaces it and the result is clamped to [0,1].
    """
    base = _unit(*seed)
    if drift <= 0:
        return base
    centered = 0.5 + (base - 0.5) * (1.0 - drift)
    return min(1.0, max(0.0, centered + drift * _wiggle(frame, *seed)))


def synth_value(attr: dict, spec_id: str, etype: str, idx: int, frame: int = 0):
    """Synthesize one attribute value at ``frame``, deterministically, per its semantic_type.

    ``frame`` only influences the value when the attribute declares ``evolves`` (timeseries always
    treats ``evolves`` as "slide the window with the frame"); otherwise the result is frame-invariant.
    """
    st = attr.get("semantic_type")
    seed = (spec_id, etype, idx, attr.get("name"))
    drift = _drift(attr)

    if st == "identifier":
        # Identity never evolves — a row keeps its name across all frames.
        return f"{attr.get('prefix', 'E')}-{idx + 1:03d}"
    if st in ("category", "status"):
        values = attr.get("values", [])
        if not values:
            return None
        u = _evolve_unit(frame, drift, *seed)
        return values[int(u * len(values)) % len(values)]
    if st in ("metric", "gauge"):
        lo, hi = (attr.get("range", [0, 100]) + [0, 1])[:2]
        u = _evolve_unit(frame, drift, *seed)
        return round(lo + (hi - lo) * u, 2)
    if st == "timeseries":
        lo, hi = (attr.get("range", [0, 100]) + [0, 1])[:2]
        points = max(0, _as_int(attr.get("points", 24), 24))
        base = lo + (hi - lo) * (0.3 + 0.4 * _unit(*seed, "base"))
        amp = (hi - lo) * 0.22 * (0.5 + _unit(*seed, "amp"))
        period = max(2, points // 3)
        # The series is a sliding window of a single absolute-time signal s(t). When the attribute
        # evolves, the window ENDS at the current frame (so dragging the slider scrolls history);
        # otherwise it stays on the v0 window [0 .. points-1]. t may be negative (pre-history) — sin
        # and the hashed jitter handle that fine, keeping every frame deterministic.
        end = frame if drift > 0 else points - 1
        series = []
        for t in range(end - points + 1, end + 1):
            wave = base + amp * math.sin(2 * math.pi * t / period)
            jitter = (hi - lo) * 0.08 * (_unit(*seed, t) - 0.5)
            series.append(round(max(lo, min(hi, wave + jitter)), 2))
        return series
    if st == "text":
        u = _evolve_unit(frame, drift, *seed)
        phrases = ["巡检正常", "待复核", "已校准", "信号偶发抖动", "等待备件"]
        return phrases[int(u * len(phrases)) % len(phrases)]
    return None


def resolve_temporal(spec: dict) -> dict:
    """Normalize a spec's optional ``temporal`` block → {frames, now, step}.

    Domain-agnostic: a spec with no ``temporal`` collapses to a single frame (frames=1), which the
    frontend reads as "no replay axis". ``now`` is clamped into [0, frames-1].
    """
    t = spec.get("temporal") or {}
    frames = max(1, _as_int(t.get("frames", 1), 1))
    now = max(0, min(frames - 1, _as_int(t.get("now", frames - 1), frames - 1)))
    step = str(t.get("step", "frame"))
    return {"frames": frames, "now": now, "step": step}


def resolve_frame(spec: dict, frame: int | None) -> int:
    """Clamp a requested frame into the spec's valid range; default to ``now`` when unspecified."""
    temporal = resolve_temporal(spec)
    f = temporal["now"] if frame is None else _as_int(frame, temporal["now"])
    return max(0, min(temporal["frames"] - 1, f))


def synth_entity_rows(entity: dict, spec_id: str, frame: int = 0) -> list[dict]:
    """All rows for one entity type at ``frame`` — `count` rows, each a {_id, ...attribute values}."""
    etype = entity["type"]
    rows: list[dict] = []
    for idx in range(max(0, _as_int(entity.get("count", 5), 5))):
        row: dict = {"_id": f"{etype}-{idx + 1:03d}"}
        for attr in entity.get("attributes", []):
            row[attr["name"]] = synth_value(attr, spec_id, etype, idx, frame)
        rows.append(row)
    return rows
