"""Phase-B.1 FINGERPRINT channel (METRIC §8d) — reads ONLY the SQL attribute store.

A true cross-domain nexus shifts BOTH endpoint units' categorical record distributions by the same theta
(index-aligned across domains, different category NAMES), so the two units' attribute histograms match
DISTRIBUTIONALLY — never lexically. The score is the negative L1 distance between the two position-aligned
histograms. This is the second FAILURE-DOMAIN-INDEPENDENT channel: it cannot see the metric series the
shape channel reads, and it compares distributions by position, so the disjoint category names never let it
collapse into a string match (the Phase-A pathology).

Honest limit: a per-column rank-normalised distance (distribution-shape invariant across the unit
population) would be more robust; the plain L1 on a thin R-record histogram is the validated minimum and
is the weaker of the two channels — see the power figures in §8d.
"""
from __future__ import annotations


def fingerprint_score(bridge: dict) -> float:
    a, b = bridge["a_hist"], bridge["b_hist"]
    return -sum(abs(x - y) for x, y in zip(a, b))
