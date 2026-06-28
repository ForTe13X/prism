"""RESEARCH_axiom_gain full protocol — the cross-model matrix aggregation into a real mini-result. Pins the
honesty contract: per-cell bootstrap mean±CI (a CI is reported, not a bare point), missing cells surface in
`coverage` (never silently dropped), the token-saving win is significant, the axiom condition is Pareto-
dominant on cost×quality, and the §5 build break-even stays the honest negative (N*=∞). Runs on the FROZEN
guaranteed-cached subset so it is deterministic regardless of any background fixture population."""
from __future__ import annotations

from backend.app.axiom_gain_protocol import PROTO_MODELS, run_protocol

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


def test_h2_capability_vs_gain_axis():
    # PREREG H2: ordering models by capability (naive-RAG F1), the QUALITY gain shrinks while the TOKEN saving
    # stays structural-flat. On the existing 8B–31B matrix the trend is observed (not pre-registered).
    r = _run()
    h2 = r["h2_capability_vs_gain"]
    rows = h2["by_capability_ascending"]
    assert [round(rows[i]["capability_naive_f1"], 4) for i in range(len(rows))] == sorted(
        round(x["capability_naive_f1"], 4) for x in rows)            # rows are ascending in capability
    assert "naive-RAG F1" in h2["capability_proxy"]
    # token saving is structural (context size) ⇒ ~model-independent (flat spread)
    assert h2["token_saving_is_structural_flat(<0.05)"] is True
    assert isinstance(h2["quality_gain_monotone_decreasing"], bool)  # the H2a flag is present + reproducible


def test_h2_frontier_run_directional_not_monotone():
    # PREREG H2, RUN: adding the 4th model (qwen3.6-35b-a3b) keeps the DIRECTIONAL trend (Spearman < 0) but
    # BREAKS strict monotonicity — and it isn't actually a frontier point (naive F1 below gemma-31b). Honest
    # result reported, not pruned. Deterministic from the committed fixtures.
    h2 = run_protocol(models=PROTO_MODELS + ["qwen/qwen3.6-35b-a3b"])["h2_capability_vs_gain"]
    rows = {r["model"]: r for r in h2["by_capability_ascending"]}
    assert "qwen/qwen3.6-35b-a3b" in rows
    assert h2["spearman_capability_gain"] is not None and h2["spearman_capability_gain"] < -0.5  # direction holds
    assert h2["quality_gain_monotone_decreasing"] is False                       # ...but the 4th point breaks monotone
    # the candidate is NOT actually more capable than gemma-31b on this task (so it didn't probe the frontier)
    assert rows["qwen/qwen3.6-35b-a3b"]["capability_naive_f1"] < rows["google/gemma-4-31b-qat"]["capability_naive_f1"]
    assert h2["token_saving_is_structural_flat(<0.05)"] is True                   # H2b: token saving stays flat


def test_h2_frontier_manual_is_flagged_and_never_merged():
    # OBSERVER §15 P1 / money-moment visual: the genuine-frontier GPT-5.5 point is a Tier-2 disclosed MANUAL
    # measurement — it must be a frozen recorded constant, flagged non-reproducible, NEVER merged into the
    # reproducible series, with the registered Confirm verdict RECOMPUTED live (not a stored literal that could
    # drift if fixtures shift). Deterministic on the frozen subset.
    r = _run()
    fm = r["h2_capability_vs_gain"]["frontier_manual"]
    rows = r["h2_capability_vs_gain"]["by_capability_ascending"]
    assert fm is not None
    assert fm["reproducible"] is False                       # the disclosure flag that keeps /protocol honest
    assert fm["capability_naive_f1"] == 0.95 and fm["quality_gain"] == 0.0
    assert fm["token_saving"] is None                        # no token counts from the web UI ⇒ H2b unmeasured for it
    assert "浏览器抓取" in fm["caveat"] and "未冻结为 fixture" in fm["caveat"]
    # the Confirm verdict is computed from the LIVE most-capable row, not stored — pin the two together so it
    # can never silently contradict the arithmetic
    assert fm["confirm_comparator_model"] == rows[-1]["model"]
    assert fm["confirm_comparator_gain"] == rows[-1]["quality_gain"]
    assert fm["confirm_rule_met"] == (fm["quality_gain"] <= rows[-1]["quality_gain"])
    # NEVER merged into the reproducible series (the array stays all-reproducible models)
    assert "gpt-5.5" not in {row["model"] for row in rows}


