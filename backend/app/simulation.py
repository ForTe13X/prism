"""Trajectory simulation (decision-support) — standalone, deterministic, domain-agnostic.

Projects ONE numeric attribute `horizon` frames past `now` under a baseline + N intervention
scenarios, each with an uncertainty band (K deterministic rolls), threshold-breach detection, and
a verdict ranking the scenarios. ALL domain knowledge lives in the spec (range / threshold /
optional `dynamics`); this engine hardcodes no domain.

Parallel-dev isolation (by design): its own deterministic hash, imports ONLY
``specs_loader.load_spec`` — it does NOT import ``data_synth`` (which a sibling session is editing).
The baseline here is a standalone deterministic value; to drive it off live cockpit state later,
pass ``baseline=`` into :func:`simulate` — nothing else changes. No ``random``, no clock →
byte-reproducible.

Dynamics (per attribute, declared in spec `dynamics`, all optional):
  model=mean_revert, rate∈[0,1] (reversion strength), trend (per-frame drift, fraction of range
  span), volatility (per-frame shock, fraction of span). Sensible defaults when absent.
Scenario (intervention) shape: {label, at, delta, mode} where mode="shift" moves the reversion
  target by delta from frame `at` onward (a setpoint change), mode="pulse" adds delta once at `at`.
"""
from __future__ import annotations

import hashlib
import math
from statistics import median

from .specs_loader import load_spec

_NUMERIC = {"metric", "gauge", "timeseries"}
_ROLLS = 9  # deterministic samples used to form the uncertainty band
_MAX_HORIZON = 96


