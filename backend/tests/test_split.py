"""split-from-shared-latent substrate (DESIGN_data_package §11). Pins the §11 honesty guards: deterministic;
honest SPARSITY (few twins, most entities domain-private); NON-LEAKY variant transform (latent id never in
the public view, disjoint cross-domain vocab, a twin's rendered numerics differ, surface/value matchers ~
chance); and WELL-POSED (oracle recovers, semantic matcher solvable). The coupling is known-truth but
constructed — these tests pin that the *construction* is honest, not that the coupling is externally real."""
from __future__ import annotations

from backend.app.data_package_split import (
    DOMAINS_SPLIT,
    SPLIT_KNOBS,
    generate_split,
    public_view,
)
from backend.app.split_gate import run_split_gate


def test_deterministic():
    assert generate_split("sp-3") == generate_split("sp-3")
    assert run_split_gate(["sp-0", "sp-1"]) == run_split_gate(["sp-0", "sp-1"])


def test_honest_sparsity_most_entities_are_domain_private():
    g = generate_split("sp-0")
    n_a, n_b, n_twin = len(g["A"]["units"]), len(g["B"]["units"]), len(g["twin_map"])
    # twins are a small fraction; the candidate space A×B dwarfs the true positives (a discriminability interval)
    assert n_twin == max(1, round(SPLIT_KNOBS["n_entities"] * SPLIT_KNOBS["twin_frac"]))
    assert n_twin < 0.10 * (n_a * n_b)
    # most entities are domain-private: total rendered records = n_entities + n_twin (twins rendered twice)
    assert n_a + n_b == SPLIT_KNOBS["n_entities"] + n_twin


def test_public_view_leaks_no_latent_truth():
    g = generate_split("sp-1")
    pv = public_view(g)
    assert "twin_map" not in pv and "_world" not in pv
    for u in pv["A"]["units"] + pv["B"]["units"]:
        assert not any(k.startswith("_") for k in u)          # no eval-only latent fields reach a consumer


def test_variant_transform_structural_facts():
    g = generate_split("sp-2")
    A, B = g["A"]["units"], g["B"]["units"]
    af, bf = DOMAINS_SPLIT["A"]["fields"]["attr"], DOMAINS_SPLIT["B"]["fields"]["attr"]
    # disjoint cross-domain vocab (class + tags) — note: disjoint vocab ALONE is not the non-leak proof (a raw
    # string match is then tautologically ~chance); the real proof is the adversarial gate below.
    assert not (set(DOMAINS_SPLIT["A"]["cls_vocab"]) & set(DOMAINS_SPLIT["B"]["cls_vocab"]))
    assert not (set(DOMAINS_SPLIT["A"]["tag_vocab"]) & set(DOMAINS_SPLIT["B"]["tag_vocab"]))
    # a true twin's rendered numerics DIFFER across domains (per-domain units + noise) — no shared key
    for ai, bi in g["twin_map"]:
        assert A[ai][af] != B[bi][bf]
        assert A[ai]["_lid"] == B[bi]["_lid"]                  # but they ARE the same latent entity (oracle truth)


def test_diagonal_id_leak_is_closed():
    # OBSERVER §13 HIGH leak #1: before the fix, twins were rendered as a perfect diagonal (a_idx==b_idx), so
    # an id-index matcher on the PUBLIC view recovered them at AUC 0.991. Independent per-domain shuffles fix it.
    for sd in ("sp-0", "sp-5", "sp-9"):
        tm = generate_split(sd)["twin_map"]
        assert sum(1 for a, b in tm if a == b) < len(tm)       # NOT all on the diagonal
    r = run_split_gate()
    assert r["adversarial_matcher_auc"]["idx_index"] <= 0.60   # the id-index matcher is now ~chance


def test_vocab_index_alignment_leak_is_closed():
    # OBSERVER §13 HIGH leak #2: before the fix, A.vocab[i] and B.vocab[i] encoded the same latent class, so a
    # vocab-POSITION matcher bridged at AUC 0.9999. Independent per-domain vocab permutations fix it.
    r = run_split_gate()
    assert r["adversarial_matcher_auc"]["vocab_pos"] <= 0.60   # the vocab-position matcher is now ~chance


def test_gate_well_posed_and_non_leaky():
    r = run_split_gate()
    assert r["checks"]["oracle_recovers(>=0.95)"] is True       # the truth is there
    # the REAL non-leak proof: every INFORMED adversarial matcher (not a rigged raw-string one) is ~chance
    assert r["checks"]["idx_index_match_chance(0.40-0.60)"] is True
    assert r["checks"]["vocab_position_match_chance(0.40-0.60)"] is True
    assert r["checks"]["value_match_chance(0.40-0.60)"] is True
    assert r["checks"]["semantic_solvable(>=0.80)"] is True     # a z-scored semantic matcher recovers
    assert r["checks"]["positives_sparse(<0.10)"] is True       # twins sparse among candidates
    assert r["twins_with_identical_rendered_attrs"] == 0        # no numeric leak
    assert r["gate_pass"] is True


def test_api_split():
    from fastapi.testclient import TestClient

    from backend.app.main import app

    client = TestClient(app)
    v = client.get("/api/split/view?seed=sp-0")
    assert v.status_code == 200
    body = v.json()
    assert "A" in body and "B" in body and "twin_map" not in body
    gate = client.get("/api/split/gate?seeds=12")
    assert gate.status_code == 200 and gate.json()["gate_pass"] is True
    assert client.get("/api/split/gate?seeds=99999").json()["seeds"] <= 100   # unbounded-compute guard (clamp)
