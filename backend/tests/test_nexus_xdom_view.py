"""Per-bridge nexus_confidence view — the data the galaxy-collision visual renders. Pins honest sparsity,
the FDR-controlled tiering (GLOW = absolute significance under Benjamini–Hochberg, not a relative decile),
the §13 extinction property (a zero-coupling pair lights ≈ nothing), and determinism."""
from __future__ import annotations

from backend.app.nexus_xdom_view import bridge_view, fdr_extinction_check


def test_honest_sparsity_and_fdr_tier_structure():
    v = bridge_view("xe-0")
    sc = v["scorecard"]
    assert sc["candidates"] == sc["high"] + sc["medium"] + sc["coincidence"]
    assert sc["coincidence"] > sc["high"] + sc["medium"]      # most candidates are ghosts (honest sparsity)
    assert 0 < sc["high"] < sc["candidates"]                  # a few FDR-significant bridges light, not all
    assert sc["fdr_q"] == 0.1 and sc["null_samples"] > 0      # the absolute-significance machinery is wired
    # GLOW (high) follows ONLY from FDR significance; medium = relative ≥2/3 vote but NOT FDR-significant
    for b in v["bridges"]:
        votes = b["shape_fires"] + b["fingerprint_fires"] + b["relational_fires"]
        assert b["votes"] == votes
        assert b["fdr_significant"] == (b["confidence"] == "high")
        if b["confidence"] == "high":
            assert b["fdr_significant"]                       # glowing ⇒ survived BH-FDR
        elif b["confidence"] == "medium":
            assert votes >= 2 and not b["fdr_significant"]    # ranked-high but not absolutely significant (dim)
        else:
            assert votes < 2 and not b["fdr_significant"]


def test_fdr_glow_is_high_precision():
    # the absolute+FDR gate makes the lit set MUCH cleaner than the old relative decile (was ~0.66)
    v = bridge_view("xe-0")
    sc = v["scorecard"]
    assert sc["high_tier_precision"] >= 0.85                  # FDR-significant glow is mostly real couplings
    assert sc["high"] < sc["true_couplings"]                  # ...but FDR is conservative ⇒ honest low recall
    assert sc["expected_false_high"] == round(0.1 * sc["high"], 2)


def test_glow_extinguishes_on_zero_coupling_pairs():
    # OBSERVER §13: the load-bearing fix. A zero-coupling pair (this A × an unrelated B) must light ≈ nothing,
    # while a real pair lights > 0 — the old relative top-decile gave ~8.27 for BOTH (precision = prevalence).
    r = fdr_extinction_check([f"xe-{i}" for i in range(20)])
    assert r["real_pair_mean_high"] > 1.0                     # real pairs still light a handful
    assert r["zero_pair_mean_high"] < 0.5                     # zero pairs EXTINGUISH (≈0, not ~8)
    assert r["extinguishes_on_zero"] is True
    assert r["real_pair_high_precision"] >= 0.85              # and the surviving glow is clean


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
    fc = client.get("/api/nexus_xdom/fdr_check?seeds=8")
    assert fc.status_code == 200 and fc.json()["extinguishes_on_zero"] is True
