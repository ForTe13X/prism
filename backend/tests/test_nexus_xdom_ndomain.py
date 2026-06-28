"""OBSERVER §13 N-domain family-wise screen (METRIC §8i). Pins the load-bearing claims: the relative
top-decile collapses ∝ 1/N²; §8h's per-pair FDR recovers precision (~flat, high) at scale; pooled
family-wise FDR is a STRICTER (never-more-lit) option that can under-power on sparse signal; determinism."""
from __future__ import annotations

from backend.app.nexus_xdom_ndomain import precision_vs_n, run_ndomain_screen


def test_relative_top_decile_collapses_with_N():
    # the §13 collapse: lights ~10% of EVERY pair ⇒ false-high ∝ C(N,2) ⇒ precision craters as N grows
    p2 = run_ndomain_screen(2, true_frac=0.05)["relative_top_decile"]["precision"]
    p8 = run_ndomain_screen(8, true_frac=0.05)["relative_top_decile"]["precision"]
    assert p2 > 0.5 and p8 < 0.10                              # 0.80 → ~0.02
    d8 = run_ndomain_screen(8, true_frac=0.05)["relative_top_decile"]
    assert d8["false_high"] > 10 * d8["true_high"]             # swamped by false positives


def test_per_pair_fdr_recovers_precision_at_scale():
    # §8h applied per pair: zero pairs extinguish ⇒ precision stays HIGH and ~flat in N (the recovery)
    for n in (4, 8, 16):
        pp = run_ndomain_screen(n, true_frac=0.05)["per_pair_fdr"]
        assert pp["precision"] is not None and pp["precision"] >= 0.9
        assert pp["true_high"] > 0                             # and it still lights the real ones (recall > 0)


def test_pooled_is_stricter_never_lights_more_than_per_pair():
    # pooled family-wise BH is a global guarantee ⇒ it can only be MORE conservative than per-pair
    for n in (4, 8, 16):
        s = run_ndomain_screen(n, true_frac=0.05)
        assert s["pooled_family_wise_fdr"]["high"] <= s["per_pair_fdr"]["high"]


def test_sweep_shape_and_determinism():
    r = precision_vs_n([2, 4, 8], true_frac=0.05)
    assert [row["n_domains"] for row in r["sweep"]] == [2, 4, 8]
    assert [row["n_pairs"] for row in r["sweep"]] == [1, 6, 28]
    # relative degrades, per-pair holds — the headline contrast
    assert r["sweep"][0]["precision_relative"] > r["sweep"][2]["precision_relative"]
    assert r["sweep"][2]["precision_per_pair_fdr"] >= 0.9
    assert run_ndomain_screen(8, true_frac=0.05) == run_ndomain_screen(8, true_frac=0.05)


def test_api():
    from fastapi.testclient import TestClient
    from backend.app.main import app

    client = TestClient(app)
    r = client.get("/api/nexus_xdom/ndomain?n_domains=6&true_frac=0.1")
    assert r.status_code == 200
    body = r.json()
    assert "relative_top_decile" in body and "per_pair_fdr" in body and "pooled_family_wise_fdr" in body
    assert client.get("/api/nexus_xdom/ndomain_sweep").status_code == 200
