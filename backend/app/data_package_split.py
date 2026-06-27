"""split-from-shared-latent substrate (DESIGN_data_package §11) — deterministic, clean-room.

The Phase-B substrate (`data_package_xdom`) injects THREE *disjoint* latents into two domains; its honest gap
(OBSERVER §11/§12) is that the coupling is a designed artifact and the headline 3-way convergence collapses
under real-calibrated noise (Track 1). This substrate is the richer, more honest stage the design anchor asks
for: build ONE latent world (a small known-truth KG of entities), then SPLIT it into two domains so a true
cross-domain twin shares the SAME underlying entity across all channels — genuinely coupled, not three
separately-injected signals. Per the §11 verdict this RAISES, does NOT close, external validity: the coupling
is now realistic + known-truth, but still constructed (splitting one latent), so it is labelled known-not-
verified. Its cleaner consumer is axiom-gain (cross-domain entity resolution), not the capped nexus metric.

The four §11 operations + their fatal traps, each guarded here:
  * SPLIT defines the ground-truth twins — only a SMALL fraction get a twin; most entities are domain-private
    (honest sparsity; splitting everything = the "too self-consistent" artifact). → ``twin_frac`` small,
    asserted sparse.
  * VARIANT TRANSFORM makes the same entity LOOK different across domains (per-domain unit scale/offset +
    noise on numerics; disjoint vocab on categories/relations; different field names) — so the shared
    identity is NOT recoverable by a surface match. Trap: a reversible/leaky transform ⇒ trivially detectable.
    Guards (hardened after the OBSERVER §13 review caught two real leaks): (1) the latent id is never
    rendered and the affine params are not rendered; (2) per-domain noise breaks exact numeric match;
    (3) the two domains' unit orders are INDEPENDENTLY shuffled, so a twin's (a_idx,b_idx) are uncorrelated
    (else the rendered id index is a diagonal that leaks the twin map); (4) each domain renders categories
    through its OWN vocab permutation, so the surface vocab POSITION does not align across domains (else an
    index-aligned matcher bridges trivially). The gate now verifies INFORMED adversarial matchers (id-index,
    vocab-position, value-overlap) — not just a raw disjoint-string matcher — are ~chance.
  * DATA MIXING injects domain-private distractors + noise ⇒ hard negatives + real sparsity (the §6c
    discriminability interval). Guard: candidate pairs ≫ true twins.
  * LLM REFINE (the surface realizer) is NOT used here — the core is deterministic templating. Honest
    tradeoff: no "single LLM-voice fingerprint" leak (the §11 trap), but lower surface realism. An optional
    LLM surface layer is future work, never the truth source.

Deterministic: reuses ``data_synth._unit`` (sha256 → [0,1]); no ``random``, no clock. Clean-room: Prism's own
code; the latent-KG-first *concept* is the author's own SyntheticData design (generic, no former-employer IP).
"""
from __future__ import annotations

from .data_synth import _unit

SPLIT_KNOBS = {
    "n_entities": 48,     # latent-world size (the known-truth KG)
    "twin_frac": 0.25,    # fraction of entities that get a cross-domain twin (the rest are domain-private)
    "n_attr": 4,          # continuous latent attributes → the NUMERIC channel
    "n_classes": 8,       # latent categorical class → the FINGERPRINT channel (index-aligned, disjoint vocab)
    "n_rel_tags": 12,     # relational neighbour-class vocabulary → the RELATIONAL channel
    "rel_pick": 4,        # relational tags per entity
    "noise": 0.20,        # per-domain rendering noise (fraction of the attr's own scale) — breaks exact match
}

# per-domain AFFINE render of each latent attribute: vX = scale[a]·v + off[a] + noise. Different units/offsets
# per (domain, attr) ⇒ the rendered numbers look unrelated; z-scoring within a domain removes the affine, so
# a SEMANTIC matcher recovers the twin while an exact/surface matcher cannot. These params are NOT rendered.
DOMAINS_SPLIT = {
    "A": {"prefix": "AX", "fields": {"attr": "metric", "cls": "category", "rel": "tags"},
          "scale": [10.0, 100.0, 5.0, 2.20462], "off": [50.0, 200.0, 0.0, 10.0],
          "cls_vocab": ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"],
          "tag_vocab": ["rack", "zone", "pdu", "vlan", "blade", "psu", "nic", "bmc", "tor", "spine", "leaf", "core"]},
    "B": {"prefix": "BQ", "fields": {"attr": "value", "cls": "kind", "rel": "labels"},
          "scale": [3.0, 0.5, 8.0, 1.0], "off": [1.0, 5.0, 20.0, 0.0],
          "cls_vocab": ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho"],
          "tag_vocab": ["fiction", "poetry", "drama", "essay", "atlas", "manual", "score", "folio", "codex", "scroll", "quire", "vellum"]},
}


def _u(seed: str, *parts: object) -> float:
    return _unit(seed, *(str(p) for p in parts))


def _latent_world(seed: str) -> list[dict]:
    """The known-truth KG: ``n_entities`` latent entities, each with a continuous attr vector, a categorical
    class, and a relational neighbour-class set. This is the shared truth both domains render from."""
    n, na = SPLIT_KNOBS["n_entities"], SPLIT_KNOBS["n_attr"]
    nc, nt, rp = SPLIT_KNOBS["n_classes"], SPLIT_KNOBS["n_rel_tags"], SPLIT_KNOBS["rel_pick"]
    world = []
    for k in range(n):
        attrs = [_u(seed, "ent", k, "attr", a) for a in range(na)]           # latent continuous attrs ∈ [0,1]
        cls = int(_u(seed, "ent", k, "cls") * nc) % nc                        # latent class index
        # relational fingerprint: the top ``rel_pick`` tag indices by latent affinity (a neighbour-class set)
        aff = [(_u(seed, "ent", k, "rel", t), t) for t in range(nt)]
        rel = sorted(t for _a, t in sorted(aff, reverse=True)[:rp])
        world.append({"lid": k, "attrs": attrs, "cls": cls, "rel": rel})
    return world


