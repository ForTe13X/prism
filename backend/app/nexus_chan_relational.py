"""Phase-B.2 RELATIONAL channel (METRIC §8e) — the third FAILURE-DOMAIN-INDEPENDENT channel.

A true cross-domain nexus draws BOTH endpoint units toward the same tag-index set (from a third latent psi,
disjoint from the shape profile and the attribute theta), so the two units' tag sets overlap; a coincidence
does not. The score is the Jaccard overlap of the two units' position-aligned tag INDEX sets (the tag NAMES
are domain-specific and never compared — distributional/structural, never lexical). This reads ONLY the
relational tag store — never the series (shape) and never the categorical records (fingerprint) — so it is
a genuinely independent third vote (measured corr ≈0.13–0.19 with the other two). Same honest caveat as the
others: the tag signal's POWER is engineered (tag_shift power-tuned), its INDEPENDENCE is not.
"""
from __future__ import annotations


def relational_score(bridge: dict) -> float:
    a, b = set(bridge.get("a_tag_idx", [])), set(bridge.get("b_tag_idx", []))
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)