def test_frontier_confirm_rule_is_computed_both_branches():
    # the registered Confirm rule is COMPUTED live, not a stored literal. The fixtures only ever hit the True
    # branch (comparator gain +0.108 > 0), so the integration assertion above can't tell a hardcoded `True` from
    # the live computation — pin the pure rule fn on BOTH branches so a stored literal would fail the False case.
    from backend.app.axiom_gain_protocol import _FRONTIER_GAIN, _frontier_confirms
    assert _frontier_confirms(_FRONTIER_GAIN, [{"quality_gain": 0.108}]) is True    # 0.0 ≤ 0.108
    assert _frontier_confirms(_FRONTIER_GAIN, [{"quality_gain": -0.05}]) is False   # a stored True would FAIL here
    assert _frontier_confirms(_FRONTIER_GAIN, []) is False                          # no rows ⇒ unconfirmed, not a crash


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
    # default H2 axis is the 3 PROTO_MODELS (the headline-driving set) — the extra points NOT silently folded in;
    # every default row is a LOCAL ($0, strict-schema) provenance
    rows0 = body["h2_capability_vs_gain"]["by_capability_ascending"]
    default_h2 = {r["model"] for r in rows0}
    assert "qwen/qwen3.6-35b-a3b" not in default_h2 and "deepseek-v4-pro-260425" not in default_h2 and len(default_h2) == 3
    assert all(r["provenance"]["source"] == "local" for r in rows0)
    # include_h2_extra=true surfaces BOTH off-default points: the qwen3.6 interior wobble (breaks strict monotone,
    # Spearman > −1) AND the deepseek API frontier (flagged api-paid/prompt-json, never silently mixed) — DON'T #4
    h2b = client.get("/api/axiomgain/logistics_demo/protocol?include_h2_extra=true").json()["h2_capability_vs_gain"]
    by = {r["model"]: r for r in h2b["by_capability_ascending"]}
    assert "qwen/qwen3.6-35b-a3b" in by and "deepseek-v4-pro-260425" in by
    assert h2b["quality_gain_monotone_decreasing"] is False           # the wobble is visible, not pruned
    assert h2b["spearman_capability_gain"] is not None and -1.0 < h2b["spearman_capability_gain"] < 0
    # the API point is flagged (reproducible from fixtures, but $≠0-to-freeze + prompt-JSON). HONEST finding:
    # over the FULL grid its task-competence is ~TIED with gemma-31b (NOT "more capable" — the dirt-0.6 slice
    # alone overstated it); it is a cross-model CORROBORATION + a real-API H2b measurement, not a frontier point
    ds = by["deepseek-v4-pro-260425"]
    g31 = by["google/gemma-4-31b-qat"]
    assert ds["provenance"]["source"] == "ark-api" and ds["provenance"]["structured"] == "prompt-json"
    assert ds["provenance"]["reproducible"] is True                         # frozen ⇒ $0 to serve, reproducible
    assert abs(ds["capability_naive_f1"] - g31["capability_naive_f1"]) < 0.03  # TIED with gemma-31b, not beyond it
    assert 0.4 < ds["token_saving"] < 0.8                                   # the structural ~60% saving holds on a real API
    assert client.get("/api/axiomgain/nope/protocol").status_code == 404   # missing source → 404 (mirrors ablation)