def _perm(seed: str, dk: str, kind: str, m: int) -> list[int]:
    """A per-domain permutation ``p`` of range(m): ``p[c]`` = the vocab position latent index ``c`` renders to.
    A and B use INDEPENDENT permutations, so a twin's surface position differs across domains — a vocab-index
    matcher cannot align them without recovering the permutation (the §13 leak fix)."""
    return sorted(range(m), key=lambda c: _u(seed, dk, "perm", kind, c))


def _render(seed: str, ent: dict, dk: str, local_idx: int, cls_perm: list[int], tag_perm: list[int]) -> dict:
    """Render one latent entity into domain ``dk`` via the variant transform. The same entity becomes a
    different-looking record per domain; the latent id is NEVER written into the output, and the categorical
    channels render through a PER-DOMAIN vocab permutation so surface position does not align across domains."""
    spec = DOMAINS_SPLIT[dk]
    noise = SPLIT_KNOBS["noise"]
    metric = []
    for a, v in enumerate(ent["attrs"]):
        sc, off = spec["scale"][a], spec["off"][a]
        jitter = noise * sc * (_u(seed, dk, "rn", ent["lid"], a) - 0.5)       # per-domain noise breaks exact match
        metric.append(round(sc * v + off + jitter, 3))
    return {
        "id": f"{spec['prefix']}-{local_idx:03d}",
        spec["fields"]["attr"]: metric,
        spec["fields"]["cls"]: spec["cls_vocab"][cls_perm[ent["cls"]]],       # disjoint vocab, PER-DOMAIN permuted
        spec["fields"]["rel"]: [spec["tag_vocab"][tag_perm[t]] for t in ent["rel"]],
        "_lid": ent["lid"],                                                   # eval-only (oracle); stripped from any public view
        "_cls_idx": ent["cls"], "_rel_idx": ent["rel"], "_attr_latent": ent["attrs"],
    }


def generate_split(seed: str) -> dict:
    """Build the latent world, split it into two domains with honest sparsity, and return the eval-only
    twin map (ground truth) + latents (oracle). Deterministic.

    Leak guards (OBSERVER §13 review): the two domains' unit orders are INDEPENDENTLY shuffled, so a twin's
    (a_idx, b_idx) are uncorrelated (no diagonal id leak); and each domain renders categories through its own
    vocab permutation, so surface position does not align across domains.
    """
    world = _latent_world(seed)
    n = len(world)
    nc, nt = SPLIT_KNOBS["n_classes"], SPLIT_KNOBS["n_rel_tags"]
    n_twin = max(1, int(round(n * SPLIT_KNOBS["twin_frac"])))
    order = sorted(range(n), key=lambda k: _u(seed, "shuf", k))
    twinned = set(order[:n_twin])
    # route each latent entity to domain(s): twins → BOTH; the rest → exactly one (domain-private hard negatives)
    A_lids, B_lids = [], []
    for k in order:
        if k in twinned:
            A_lids.append(k); B_lids.append(k)
        elif _u(seed, "side", k) < 0.5:
            A_lids.append(k)
        else:
            B_lids.append(k)
    # INDEPENDENT per-domain shuffle of the final render order ⇒ a twin's positions in A and B are uncorrelated
    A_lids = [A_lids[j] for j in sorted(range(len(A_lids)), key=lambda i: _u(seed, "ordA", i))]
    B_lids = [B_lids[j] for j in sorted(range(len(B_lids)), key=lambda i: _u(seed, "ordB", i))]
    cpA, cpB = _perm(seed, "A", "cls", nc), _perm(seed, "B", "cls", nc)
    tpA, tpB = _perm(seed, "A", "tag", nt), _perm(seed, "B", "tag", nt)
    A_units = [_render(seed, world[k], "A", j, cpA, tpA) for j, k in enumerate(A_lids)]
    B_units = [_render(seed, world[k], "B", j, cpB, tpB) for j, k in enumerate(B_lids)]
    a_pos = {k: j for j, k in enumerate(A_lids)}
    b_pos = {k: j for j, k in enumerate(B_lids)}
    twin_map = sorted((a_pos[k], b_pos[k]) for k in twinned)
    return {
        "seed": seed,
        "A": {"domain": "A", "prefix": DOMAINS_SPLIT["A"]["prefix"], "units": A_units},
        "B": {"domain": "B", "prefix": DOMAINS_SPLIT["B"]["prefix"], "units": B_units},
        "twin_map": twin_map,                          # eval-only: the true cross-domain (a_idx, b_idx) bridges
        "_world": world,                               # eval-only: the oracle's latent KG
    }


def public_view(g: dict) -> dict:
    """The substrate as a downstream consumer (a metric / axiom-gain) would see it: domain records with the
    eval-only ``_*`` latent fields STRIPPED, and NO twin map. Proves the truth is not leaked into the input."""
    def strip(u: dict) -> dict:
        return {k: v for k, v in u.items() if not k.startswith("_")}
    return {"seed": g["seed"],
            "A": {**g["A"], "units": [strip(u) for u in g["A"]["units"]]},
            "B": {**g["B"], "units": [strip(u) for u in g["B"]["units"]]}}
