"""Coupling external validity on REAL paired data along a STRENGTH SPECTRUM (METRIC §8j): breast_cancer
views of the same tumor — a near-duplicate softball (same-feature mean↔worst) vs a genuine cross-aspect
coupling (disjoint features). Pins the honest finding: the convergence signal degrades monotonically as the
coupling becomes genuinely cross-domain, raw match is ~chance both ends (non-leaky), and it's deterministic.
Needs scikit-learn (genuine real data; never fabricated)."""
from __future__ import annotations

import pytest

sklearn = pytest.importorskip("sklearn")  # real data only — never faked

from backend.app.nexus_real_pair import run_real_coupling


def test_signal_degrades_from_softball_to_genuine_cross_aspect():
    r = run_real_coupling()
    assert r.get("is_real_data") is True and r["n"] == 569
    same = r["same_feature_near_duplicate"]
    disjoint = r["disjoint_feature_cross_aspect"]
    # surface is non-leaky at BOTH ends (the per-view affine ⇒ raw match ~chance)
    assert 0.40 <= same["raw_value_match_auc"] <= 0.60
    assert 0.40 <= disjoint["raw_value_match_auc"] <= 0.60
    # the same-feature views are an honestly-DISCLOSED softball (near-duplicate, aligned corr ~0.87)
    assert same["same_base_diag_corr"] > 0.7
    assert same["semantic_zscore_auc"] >= 0.85               # strong on the near-copy (the easy end)
    # the GENUINE cross-aspect coupling: signal DEGRADES sharply, unique resolution ≈ impossible
    assert disjoint["semantic_zscore_auc"] < same["semantic_zscore_auc"] - 0.15   # monotone degradation
    assert disjoint["semantic_zscore_auc"] > 0.55           # ...but still above chance (signal partly transfers)
    assert disjoint["resolver_top1_acc"] < 0.05             # genuine cross-aspect: not uniquely resolvable
    assert r["verdict"] == "real_coupling_signal_degrades_from_softball_to_genuine_cross_aspect"


def test_deterministic_and_api():
    assert run_real_coupling() == run_real_coupling()
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    res = client.get("/api/nexus_xdom/real_coupling")
    assert res.status_code == 200
    body = res.json()
    assert body["checks"]["surface_non_leaky_both(raw~chance)"] is True
    assert body["checks"]["signal_degrades_with_genuineness"] is True
    assert body["checks"]["same_feature_is_a_softball(diag_corr>0.7)"] is True
