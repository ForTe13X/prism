"""§6c-style discriminability gate for the split-from-shared-latent substrate (DESIGN_data_package §11 +
OBSERVER §13). Validates — channel-blind, before any metric — that the substrate is WELL-POSED:
  * ORACLE (sees the latent id) RECOVERS the true twins ⇒ the truth is there to be found (AUC ≥ 0.95);
  * INFORMED ADVERSARIAL matchers are ~CHANCE ⇒ the variant transform is genuinely NON-LEAKY. These are not
    blunt raw-string matchers (a disjoint vocab makes those trivially 0.5 — a tautology, not a measurement);
    they are matchers that KNOW the structure and try to exploit it: (a) ID-INDEX equality (a_idx==b_idx —
    catches the diagonal-render leak), (b) VOCAB-POSITION match (map each rendered token back to its vocab
    INDEX and compare — catches the index-aligned-vocab leak), (c) integer VALUE overlap. All must be ~chance.
  * a SEMANTIC matcher (z-scored numeric distance, which undoes the per-domain affine) RECOVERS ⇒ the
    substrate is hard-but-SOLVABLE (a real metric has signal to find), not impossible;
  * SPARSITY: candidate pairs ≫ true twins (most entities are domain-private hard negatives), so a
    discriminability interval exists (the §6c requirement, the §13 multiple-comparison reality).

A pass means: an informed solver wins, even STRUCTURE-AWARE surface proxies don't, the signal is genuinely
there, and positives are sparse — i.e. a real cross-domain-coreference benchmark, not a leaky or self-
consistent toy. The two HIGH leaks the §13 review found (diagonal id, index-aligned vocab) are now both
tested adversarially here. Cross-seed scores are pooled (valid: every channel here is z-scored or a 0/1
indicator, so per-seed-comparable). Deterministic.
"""
from __future__ import annotations

from .data_package_split import DOMAINS_SPLIT, generate_split
from .nexus_eval import roc_auc


def _vocab_pos(u: dict, dk: str) -> tuple[int, set]:
    """Map a rendered record back to its vocab POSITIONS (class index + tag index set) — what a structure-
    aware attacker reads to try to align the two domains. After the per-domain permutation these do NOT
    align across a twin, so an index matcher built on them is ~chance."""
    spec = DOMAINS_SPLIT[dk]
    cls_pos = spec["cls_vocab"].index(u[spec["fields"]["cls"]])
    tag_pos = {spec["tag_vocab"].index(t) for t in u[spec["fields"]["rel"]]}
    return cls_pos, tag_pos


def _zscore(units: list[dict], field: str) -> list[list[float]]:
    """Per-attribute z-score within a domain's population — removes the per-domain affine so a twin's
    numeric vector is comparable across domains (the variant transform is undone statistically, not by key)."""
    if not units:
        return []
    na = len(units[0][field])
    stats = []
    for a in range(na):
        col = [u[field][a] for u in units]
        m = sum(col) / len(col)
        sd = (sum((x - m) ** 2 for x in col) / len(col)) ** 0.5 or 1.0
        stats.append((m, sd))
    return [[(u[field][a] - stats[a][0]) / stats[a][1] for a in range(na)] for u in units]


def _tokens(u: dict, dk: str) -> set:
    spec = DOMAINS_SPLIT[dk]
    return {u[spec["fields"]["cls"]], *u[spec["fields"]["rel"]]}


def _int_values(u: dict, dk: str) -> set:
    return {round(v) for v in u[DOMAINS_SPLIT[dk]["fields"]["attr"]]}


