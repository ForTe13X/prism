"""Axiom-gain ablation (DP2). The LLM-dependent figures are read from the FROZEN fixtures committed in
backend/benchmark_fixtures/ (no live model), so these run deterministically in CI. The deterministic
axiom layer + context builders are tested directly. The headline invariants asserted here are the real,
non-tautological result: axiom-RAG ≥ naive-RAG quality at FEWER input tokens, and the gain grows with
dirtiness."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import llm_client
from backend.app.axiom_layer import axiom_context, canon, naive_context
from backend.app.benchmark import _manifest, _parse, run_ablation
from backend.app.data_package import generate
from backend.app.data_package_eval import observation_view, oracle_solve, score
from backend.app.main import app

client = TestClient(app)


def test_canon_folds_aliases_to_canonical():
    assert canon("華東") == "华东" and canon("华东区") == "华东" and canon("HD") == "华东"


def test_axiom_layer_resolves_and_is_dirt_robust():
    from backend.app.axiom_layer import _resolve

    seeds = ["ho-0", "ho-1", "ho-2", "ho-3"]
    def mean_f1(d):
        vals = []
        for sd in seeds:
            pkg = generate("logistics_demo", dirtiness=d, link_explicitness=4, seed=sd)
            obs, truth = observation_view(pkg), oracle_solve(pkg, "explain_delays")
            vals.append(score({f["news_id"]: f["shipment_ids"] for f in _resolve(obs)}, truth)["f1"])
        return sum(vals) / len(vals)

    assert mean_f1(0.0) == 1.0          # clean: the canonical resolver is exact
    assert mean_f1(0.6) >= 0.8          # dirty: degrades gracefully, stays strong (robustness)


def test_resolve_assigns_each_news_to_at_most_one_warehouse():
    # exclusivity: even when two anomalies coincide in time, one news is never attributed to two
    # warehouses (no over-claim) — checked across many seeds incl. dirt-shifted frames
    from backend.app.axiom_layer import _resolve

    for i in range(40):
        for d in (0.0, 0.3, 0.6):
            obs = observation_view(generate("logistics_demo", dirtiness=d, link_explicitness=4, seed=f"uq-{i}"))
            ids = [f["news_id"] for f in _resolve(obs)]
            assert len(ids) == len(set(ids))


def test_axiom_context_is_more_compact_than_naive():
    obs = observation_view(generate("logistics_demo", dirtiness=0.0, link_explicitness=4, seed="ho-0"))
    n, a = naive_context(obs), axiom_context(obs)
    assert n and a and len(a) < len(n)  # pre-joined facts are smaller than the raw stores


def test_parse_answer_json():
    assert _parse('{"answer":[{"news_id":"NEWS-002","shipment_ids":["SHP-0005","SHP-0019"]}]}') == {
        "NEWS-002": ["SHP-0005", "SHP-0019"]
    }
    assert _parse("not json") == {}


def test_structured_complete_requires_fixture_when_offline():
    r = llm_client.structured_complete("sys", "an unseen prompt that has no fixture", {"name": "x", "schema": {}},
                                       model="m", allow_live=False)
    assert r["ok"] is False  # no fixture + no live → observable miss, never fabricated


def test_ablation_from_fixtures_is_reproducible_and_axiom_wins():
    assert _manifest().get("models"), "frozen manifest must exist (run the ablation to populate fixtures)"
    r = run_ablation()  # no args → manifest + fixtures, no live model
    assert r["ok"] and r["all_cached"]
    by = {(c["model"], c["dirtiness"], c["condition"]): c for c in r["conditions"]}
    for (model, dirt, cond), c in by.items():
        if cond != "axiom-RAG":
            continue
        naive = by[(model, dirt, "naive-RAG")]
        assert c["quality_f1"] >= naive["quality_f1"]          # equal-or-better quality
        assert c["avg_in_tok"] < naive["avg_in_tok"]           # at fewer input tokens
    assert r["gains"] and all(g["quality_delta"] >= 0 and g["input_token_ratio"] < 1 for g in r["gains"])


def test_ablation_gain_grows_with_dirtiness():
    r = run_ablation()
    g = {(x["model"], x["dirtiness"]): x["quality_delta"] for x in r["gains"]}
    # for at least one model the axiom advantage is larger under dirt than clean (robustness)
    assert any(g.get((m, 0.6), 0) > g.get((m, 0.0), 0) for m in {k[0] for k in g})


def test_api_axiomgain():
    r = client.get("/api/axiomgain/logistics_demo")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] and body["conditions"] and body["gains"] and body["all_cached"]
    assert client.get("/api/axiomgain/nope").status_code == 404
