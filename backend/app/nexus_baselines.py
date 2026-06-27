"""The dumb-baseline ladder (METRIC_nexus_reality §5) — the bar every lens must clear.

Each baseline scores a candidate bridge (higher = more "real") from OBSERVATIONS only. The point is the
⭐ TIME-COINCIDENCE baseline: it pays no modeling cost, just temporal closeness. Because at link L4–L5 the
entity strings are gone, time is the dominant natural separator — so a lens only earns its keep if it
STRICTLY exceeds this baseline's ROC-AUC there. The string baselines (Jaccard / entity-mention) are strong
at L1 (literal ids) and must collapse toward chance by L4 — that collapse is exactly the discriminative
interval the lenses are meant to fill.

All deterministic, pure functions of (bridge, context); no model, no clock.
"""
from __future__ import annotations

from .nexus_substrate import _tokens


def time_coincidence(bridge: dict, ctx: dict | None = None) -> float:
    """⭐ The lethal baseline: temporal closeness of news frame to the observed anomaly frame. Pays no
    modeling cost. 1/(1+|Δframe|) ∈ (0,1]."""
    return 1.0 / (1.0 + bridge["dframe"])


def _hub_identity_tokens(bridge: dict) -> set:
    h = bridge["hub"]
    toks: set = set()
    for k in ("id", "name", "region", "port"):
        toks |= _tokens(str(h.get(k, "")))
    return toks


def string_jaccard(bridge: dict, ctx: dict | None = None) -> float:
    """Token Jaccard between the news body and the hub's identity strings — strong at L1, ~0 by L4."""
    a, b = _tokens(bridge["news_body"]), _hub_identity_tokens(bridge)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / len(a | b) if (a | b) else 0.0


def entity_mention(bridge: dict, ctx: dict | None = None) -> float:
    """Raw cross-edge cue count: how many hub-identity cue TYPES (id/name/region/port) the news body
    literally contains. The crudest 'they mention each other' signal; 0 once the link is non-explicit."""
    body, h = bridge["news_body"], bridge["hub"]
    hits = 0
    for k in ("id", "name", "region", "port"):
        v = str(h.get(k, ""))
        if v and v in body:
            hits += 1
    return float(hits)


def anomaly_depth(bridge: dict, ctx: dict | None = None) -> float:
    """A non-relational structural baseline: how deep the hub's metric dip is. Should NOT by itself
    separate real bridges from coincident ones — a sanity floor (if it 'wins', the task is degenerate)."""
    return float(bridge.get("anomaly_depth", 0.0))


# name → scorer; the ladder the metric is reported against. Time-coincidence is the one to beat.
BASELINES = {
    "time_coincidence": time_coincidence,   # ⭐ the bar
    "string_jaccard": string_jaccard,
    "entity_mention": entity_mention,
    "anomaly_depth": anomaly_depth,
}


def score_all(bridges: list, ctx: dict | None = None) -> dict:
    """Return {baseline_name: [score per bridge]} aligned with ``bridges`` order."""
    return {name: [fn(b, ctx) for b in bridges] for name, fn in BASELINES.items()}
