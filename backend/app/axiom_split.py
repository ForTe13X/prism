"""Axiom layer for the split-from-shared-latent substrate (DESIGN_data_package §11b) — the deterministic
cross-domain TWIN RESOLVER + the naive/axiom contexts the axiom-gain ablation measures. Clean-room.

The task is cross-domain COREFERENCE: some domain-A entities (AX-*) are the SAME real-world entity as some
domain-B entity (BQ-*), but rendered through a non-leaky variant transform (different units/vocab/schema) so
the link is NOT recoverable by surface match — only by the semantic numeric correlation (the gate proved a
z-scored matcher recovers at ~0.99 while every surface/structural matcher is ~chance). The question: for each
such A entity, list its B-domain tags. That answer requires resolving the twin first.
  * naive_context_split — the raw both-domain records: the model must do the cross-domain resolution ITSELF
    from variant-transformed numbers (hard — there is no shared key, surface is non-leaky);
  * axiom_context_split — the RESOLVER's predicted twin links pre-joined to the B tags: compact, the model
    reads the answer off.

The "axiom" here is a DETERMINISTIC resolver (within-domain z-score → mutual-best numeric match + a distance
gate), so build cost ≈ 0 LLM tokens (same honest story as the logistics axiom layer). Its accuracy is bounded
and reported (it is not an oracle); axiom-RAG quality is therefore bounded by the resolver, which is the
honest point — the structured foundation does the cross-domain resolution the LLM cannot do well from raw.
No clock, no random.
"""
from __future__ import annotations

from .data_package_split import DOMAINS_SPLIT, generate_split, public_view

_AF = DOMAINS_SPLIT["A"]["fields"]
_BF = DOMAINS_SPLIT["B"]["fields"]
# pre-registered from the twin-vs-private z-distance DISTRIBUTIONS (NOT tuned on the final F1, §6c): over 20
# seeds the true-twin best z-distance has median≈0.385, a private entity's best-distance median≈1.0; the gate
# sits at their MIDPOINT (≈0.69), so a predicted twin is a MUTUAL best match closer than a typical coincidental
# match. (A Lowe-style best/second-best ratio gate was tried and DROPPED — it only traded recall for precision,
# not net F1, so it adds a knob without a win.)
RESOLVE_DIST_GATE = 0.69


def _zscore(units: list[dict], field: str) -> list[list[float]]:
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


def resolve_twins(pub: dict) -> list[dict]:
    """Predict cross-domain twin links from the PUBLIC view only (no latents). Within-domain z-score undoes
    the per-domain affine; a pair is a predicted twin iff it is a MUTUAL best numeric match AND within the
    pre-registered distance gate (so domain-private entities, whose best match is far, are rejected)."""
    A, B = pub["A"]["units"], pub["B"]["units"]
    if not A or not B:
        return []
    zA, zB = _zscore(A, _AF["attr"]), _zscore(B, _BF["attr"])

    def dist(i: int, j: int) -> float:
        return sum((zA[i][k] - zB[j][k]) ** 2 for k in range(len(zA[i])))

    bestB = [min(range(len(B)), key=lambda j: dist(i, j)) for i in range(len(A))]
    bestA = [min(range(len(A)), key=lambda i: dist(i, j)) for j in range(len(B))]
    links = []
    for i in range(len(A)):
        j = bestB[i]
        if bestA[j] == i and dist(i, j) <= RESOLVE_DIST_GATE:        # mutual best, closer than midpoint
            links.append({"a_id": A[i]["id"], "b_id": B[j]["id"], "b_tags": sorted(B[j][_BF["rel"]])})
    return links


def task_question_split() -> str:
    return ("下列两域记录里,有些 A 域实体(AX-)与某个 B 域实体(BQ-)指向**同一现实实体**(经过单位/词汇/字段改写,"
            "无共享主键)。对每个这样的 A 实体,列出它对应 B 实体的**标签**(B 记录的 labels 字段)。只用上下文、不要"
            "编造;无法确定就不输出该条。输出 JSON:{\"answer\":[{\"a_id\":\"AX-...\",\"b_tags\":[\"...\"]}]}。")


def naive_context_split(pub: dict) -> str:
    """Raw both-domain records — present but UNRESOLVED; the model must cross-domain-match itself."""
    lines = ["[A 域记录]"]
    for u in pub["A"]["units"]:
        lines.append(f"- {u['id']} {_AF['attr']}={u[_AF['attr']]} {_AF['cls']}={u[_AF['cls']]} {_AF['rel']}={u[_AF['rel']]}")
    lines.append("[B 域记录]")
    for u in pub["B"]["units"]:
        lines.append(f"- {u['id']} {_BF['attr']}={u[_BF['attr']]} {_BF['cls']}={u[_BF['cls']]} {_BF['rel']}={u[_BF['rel']]}")
    return "\n".join(lines)


def axiom_context_split(pub: dict) -> str:
    """The resolver's predicted twins, pre-joined to the B tags — compact; the model reads the answer off."""
    links = resolve_twins(pub)
    lines = ["[已解析跨域孪生 · A 实体 ≡ B 实体 → B 标签]"]
    for f in links:
        lines.append(f"- {f['a_id']} ≡ {f['b_id']};B标签={','.join(f['b_tags'])}")
    if len(lines) == 1:
        lines.append("- (无可解析的跨域孪生)")
    return "\n".join(lines)


def oracle_answer_split(g: dict) -> dict:
    """Ground truth: for each true twin (from the eval-only twin_map), the A id → its B record's tags."""
    A, B = g["A"]["units"], g["B"]["units"]
    return {A[ai]["id"]: sorted(B[bi][_BF["rel"]]) for ai, bi in g["twin_map"]}


def resolver_accuracy(seeds: list[str]) -> dict:
    """Honest, LLM-free: how good is the deterministic resolver vs the true twin_map (P/R/F1 over A→B-tags)?
    This BOUNDS axiom-RAG quality, so it is reported alongside."""
    from .data_package_eval import score
    tp = fp = fn = 0
    f1s = []
    for sd in seeds:
        g = generate_split(sd)
        pub = public_view(g)
        pred = {f["a_id"]: f["b_tags"] for f in resolve_twins(pub)}
        truth = oracle_answer_split(g)
        link_pred = {f["a_id"] for f in resolve_twins(pub)}
        link_truth = set(truth)
        tp += len(link_pred & link_truth); fp += len(link_pred - link_truth); fn += len(link_truth - link_pred)
        f1s.append(score(pred, truth)["f1"])
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    return {"link_precision": round(prec, 3), "link_recall": round(rec, 3),
            "answer_f1_mean": round(sum(f1s) / len(f1s), 3) if f1s else 0.0, "seeds": len(seeds)}
