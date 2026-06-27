"""§5 build-cost amortization — the invariants of the honest result: the learning machinery is correct
(mines a dictionary, reaches algorithmic PARITY) yet its accuracy benefit is 0, so the gain lives in the
build-free structural axioms (exclusivity + compaction). Plus determinism, the held-out boundary (no
train leak), and that generalizing the deterministic join did NOT disturb the frozen logistics fixtures."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.app import axiom_layer
from backend.app.amortization import run_amortization
from backend.app.axiom_learn import estimate_tokens, learned_canon
from backend.app.benchmark import run_ablation
from backend.app.main import app

client = TestClient(app)


def _canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def test_deterministic_byte_identical():
    assert _canon(run_amortization()) == _canon(run_amortization())


def test_refuses_train_eval_leak():
    # the held-out boundary is the whole point — a shared seed must be refused, not silently amortized
    r = run_amortization(train_seeds=["ho-0", "tr-1"], eval_seeds=["ho-0", "ho-1"])
    assert r["ok"] is False and "leak" in r["error"]


def test_refuses_zero_dirt():
    # aliases (the learned thing) only exist under dirtiness; amortizing at dirt=0 is meaningless
    assert run_amortization(dirt=0.0)["ok"] is False


def test_learner_reaches_algorithmic_parity():
    # the learned dictionary, at convergence, matches the shipped algorithmic layer on held-out — so a
    # 0 benefit below is a property of the TASK, not a broken learner.
    b = run_amortization()["learned_build"]
    assert b["parity_with_algorithmic"]["equal"] is True
    assert b["parity_with_algorithmic"]["learned_converged_f1"] == b["parity_with_algorithmic"]["algorithmic_f1"]


def test_value_is_in_buildfree_structure_not_learned_dictionary():
    # THE HONEST HEADLINE: build-free STRUCTURAL axioms (exclusivity + anomaly-frame anchoring +
    # time-primary scoring, together) carry the gain; the learned dictionary adds 0 at every dirtiness,
    # so it does not amortize on accuracy.
    d = run_amortization()["value_decomposition"]
    assert d["structural_gain_buildfree"] > 0.1            # basic linked → axiom: a real, free gain
    assert d["learned_dictionary_gain"] == 0.0              # the part with a build cost buys nothing
    assert d["axiom_empty_dict_f1"] == d["axiom_full_dict_f1"]
    assert all(row["dictionary_delta"] == 0.0 for row in d["dictionary_benefit_dirt_sweep"])


def test_compression_is_build_free():
    # the per-query token saving is available with an EMPTY dictionary (build≈0) — so compaction needs
    # no learning either.
    c = run_amortization()["compression_buildfree"]
    assert c["axiom_empty_dict_tok_est"] == c["axiom_full_dict_tok_est"]
    assert c["axiom_full_dict_tok_est"] < c["naive_tok_est"]   # axiom context is genuinely more compact
    assert c["saving_per_query_est"] > 0


def test_breakeven_dictionary_never_amortizes():
    bk = run_amortization()["breakeven"]
    assert bk["dictionary_amortizes_on_accuracy"] is False
    assert bk["breakeven_N_dictionary"] is None


def test_learning_curve_monotone():
    rounds = run_amortization()["rounds"]
    cov = [r["heldout_alias_coverage"] for r in rounds]
    build = [r["cum_build_tokens"] for r in rounds]
    assert cov == sorted(cov)                                  # coverage non-decreasing
    assert build == sorted(build) and build[0] > 0            # build cost strictly accumulates
    assert sum(r["new_aliases"] for r in rounds) == rounds[-1]["aliases_known"]


def test_estimate_tokens_deterministic_and_sane():
    assert estimate_tokens("") == 0
    assert estimate_tokens("台风封港 WH-001") == estimate_tokens("台风封港 WH-001")
    assert estimate_tokens("台风封港封港封港") > estimate_tokens("台风")  # more CJK → more tokens


def test_learned_canon_resolves_known_leaves_unknown():
    m = {"華東": "华东", "HD": "华东"}
    assert learned_canon("華東封港", m) == "华东封港"
    assert learned_canon("HD港区", m) == "华东港区"
    assert learned_canon("华北区", m) == "华北区"                # not in the learned map → untouched


def test_resolve_refactor_preserved_logistics_fixtures():
    # generalizing axiom_layer._resolve to read stores by ROLE must leave the logistics axiom_context —
    # and therefore the frozen ablation fixtures — byte-identical (all cached, no live call).
    assert run_ablation("logistics_demo")["all_cached"] is True


def test_api_amortization_both_domains_and_404():
    a = client.get("/api/axiomgain/logistics_demo/amortization")
    assert a.status_code == 200
    body = a.json()
    assert body["value_decomposition"]["learned_dictionary_gain"] == 0.0
    assert body["compression_buildfree"]["metered_crosscheck"] is not None   # logistics has fixtures

    e = client.get("/api/axiomgain/energy_demo/amortization")
    assert e.status_code == 200
    ebody = e.json()
    assert ebody["value_decomposition"]["learned_dictionary_gain"] == 0.0    # same honest result, 2nd domain
    assert ebody["compression_buildfree"]["metered_crosscheck"] is None      # energy ablation deferred → no fixtures

    assert client.get("/api/axiomgain/nope/amortization").status_code == 404
