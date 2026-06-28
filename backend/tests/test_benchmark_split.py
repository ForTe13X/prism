"""Axiom-gain on the split substrate (DESIGN_data_package §11b): the deterministic resolver + the naive vs
axiom contexts + the cached LLM ablation. Pins: the resolver recovers twins from the PUBLIC view (no oracle);
the axiom context is compact and carries the answer while naive carries both raw domains; the ablation runs
from frozen fixtures and axiom-RAG is at least as good as naive-RAG at fewer tokens; and the honest bound
(axiom-RAG quality ≤ resolver accuracy) is surfaced."""
from __future__ import annotations

from backend.app.axiom_split import (
    axiom_context_split,
    naive_context_split,
    oracle_answer_split,
    resolve_twins,
    resolver_accuracy,
)
from backend.app.benchmark_split import run_split_ablation
from backend.app.data_package_split import DOMAINS_SPLIT, generate_split, public_view

SEEDS = [f"sp-{i}" for i in range(8)]
_B_REL = DOMAINS_SPLIT["B"]["fields"]["rel"]


def test_resolver_recovers_twins_from_public_view_only():
    # the resolver uses ONLY public_view (no _* latents); it is deterministic and reasonably accurate
    g = generate_split("sp-0")
    pub = public_view(g)
    assert all(not any(k.startswith("_") for k in u) for u in pub["A"]["units"])   # truly public input
    acc = resolver_accuracy(SEEDS)
    assert acc["link_precision"] >= 0.6 and acc["link_recall"] >= 0.6
    assert acc["answer_f1_mean"] >= 0.5
    assert resolve_twins(pub) == resolve_twins(pub)                                # deterministic


def test_oracle_answer_matches_twin_map():
    g = generate_split("sp-1")
    truth = oracle_answer_split(g)
    A, B = g["A"]["units"], g["B"]["units"]
    assert len(truth) == len(g["twin_map"])
    for ai, bi in g["twin_map"]:
        assert truth[A[ai]["id"]] == sorted(B[bi][_B_REL])


def test_axiom_context_is_compact_naive_has_both_domains():
    pub = public_view(generate_split("sp-2"))
    naive, axiom = naive_context_split(pub), axiom_context_split(pub)
    assert "[A 域记录]" in naive and "[B 域记录]" in naive       # naive dumps both raw domains
    assert "≡" in axiom                                          # axiom shows resolved twin links
    assert len(axiom) < len(naive)                              # axiom is the compact, pre-joined context


def test_ablation_from_fixtures_axiom_enables_task_at_fewer_tokens():
    r = run_split_ablation()                                     # fixtures only (allow_live defaults False)
    assert r["ok"] is True
    idx = {(c["model"], c["condition"]): c for c in r["conditions"]}
    res_f1 = r["resolver_accuracy"]["answer_f1_mean"]
    for g in r["gains"]:
        nv, ax = idx[(g["model"], "naive-RAG")], idx[(g["model"], "axiom-RAG")]
        assert ax["quality_f1"] >= nv["quality_f1"]            # axiom at least as good on quality
        assert g["input_token_saving"] > 0.0                  # and cheaper (compact resolved context)
        assert ax["quality_f1"] <= res_f1 + 0.005             # axiom-RAG quality cannot exceed the resolver ceiling
        assert isinstance(ax["truncated_calls"], int)         # truncation is SURFACED (not hidden) for every cond
    # the FAITHFUL primary result (qwen) must be truncation-CLEAN — so qwen's 0.656 is real capability, not a
    # harness cap artifact (the §11b defect the review caught). gemma legitimately over-generates and may truncate.
    qwen_ax = idx[("qwen-3-8b-instruct", "axiom-RAG")]
    assert qwen_ax["truncated_calls"] == 0
    # NON-VACUOUS enablement: qwen is genuinely enabled (axiom-RAG ≫ 0 AND a large positive gain over naive≈0),
    # so the test cannot pass with axiom collapsing to ~0 everywhere.
    assert qwen_ax["quality_f1"] > 0.3
    assert next(g["quality_delta"] for g in r["gains"] if g["model"] == "qwen-3-8b-instruct") > 0.3


def test_api_ablation():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    res = client.get("/api/split/ablation")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True and "gains" in body and "resolver_accuracy" in body
