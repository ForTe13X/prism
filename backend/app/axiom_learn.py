"""Learned canonical resolver (RESEARCH_axiom_gain §5) — the axiom layer with a REAL build cost.

The shipped axiom layer (``axiom_layer.canon``) hardcodes its alias dictionary, so its build cost is ~0
and amortization is trivial-by-construction. §5 ("建造成本 + 摊销曲线") is the real research question:
an axiom-net pays a one-time BUILD cost (a learning loop that consumes labeled training examples) for a
per-query SAVING — so the honest figure is the break-even N* where ``saving·N − build`` turns positive.

This module supplies the learnable half, fully DETERMINISTIC (no clock/random, no live model):
  * ``learn_resolver`` mines a variant→canonical alias dictionary INCREMENTALLY from a TRAINING split of
    packages, supervised by each training package's recorded ``corruption_map['aliases']`` (a realistic
    "we have some labeled alias examples" setup). Held-out packages NEVER expose their corruption_map to
    the learner — the train/test boundary that keeps the eval honestly held-out.
  * Build cost is charged in (estimated) tokens of the observation text the learner reads per training
    package — a real, countable proxy for build effort (HONEST: estimated, not model-metered; a real
    LLM-fired build would cost strictly more, so this is a lower bound on the amortization gap).
  * ``learned_canon`` is the mined-dictionary canonicalizer injected into ``axiom_layer._resolve`` — so
    the SAME deterministic cross-source join scores the learned layer and the algorithmic one apples-to-
    apples (see ``amortization.run_amortization``).
"""
from __future__ import annotations

import re

from . import axiom_layer
from .data_package import _DEFAULT_ROLES
from .data_package_eval import observation_view, oracle_solve, score

_CJK = re.compile(r"[㐀-鿿豈-﫿]")
_WORD = re.compile(r"[A-Za-z0-9]+")


def estimate_tokens(text: str) -> int:
    """Deterministic, MODEL-FREE token estimate (an honest proxy, NOT the model's tokenizer): each CJK
    char ≈ 1 token, each ASCII word-run ≈ ceil(len/4) tokens, the rest (punct/space) ≈ ceil(n/3)."""
    if not text:
        return 0
    cjk = len(_CJK.findall(text))
    words = _WORD.findall(text)
    word_chars = sum(len(w) for w in words)
    word_tok = sum(-(-len(w) // 4) for w in words)
    other = len(text) - cjk - word_chars
    return cjk + word_tok + -(-other // 3)


def learned_canon(text: str, alias_map: dict) -> str:
    """Canonicalize using ONLY the mined dictionary — variants never seen in training stay unresolved
    (that residual mis-resolution is exactly the learning signal). Longest variant first so a variant
    that contains a shorter one (e.g. '华东区' ⊃ '华东') resolves as a whole."""
    for variant in sorted(alias_map, key=len, reverse=True):
        if variant:
            text = text.replace(variant, alias_map[variant])
    return text


def observation_read_text(obs: dict) -> str:
    """A domain-generic rendering of the observations a learner reads per training package (news bodies +
    hub/record rows by ROLE) — the basis for the (estimated) build cost. Generic so the cost is measured
    the same way for any domain, not via a logistics-worded context."""
    r = obs.get("roles", _DEFAULT_ROLES)
    parts = [n.get("body", "") for n in obs["news"]]
    for store in (r["hub_store"], r["record_store"]):
        for row in obs["sql"].get(store, []):
            parts.append(" ".join(f"{k}={v}" for k, v in row.items()))
    return "\n".join(parts)


def resolve_answer(obs: dict, canon_fn) -> dict:
    """Deterministic explain_delays answer {news_id: shipment_ids} from the cross-source join under a
    given canonicalizer — no LLM, so the learned vs algorithmic layers compare without fixtures."""
    return {f["news_id"]: f["shipment_ids"] for f in axiom_layer._resolve(obs, canon_fn)}


def heldout_resolve_f1(eval_obs: list[dict], eval_truth: list[dict], canon_fn) -> float:
    if not eval_obs:
        return 0.0
    return round(sum(score(resolve_answer(o, canon_fn), t)["f1"]
                     for o, t in zip(eval_obs, eval_truth)) / len(eval_obs), 4)


def eval_variants(eval_pkgs: list[dict]) -> set:
    """The distinct alias variants present across held-out packages — an EVALUATOR diagnostic (the
    learner itself never reads these corruption_maps), used only to report dictionary coverage."""
    out: set = set()
    for p in eval_pkgs:
        out.update(p.get("corruption_map", {}).get("aliases", {}).keys())
    return out


def alias_coverage(alias_map: dict, variants: set) -> float:
    if not variants:
        return 1.0
    return round(len(variants & set(alias_map)) / len(variants), 4)


def learn_resolver(source_id: str, train_seeds: list[str], dirt: float,
                   eval_obs: list[dict], eval_truth: list[dict], eval_variants_set: set) -> dict:
    """Incrementally mine the alias dictionary from the training split, recording per round the marginal
    build cost (tokens read), the marginal aliases gained, and the held-out quality reached so far —
    i.e. the per-iteration (cost, benefit) curve §5 calls for. Imported lazily to avoid a cycle."""
    from .data_package import generate

    alias_map: dict = {}
    rounds: list[dict] = []
    build_tokens = 0
    for i, sd in enumerate(train_seeds):
        pkg = generate(source_id, dirtiness=dirt, link_explicitness=4, seed=sd)
        # the learner reads this training package's raw observations (the build cost) and is supervised by
        # its labeled variant→canonical pairs (held-out packages never reach this branch).
        read_tokens = estimate_tokens(observation_read_text(observation_view(pkg)))
        build_tokens += read_tokens
        before = len(alias_map)
        for variant, canonical in pkg["corruption_map"]["aliases"].items():
            alias_map.setdefault(variant, canonical)
        new_aliases = len(alias_map) - before
        cf = (lambda m: (lambda t: learned_canon(t, m)))(dict(alias_map))  # snapshot this round's dict
        rounds.append({
            "round": i + 1, "seed": sd,
            "round_build_tokens": read_tokens, "cum_build_tokens": build_tokens,
            "new_aliases": new_aliases, "aliases_known": len(alias_map),
            "heldout_alias_coverage": alias_coverage(alias_map, eval_variants_set),
            "heldout_resolve_f1": heldout_resolve_f1(eval_obs, eval_truth, cf),
        })
    return {"alias_map": alias_map, "rounds": rounds, "build_tokens": build_tokens}


def held_out_packages(source_id: str, eval_seeds: list[str], dirt: float) -> tuple[list, list, list, set]:
    """Generate the held-out eval packages once and derive the obs/truth/variant views used everywhere."""
    from .data_package import generate

    pkgs = [generate(source_id, dirtiness=dirt, link_explicitness=4, seed=sd) for sd in eval_seeds]
    obs = [observation_view(p) for p in pkgs]
    truth = [oracle_solve(p, "explain_delays") for p in pkgs]
    return pkgs, obs, truth, eval_variants(pkgs)