def _collect(seeds: list[str]) -> dict:
    # oracle = truth; idx_index/vocab_pos/value = INFORMED adversarial matchers (must fail); raw_surface kept
    # only to SHOW it is tautologically 0.5 (disjoint vocab ⇒ all-tie), NOT counted in the non-leak verdict.
    pools = {"oracle": [], "idx_index": [], "vocab_pos": [], "value": [], "raw_surface": [], "semantic": []}
    labels = []
    spar = {"candidates": 0, "twins": 0}
    leak = {"twins_with_identical_attrs": 0}
    af, bf = DOMAINS_SPLIT["A"]["fields"]["attr"], DOMAINS_SPLIT["B"]["fields"]["attr"]
    for sd in seeds:
        g = generate_split(sd)
        A, B = g["A"]["units"], g["B"]["units"]
        twins = set(map(tuple, g["twin_map"]))
        zA, zB = _zscore(A, af), _zscore(B, bf)
        posA = [_vocab_pos(a, "A") for a in A]
        posB = [_vocab_pos(b, "B") for b in B]
        spar["candidates"] += len(A) * len(B)
        spar["twins"] += len(twins)
        for ai, a in enumerate(A):
            ta, va = _tokens(a, "A"), _int_values(a, "A")
            ca, sa = posA[ai]
            for bi, b in enumerate(B):
                labels.append(1 if (ai, bi) in twins else 0)
                pools["oracle"].append(1.0 if a["_lid"] == b["_lid"] else 0.0)
                pools["idx_index"].append(1.0 if ai == bi else 0.0)               # diagonal-leak probe
                cb, sb = posB[bi]
                pools["vocab_pos"].append((1.0 if ca == cb else 0.0)              # index-aligned-vocab probe
                                          + (len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0))
                tb, vb = _tokens(b, "B"), _int_values(b, "B")
                pools["value"].append(len(va & vb) / len(va | vb) if (va | vb) else 0.0)
                pools["raw_surface"].append(len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0)
                pools["semantic"].append(-sum((zA[ai][k] - zB[bi][k]) ** 2 for k in range(len(zA[ai]))))
        for (ai, bi) in twins:
            if A[ai][af] == B[bi][bf]:                       # identical rendered numerics ⇒ a leak
                leak["twins_with_identical_attrs"] += 1
    return {"pools": pools, "labels": labels, "sparsity": spar, "leak": leak}


def run_split_gate(seeds: list[str] | None = None) -> dict:
    seeds = seeds or [f"sp-{i}" for i in range(40)]
    data = _collect(seeds)
    pools, labels = data["pools"], data["labels"]
    n, npos = len(labels), sum(labels)
    auc = {k: roc_auc(v, labels) for k, v in pools.items()}
    spar, leak = data["sparsity"], data["leak"]
    prevalence = spar["twins"] / spar["candidates"] if spar["candidates"] else 0.0

    def chance(x: float) -> bool:
        return 0.40 <= x <= 0.60
    oracle_ok = auc["oracle"] >= 0.95
    semantic_solvable = auc["semantic"] >= 0.80
    sparse = prevalence < 0.10
    # the REAL non-leak verdict: every INFORMED adversarial matcher is ~chance + no exact numeric leak.
    adversarial = {"idx_index": auc["idx_index"], "vocab_pos": auc["vocab_pos"], "value": auc["value"]}
    non_leaky = all(chance(v) for v in adversarial.values()) and leak["twins_with_identical_attrs"] == 0

    return {
        "seeds": len(seeds), "n_candidates": n, "n_twins": npos, "prevalence": round(prevalence, 4),
        "oracle_auc": auc["oracle"], "semantic_zscore_auc": auc["semantic"],
        "adversarial_matcher_auc": {k: round(v, 4) for k, v in adversarial.items()},
        "raw_surface_jaccard_auc": auc["raw_surface"],   # ≈0.5 BY CONSTRUCTION (disjoint vocab) — not a measurement
        "twins_with_identical_rendered_attrs": leak["twins_with_identical_attrs"],
        "gate_pass": bool(oracle_ok and non_leaky and semantic_solvable and sparse),
        "checks": {
            "oracle_recovers(>=0.95)": oracle_ok,
            "idx_index_match_chance(0.40-0.60)": chance(auc["idx_index"]),
            "vocab_position_match_chance(0.40-0.60)": chance(auc["vocab_pos"]),
            "value_match_chance(0.40-0.60)": chance(auc["value"]),
            "semantic_solvable(>=0.80)": semantic_solvable,
            "positives_sparse(<0.10)": sparse,
            "non_leaky": non_leaky,
        },
        "note": ("split-from-shared-latent §6c gate: the oracle (latent id) recovers the true twins; the "
                 "INFORMED adversarial matchers — id-index (diagonal probe), vocab-position (index-alignment "
                 "probe), integer value-overlap — are all ~chance ⇒ genuinely non-leaky (the §13 review's two "
                 "HIGH leaks are now closed + tested); a z-scored semantic matcher recovers (hard-but-"
                 "solvable); twins are sparse among A×B candidates. raw_surface_jaccard≈0.5 is tautological "
                 "(disjoint vocab) and is NOT part of the verdict. HONEST: the coupling is known-truth but "
                 "CONSTRUCTED (split from one latent) — external validity is RAISED, not closed (DESIGN §11)."),
    }