def _u(*parts: object) -> float:
    """Stable float in [0,1) from a seed (sha256 → first 8 hex digits). No random, no clock."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def _span(attr: dict) -> tuple[float, float, float]:
    lo, hi = (list(attr.get("range", [0, 100])) + [0, 1])[:2]
    return float(lo), float(hi), (float(hi) - float(lo)) or 1.0


def _baseline_value(spec_id: str, etype: str, attr: dict, idx: int) -> float:
    lo, _hi, span = _span(attr)
    return lo + span * _u(spec_id, etype, attr["name"], idx, "baseline")


def _dynamics(attr: dict) -> dict:
    d = dict(attr.get("dynamics") or {})
    lo, hi, span = _span(attr)
    return {
        "model": str(d.get("model", "mean_revert")),
        "rate": max(0.0, min(1.0, float(d.get("rate", 0.15)))),
        "trend": float(d.get("trend", 0.0)) * span,
        "vol": max(0.0, float(d.get("volatility", 0.12))) * span,
        "lo": lo,
        "hi": hi,
    }


def _roll(spec_id: str, etype: str, attr: dict, idx: int, baseline: float, horizon: int,
          scenario: dict, dyn: dict, k: int) -> list[float]:
    """One deterministic trajectory sample (roll k): values for frames 0..horizon (0 == now)."""
    at = int(scenario.get("at", 0))
    delta = float(scenario.get("delta", 0.0))
    mode = str(scenario.get("mode", "shift"))
    label = str(scenario.get("label", "baseline"))
    x = baseline
    out = [round(x, 3)]
    for f in range(1, horizon + 1):
        target = baseline + (delta if (mode == "shift" and f >= at) else 0.0)
        shock = dyn["vol"] * (_u(spec_id, etype, attr["name"], idx, label, k, f) - 0.5)
        x = x + dyn["rate"] * (target - x) + dyn["trend"] + shock
        if mode == "pulse" and f == at:
            x += delta
        x = min(dyn["hi"], max(dyn["lo"], x))
        out.append(round(x, 3))
    return out


def _trajectory(spec_id: str, etype: str, attr: dict, idx: int, baseline: float, horizon: int,
                scenario: dict, dyn: dict, threshold: dict | None) -> dict:
    rolls = [_roll(spec_id, etype, attr, idx, baseline, horizon, scenario, dyn, k) for k in range(_ROLLS)]
    limit = (threshold or {}).get("limit")
    frames: list[dict] = []
    breach_frame: int | None = None
    for f in range(horizon + 1):
        col = sorted(r[f] for r in rolls)
        lo, mid, hi = col[0], float(median(col)), col[-1]
        frames.append({"f": f, "lo": round(lo, 3), "mid": round(mid, 3), "hi": round(hi, 3)})
        if breach_frame is None and limit is not None and mid >= float(limit):
            breach_frame = f
    return {
        "label": str(scenario.get("label", "baseline")),
        "frames": frames,
        "breach_frame": breach_frame,
        "terminal_mid": frames[-1]["mid"],
    }


def _verdict(trajectories: list[dict], threshold: dict | None) -> dict:
    breaches = {t["label"]: t["breach_frame"] for t in trajectories}
    limit = (threshold or {}).get("limit")
    if limit is None:
        best = min(trajectories, key=lambda t: t["terminal_mid"])
        return {"objective": "min_terminal", "best_label": best["label"], "breaches": breaches,
                "reason": f"无阈值;按终值最低取 {best['label']}"}
    # avoid breach first; among those latest/none; tiebreak lower terminal_mid
    def score(t: dict) -> tuple:
        bf = t["breach_frame"]
        return (bf is None, bf if bf is not None else 1 << 30, -t["terminal_mid"])

    best = max(trajectories, key=score)
    if best["breach_frame"] is None:
        reason = f"{best['label']} 在 {len(best['frames']) - 1} 帧内不越限(limit={limit})"
    else:
        reason = f"无方案完全避免;{best['label']} 越限最晚(帧 {best['breach_frame']})"
    return {"objective": "avoid_breach", "limit": float(limit), "best_label": best["label"],
            "breaches": breaches, "reason": reason}


def simulate(spec_id: str, entity_type: str, attribute: str, *, horizon: int = 12,
             scenarios: list[dict] | None = None, row_index: int | None = None,
             baseline: float | None = None) -> dict:
    """Run baseline + scenarios for one numeric attribute of one entity row. Deterministic.

    Returns ``{ok, ...}``; ``ok=False`` with ``error`` for unknown spec / missing or non-numeric
    attribute. ``row_index`` defaults to the most decision-relevant row (highest baseline, i.e.
    closest to an upper threshold). Pass ``baseline`` to drive from live state.
    """
    spec = load_spec(spec_id)
    if spec is None:
        return {"ok": False, "error": f"spec not found: {spec_id}"}
    entity = next((e for e in spec.get("entities", []) if e.get("type") == entity_type), None)
    if entity is None:
        return {"ok": False, "error": f"entity not in spec: {entity_type}"}
    attr = next((a for a in entity.get("attributes", []) if a.get("name") == attribute), None)
    if attr is None or attr.get("semantic_type") not in _NUMERIC:
        return {"ok": False, "error": f"attribute missing or non-numeric: {attribute}"}

    horizon = max(1, min(int(horizon), _MAX_HORIZON))
    count = max(1, int(entity.get("count", 1)))
    if row_index is None:
        row_index = max(range(count), key=lambda i: _baseline_value(spec_id, entity_type, attr, i))
    row_index = max(0, min(count - 1, int(row_index)))
    base = float(baseline) if baseline is not None else _baseline_value(spec_id, entity_type, attr, row_index)
    if not math.isfinite(base):
        return {"ok": False, "error": "baseline must be finite"}

    dyn = _dynamics(attr)
    threshold = attr.get("threshold")
    scen_list = [{"label": "baseline", "at": 0, "delta": 0.0, "mode": "shift"}] + list(scenarios or [])
    trajectories = [_trajectory(spec_id, entity_type, attr, row_index, base, horizon, s, dyn, threshold) for s in scen_list]

    return {
        "ok": True,
        "spec_id": spec_id, "entity_type": entity_type, "attribute": attribute,
        "row_index": row_index, "baseline": round(base, 3),
        "now": int((spec.get("temporal") or {}).get("now", 0)),
        "horizon": horizon, "range": attr.get("range"), "unit": attr.get("unit", ""),
        "threshold": threshold, "dynamics": {"model": dyn["model"], "rate": dyn["rate"]},
        "trajectories": trajectories,
        "verdict": _verdict(trajectories, threshold),
        "confidence": {"rolls": _ROLLS,
                       "note": "band = min/median/max across deterministic rolls; baseline is standalone synthetic until wired to live state"},
    }
