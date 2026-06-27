"""RESEARCH_axiom_gain full protocol — the cross-model matrix aggregation into a real mini-result. Pins the
honesty contract: per-cell bootstrap mean±CI (a CI is reported, not a bare point), missing cells surface in
`coverage` (never silently dropped), the token-saving win is significant, the axiom condition is Pareto-
dominant on cost×quality, and the §5 build break-even stays the honest negative (N*=∞). Runs on the FROZEN
guaranteed-cached subset so it is deterministic regardless of any background fixture population."""
from __future__ import annotations

from backend.app.axiom_gain_protocol import run_protocol

# the subset that has been frozen in fixtures since the first DP2 run — guaranteed cached, fast, deterministic
SUB = {"models": ["qwen-3-8b-instruct", "google/gemma-4-12b-qat"],
       "seeds": [f"ho-{i}" for i in range(4)], "dirts": [0.0, 0.6]}


def _run():
    return run_protocol(**SUB)


def test_matrix_reports_mean_and_bootstrap_ci_per_cell():
    r = _run()
    assert r["coverage"]["cached"] == r["coverage"]["requested"] and not r["coverage"]["missing"]
    assert len(r["matrix"]) == 4  # 2 models × 2 dirts
    for c in r["matrix"]:
        lo, hi = c["quality_delta_ci95"]
        assert lo <= c["quality_delta_mean"] <= hi          # the point sits inside its own CI
        slo, shi = c["token_saving_ci95"]
        assert slo <= c["token_saving_mean"] <= shi
        assert c["n_seeds"] == 4


def test_token_saving_is_real_and_large():
    # the structural/compaction win: the axiom layer cuts ~60% of input tokens, CI excluding 0 in every cell
    r = _run()
    assert all(c["token_saving_excludes_0"] for c in r["matrix"])
    assert r["headline"]["mean_input_token_saving"] > 0.4
    assert r["headline"]["token_saving_significant_cells"] == "4/4"


def test_quality_never_meaningfully_worse_and_axiom_pareto_dominant():
    r = _run()
    assert r["headline"]["quality_never_worse"] is True          # axiom ΔF1 ≥ -0.02 everywhere
    fr = r["cost_per_correct_frontier"]
    assert fr["axiom_dominates"] is True and fr["naive_on_front"] == 0  # only axiom on the cost×quality front


def test_gain_grows_with_dirtiness_endpoint():
    # H2 (endpoint form): the gain is larger on dirtier data. The subset has 2 dirt levels so the endpoint
    # flag == monotonicity; the full 3-model run honestly separates endpoint (3/3) from true monotone (1/3).
    r = _run()
    assert r["headline"]["models_endpoint_gain_grows"] == "2/2"
    for model, rob in r["robustness_gain_vs_dirt"].items():
        assert rob["endpoint_hi_ge_lo"] is True
        assert "monotonic_increasing" in rob and "peak_dirt" in rob   # the honest trend fields exist


def test_build_amortization_is_the_honest_negative():
    # §5: structural axioms are build-free; the learned dictionary adds ~0 held-out F1 ⇒ never amortizes
    r = _run()
    amo = r["build_amortization"]
    assert amo.get("breakeven_N_dictionary") is None            # N* = ∞ (honest negative, surfaced)
    assert "honest" in amo.get("note", "").lower() or "negative" in amo.get("note", "").lower()


def test_deterministic():
    assert run_protocol(**SUB) == run_protocol(**SUB)


def test_quality_significance_is_honestly_partial():
    # the honest under-claim: quality gain is NOT significant in every cell. On the 4-seed subset only 1/4
    # cells clear CI>0; the other three must be flagged indeterminate (excludes_0 False, lo ≤ 0), not hidden.
    r = _run()
    assert r["headline"]["quality_gain_significant_cells"] == "1/4"
    indeterminate = [c for c in r["matrix"] if not c["quality_delta_excludes_0"]]
    assert len(indeterminate) == 3
    assert all(c["quality_delta_ci95"][0] <= 0 for c in indeterminate)   # their CI truly straddles/≤0


def test_coverage_reports_missing_cells_not_drops_them():
    # ask for a seed that is NOT in fixtures — it must appear in coverage.missing, not vanish or error
    r = run_protocol(models=["qwen-3-8b-instruct"], seeds=["ho-0", "definitely-uncached-seed"], dirts=[0.0])
    assert any(m["seed"] == "definitely-uncached-seed" for m in r["coverage"]["missing"])
    assert r["coverage"]["cached"] >= 1


def test_api_protocol():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    res = client.get("/api/axiomgain/logistics_demo/protocol")
    assert res.status_code == 200
    body = res.json()
    assert "matrix" in body and "headline" in body and "honest_verdict" in body
    assert "coverage" in body
    assert client.get("/api/axiomgain/nope/protocol").status_code == 404   # missing source → 404 (mirrors ablation)
