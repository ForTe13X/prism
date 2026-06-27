"""Phase-B.1 SHAPE channel (METRIC §8d) — reads ONLY the metric timeseries.

A true cross-domain nexus injects the SAME dip profile into both endpoints' series (at independent frames),
so the two trough-aligned dip windows correlate; a coincidence does not. The score is the max-lag Pearson
correlation of the two windows, each centred on its OWN in-band trough (so it is offset-free — it never
uses the |Δframe| difference the time baseline lives on; it re-derives each trough internally and reads no
attribute and no eval label). This is one of the two FAILURE-DOMAIN-INDEPENDENT channels: it cannot see the
SQL attribute store the fingerprint channel reads.
"""
from __future__ import annotations

import math

from .data_package_xdom import KNOBS


def _z(xs: list[float]) -> list[float]:
    n = len(xs) or 1
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / n) or 1.0
    return [(x - m) / sd for x in xs]


def _pearson(a: list[float], b: list[float]) -> float:
    za, zb = _z(a), _z(b)
    return sum(x * y for x, y in zip(za, zb)) / (len(za) or 1)


def _max_lag_pearson(a: list[float], b: list[float], max_lag: int = 3) -> float:
    """Best correlation over small integer shifts — robust to a ±frame trough-detection jitter."""
    best = -2.0
    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            x, y = a[lag:], b[: len(b) - lag]
        elif lag < 0:
            x, y = a[: len(a) + lag], b[-lag:]
        else:
            x, y = a, b
        if len(x) >= 4:
            best = max(best, _pearson(x, y))
    return best


def _trough_window(series: list[float]) -> list[float]:
    """The dip window: the in-band argmin (the unit's own trough) ± half_width. The channel finds the
    trough itself, so it is independent of the candidacy anchor frame passed on the bridge."""
    lo, span, hw = KNOBS["band_lo"], KNOBS["band_span"], KNOBS["half_width"]
    win = series[lo:lo + span]
    f = lo + min(range(len(win)), key=lambda i: win[i])
    a, b = max(0, f - hw), min(len(series), f + hw + 1)
    return series[a:b]


def shape_score(bridge: dict) -> float:
    return _max_lag_pearson(_trough_window(bridge["a_series"]), _trough_window(bridge["b_series"]))
