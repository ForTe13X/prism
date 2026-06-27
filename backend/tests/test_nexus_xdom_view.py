"""Per-bridge nexus_confidence view — the data the galaxy-collision visual renders. Pins honest sparsity
(most candidates are ghosts), the label-free tiering (the eval label never sets the tier), and determinism."""
from __future__ import annotations

from backend.app.nexus_xdom_view import bridge_view


def test_honest_sparsity_and_tier_structure():
    v = bridge_view("xe-0")
    sc = v["scorecard"]
    assert sc["candidates"] == sc["high"] + sc["medium"] + sc["coincidence"]
    assert sc["coincidence"] > sc["high"] + sc["medium"]      # most candidates are ghosts (honest sparsity)
    assert 0 < sc["high"] < sc["candidates"]                  # a few verified bridges light, not all
    # every bridge's tier follows ONLY from the ≥2/3 channel vote — never from its truth label
    for b in v["bridges"]:
        votes = b["shape_fires"] + b["fingerprint_fires"] + b["relational_fires"]
        assert b["votes"] == votes
        expect = "high" if votes >= 2 else ("medium" if votes == 1 else "coincidence")
        assert b["confidence"] == expect
        assert b["dissent"] == (0 < votes < 3)


def test_high_tier_is_mostly_real_but_recall_is_honestly_low():
    v = bridge_view("xe-0")
    sc = v["scorecard"]
    assert sc["high_tier_precision"] >= 0.6                   # the lit set is mostly real couplings
    assert sc["high"] < sc["true_couplings"]                  # ...but the ≥2/2 gate lights only some (low recall)


def test_layout_entities_present():
    v = bridge_view("xe-1")
    assert len(v["A"]["units"]) == len(v["B"]["units"]) >= 8
    assert v["A"]["prefix"] != v["B"]["prefix"] and v["A"]["metric"] != v["B"]["metric"]
    assert any(u["anchor"] for u in v["A"]["units"])          # some units carry a dip (anchors)


def test_deterministic_and_api():
    assert bridge_view("xe-3") == bridge_view("xe-3")
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    r = client.get("/api/nexus_xdom/view?seed=xe-2")
    assert r.status_code == 200
    body = r.json()
    assert "bridges" in body and "scorecard" in body and "caveat" in body
