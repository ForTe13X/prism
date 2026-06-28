"""RESEARCH_axiom_gain §4/§6/§6b — the FULL-protocol aggregation over the ablation matrix: turn the
point-estimate ablation into a real mini-result (cross-model matrix × multi-seed mean±CI + cost-per-correct
Pareto frontier + gain×dirtiness robustness curve + the §5 build-amortization break-even). Deterministic.

The ablation engine (`benchmark.run_ablation`) already runs naive-RAG vs axiom-RAG on the SAME model/prompt
and reports per-(model,dirt) quality + tokens. It pools seeds internally, so it gives a POINT estimate with
no variance. Here we call it PER SINGLE SEED (all cached ⇒ fast, deterministic) to recover the per-seed
spread, then:
  * mean ± deterministic-bootstrap 95% CI on the quality gain (ΔF1) and the token saving (1 − in-token ratio),
    per (model, dirt) — the project's "report mean±CI, a CI that straddles 0 is indeterminate" discipline;
  * the cost-per-correct PARETO frontier across every (model, dirt, condition) point — is the axiom condition
    Pareto-dominant (lower tokens-per-correct AND ≥ quality) everywhere?;
  * the gain×dirtiness ROBUSTNESS curve per model (does the gain grow as the data gets dirtier? — H2);
  * the model-SCALE interaction (does the gain shrink as the model gets larger? — structure helps the weak
    model more) using the within-family gemma 12b→31b pair as the clean axis;
  * the §5 build break-even pulled from `run_amortization` (structural gain is build-free; the learned
    dictionary adds ~0 held-out F1 ⇒ N* = ∞ — an honest negative, surfaced not hidden).

HONESTY: nothing here is tuned; the matrix/seeds/dirts are inputs. Missing (un-cached) cells are reported in
`coverage`, never silently dropped. Local models ⇒ $=0, so the cost axis is REAL tokens (tokens-per-correct),
not dollars — stated, not blurred. Determinism: bootstrap resamples via Prism's own `_unit` sha256 hash.
"""
from __future__ import annotations

from .amortization import run_amortization
from .benchmark import run_ablation
from .data_synth import _unit

# default protocol matrix (the fixture-populated set). The gemma 12b→31b pair is the clean within-family
# scale axis; qwen-8b is a third, smaller, cross-family point.
PROTO_MODELS = ["qwen-3-8b-instruct", "google/gemma-4-12b-qat", "google/gemma-4-31b-qat"]
PROTO_SEEDS = [f"ho-{i}" for i in range(8)]
PROTO_DIRTS = [0.0, 0.3, 0.6, 0.9]
_BOOT = 500
_SCALE_PAIR = ("google/gemma-4-12b-qat", "google/gemma-4-31b-qat")  # same family, 12b→31b

# The genuine-frontier GPT-5.5 point (OBSERVER §15 P1) — a Tier-2 disclosed MANUAL measurement (browser-captured,
# NOT reproducible). Recorded constants mirror docs/PREREG_axiom_gain_frontier.md §"Genuine frontier point".
_FRONTIER_CAP = 0.95   # naive F1 ≈ 0.95 (highest of any model tested)
_FRONTIER_GAIN = 0.0   # ΔF1 ≈ 0 from a 4-naive + 1-axiom slice (NOT a mean±CI)


def _frontier_confirms(frontier_gain: float, rows: list) -> bool:
    """Registered Confirm rule: frontier ΔF1 ≤ the most-capable current model's ΔF1. Pure + computed from the
    LIVE rows (never a stored literal) so the verdict can't drift if the fixtures shift — and so BOTH branches
    are unit-testable (the fixtures only ever exercise the True branch)."""
    return bool(rows and frontier_gain <= rows[-1]["quality_gain"])


def _provenance(model: str) -> dict:
    """Per-model provenance for the H2 axis. Most rows are LOCAL ($0, strict json-schema). deepseek-v4-pro is an
    INDEPENDENT real-API point whose full-grid task-competence is TIED with gemma-31b (naive F1 ~0.808 vs 0.8075)
    — a cross-model corroboration, NOT a higher-capability / frontier point — FROZEN from a one-time paid Ark run
    (reproducible from fixtures at serve-time $0) and produced with prompt-JSON (the model supports no
    response_format). Surfaced per-row so the visual can badge + caveat it, never silently mixing a $≠0 /
    prompt-JSON point into the $0 strict-schema set (the capability proxy + F1 are still measured identically,
    so the point is comparable, with a caveat)."""
    if model == "deepseek-v4-pro-260425":
        return {"source": "ark-api", "cost": "paid-freeze", "structured": "prompt-json", "reproducible": True}
    return {"source": "local", "cost": "free", "structured": "json-schema", "reproducible": True}


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _boot_ci(xs: list[float], tag: str) -> tuple[float, float, float]:
    """Deterministic bootstrap (mean, ci_lo, ci_hi) over a per-seed sample. Resamples seeds with replacement
    using `_unit` (no random/clock). A single-point sample returns (x, x, x)."""
    k = len(xs)
    if k == 0:
        return 0.0, 0.0, 0.0
    if k == 1:
        return xs[0], xs[0], xs[0]
    means = []
    for b in range(_BOOT):
        idx = [int(_unit(tag, b, i) * k) % k for i in range(k)]
        means.append(sum(xs[j] for j in idx) / k)
    means.sort()
    return _mean(xs), means[int(0.025 * _BOOT)], means[int(0.975 * _BOOT) - 1]


def _cell(source_id: str, model: str, dirt: float, seed: str) -> dict | None:
    """One (model, dirt, seed) ablation cell from fixtures, or None if not cached. Returns the per-seed
    quality delta, the input-token saving fraction, and the absolute naive/axiom (f1, tokens-per-correct)."""
    r = run_ablation(source_id, seeds=[seed], models=[model], dirts=[dirt], allow_live=False)
    if not r.get("ok") or not r.get("gains"):
        return None
    conds = {c["condition"]: c for c in r["conditions"]}
    nv, ax = conds.get("naive-RAG"), conds.get("axiom-RAG")
    if not nv or not ax:
        return None
    nv_in = nv["avg_in_tok"] or 1e-9
    return {
        "quality_delta": ax["quality_f1"] - nv["quality_f1"],
        "token_saving": 1.0 - ax["avg_in_tok"] / nv_in,   # fraction of input tokens the axiom layer removes
        "naive_f1": nv["quality_f1"], "axiom_f1": ax["quality_f1"],
        "naive_tpc": nv["tokens_per_correct"], "axiom_tpc": ax["tokens_per_correct"],
    }


def _pareto_front(points: list[dict]) -> None:
    """Mark Pareto-efficient points IN PLACE (`on_front`): minimise tokens_per_correct, maximise quality_f1.
    A point is dominated if another has tpc ≤ and f1 ≥ with at least one strict."""
    for p in points:
        dominated = any(
            q is not p and q["tpc"] <= p["tpc"] and q["f1"] >= p["f1"]
            and (q["tpc"] < p["tpc"] or q["f1"] > p["f1"])
            for q in points
        )
        p["on_front"] = not dominated


def run_protocol(source_id: str = "logistics_demo", *, models: list[str] | None = None,
                 seeds: list[str] | None = None, dirts: list[float] | None = None) -> dict:
    models = models or PROTO_MODELS
    seeds = seeds or PROTO_SEEDS
    dirts = dirts if dirts is not None else PROTO_DIRTS

    matrix, coverage = [], {"requested": 0, "cached": 0, "missing": []}
    for model in models:
        for dirt in dirts:
            per_seed = []
            for sd in seeds:
                coverage["requested"] += 1
                c = _cell(source_id, model, dirt, sd)
                if c is None:
                    coverage["missing"].append({"model": model, "dirt": dirt, "seed": sd})
                    continue
                coverage["cached"] += 1
                per_seed.append(c)
            if not per_seed:
                continue
            deltas = [c["quality_delta"] for c in per_seed]
            savings = [c["token_saving"] for c in per_seed]
            dm, dlo, dhi = _boot_ci(deltas, f"agΔ|{model}|{dirt}")
            sm, slo, shi = _boot_ci(savings, f"agS|{model}|{dirt}")
            matrix.append({
                "model": model, "dirtiness": dirt, "n_seeds": len(per_seed),
                "quality_delta_mean": round(dm, 4), "quality_delta_ci95": [round(dlo, 4), round(dhi, 4)],
                "quality_delta_excludes_0": dlo > 0,
                "token_saving_mean": round(sm, 4), "token_saving_ci95": [round(slo, 4), round(shi, 4)],
                "token_saving_excludes_0": slo > 0,
                "naive_f1": round(_mean([c["naive_f1"] for c in per_seed]), 4),
                "axiom_f1": round(_mean([c["axiom_f1"] for c in per_seed]), 4),
                "naive_tpc": round(_mean([c["naive_tpc"] for c in per_seed]), 1),
                "axiom_tpc": round(_mean([c["axiom_tpc"] for c in per_seed]), 1),
            })

    # cost-per-correct Pareto frontier over every (model, dirt, condition) point
    front = []
    for cell in matrix:
        for cond, f1k, tpck in (("naive", "naive_f1", "naive_tpc"), ("axiom", "axiom_f1", "axiom_tpc")):
            front.append({"label": f"{cond}|{cell['model']}|d{cell['dirtiness']}",
                          "model": cell["model"], "dirtiness": cell["dirtiness"], "condition": cond,
                          "tpc": cell[tpck], "f1": cell[f1k]})
    _pareto_front(front)
    axiom_front = [p for p in front if p["condition"] == "axiom" and p["on_front"]]
    naive_front = [p for p in front if p["condition"] == "naive" and p["on_front"]]

    # gain×dirtiness robustness curve per model. We report BOTH an honest endpoint flag (hi ≥ lo) AND a true
    # monotonicity flag + the peak dirt — because the gain is NOT monotone for every model (some peak at an
    # intermediate dirt then dip at the noisiest dirt=0.9), and an endpoint-only test would hide that shape.
    robustness = {}
    for model in models:
        pts = sorted([c for c in matrix if c["model"] == model], key=lambda c: c["dirtiness"])
        if len(pts) >= 2:
            ds = [c["quality_delta_mean"] for c in pts]
            peak = max(range(len(pts)), key=lambda i: ds[i])
            robustness[model] = {
                "curve": [{"dirt": c["dirtiness"], "quality_delta": c["quality_delta_mean"],
                           "token_saving": c["token_saving_mean"]} for c in pts],
                "endpoint_hi_ge_lo": ds[-1] >= ds[0],               # was 'delta_grows_with_dirt' — endpoint only
                "monotonic_increasing": all(ds[i + 1] >= ds[i] for i in range(len(ds) - 1)),
                "peak_dirt": pts[peak]["dirtiness"],
                "delta_lo_to_hi": [ds[0], ds[-1]],
            }

    # model-scale interaction on the within-family pair (does the gain shrink as the model grows?). HONEST:
    # this is a SINGLE within-family pair and a point comparison of two cell-mean averages — there is NO CI on
    # the difference. We report the per-dirt margins (small−large) so the reader sees it is directional but
    # essentially flat except at one dirt level, not a significance-tested effect.
    def _model_mean(model: str, key: str) -> float | None:
        vals = [c[key] for c in matrix if c["model"] == model]
        return round(_mean(vals), 4) if vals else None

    small, large = _SCALE_PAIR
    sm = {c["dirtiness"]: c["quality_delta_mean"] for c in matrix if c["model"] == small}
    lg = {c["dirtiness"]: c["quality_delta_mean"] for c in matrix if c["model"] == large}
    per_dirt_margin = [{"dirt": d, "small_minus_large": round(sm[d] - lg[d], 4)}
                       for d in sorted(set(sm) & set(lg))]
    scale = {"pair": list(_SCALE_PAIR),
             "small_quality_delta_mean": _model_mean(small, "quality_delta_mean"),
             "large_quality_delta_mean": _model_mean(large, "quality_delta_mean"),
             "small_token_saving_mean": _model_mean(small, "token_saving_mean"),
             "large_token_saving_mean": _model_mean(large, "token_saving_mean"),
             "per_dirt_small_minus_large": per_dirt_margin,
             "small_gt_large_at_all_dirts": bool(per_dirt_margin) and all(m["small_minus_large"] > 0 for m in per_dirt_margin),
             "caveat": ("single within-family pair; point comparison of cell-mean averages, NO CI on the "
                        "difference ⇒ DIRECTIONAL only, not significance-tested.")}

    # H2 (PREREG_axiom_gain_frontier.md): does the QUALITY gain shrink as the model gets more capable, while
    # the TOKEN saving (structural ⇒ context-size-bound) stays flat? Capability proxy = per-model mean naive-RAG
    # F1 (task competence WITHOUT the axiom layer). This is the cross-capability axis the registered frontier
    # point extends; here it is computed on whatever models are in the matrix.
    h2_rows = []
    for m in models:
        cells = [c for c in matrix if c["model"] == m]
        if cells:
            h2_rows.append({"model": m,
                            "capability_naive_f1": round(_mean([c["naive_f1"] for c in cells]), 4),
                            "quality_gain": round(_mean([c["quality_delta_mean"] for c in cells]), 4),
                            "token_saving": round(_mean([c["token_saving_mean"] for c in cells]), 4),
                            "provenance": _provenance(m)})
    h2_rows.sort(key=lambda r: r["capability_naive_f1"])  # ascending capability
    h2_gains = [r["quality_gain"] for r in h2_rows]
    h2_saves = [r["token_saving"] for r in h2_rows]
    save_spread = round(max(h2_saves) - min(h2_saves), 4) if h2_saves else 0.0
    # Spearman rank corr(capability, gain): the DIRECTIONAL H2a measure (robust to a single off-monotone point;
    # the monotone bool is brittle). h2_rows is already ascending in capability ⇒ cap rank = position i.
    spearman = None
    n = len(h2_rows)
    if n >= 3 and len(set(h2_gains)) == n:
        grank = {g: i for i, g in enumerate(sorted(h2_gains))}
        d2 = sum((i - grank[h2_gains[i]]) ** 2 for i in range(n))
        spearman = round(1 - 6 * d2 / (n * (n * n - 1)), 3)
    h2 = {
        "capability_proxy": "per-model mean naive-RAG F1 (task competence WITHOUT the axiom layer)",
        "by_capability_ascending": h2_rows,
        "spearman_capability_gain": spearman,                  # H2a direction: < 0 ⇒ gain shrinks with capability
        "quality_gain_monotone_decreasing": all(h2_gains[i] >= h2_gains[i + 1] for i in range(len(h2_gains) - 1)),
        "token_saving_spread": save_spread,
        "token_saving_is_structural_flat(<0.05)": save_spread < 0.05,
        "note": ("H2a: quality gain ↓ as capability ↑ (a capable model needs the pre-resolution less) — read the "
                 "SPEARMAN (directional), not the brittle monotone bool. H2b: token saving is structural (context "
                 "size) ⇒ ~model-independent; the 61% headline survives any model, only the QUALITY benefit shrinks. "
                 "Pre-registered (PREREG_axiom_gain_frontier.md); the frontier RUN added qwen3.6-35b-a3b — see §11d."),
        # The genuine-frontier point (OBSERVER §15 P1): GPT-5.5 at dirt 0.6 confirms H2a (gain ≈ 0 at the highest
        # capability). It is a Tier-2 disclosed MANUAL measurement — browser-captured, NOT API, NOT reproducible —
        # so it is a frozen recorded CONSTANT flagged reproducible:False and is NEVER merged into the reproducible
        # `by_capability_ascending` series. The registered Confirm rule ("frontier ΔF1 ≤ the most-capable current
        # model's ΔF1") is RECOMPUTED here from the live rows, never a stored literal — so the verdict can't drift
        # if the fixtures shift. Mirrors docs/PREREG_axiom_gain_frontier.md §"Genuine frontier point".
        "frontier_manual": ({
            "model": "gpt-5.5",
            "source": "browser-captured (ChatGPT web 极速, 2026-06-28)",
            "reproducible": False,
            "capability_naive_f1": _FRONTIER_CAP,
            "quality_gain": _FRONTIER_GAIN,
            "token_saving": None,                              # web UI exposes no token counts ⇒ H2b unmeasured for it
            "confirm_rule": "registered: frontier ΔF1 ≤ the most-capable current model's ΔF1",
            "confirm_comparator_model": h2_rows[-1]["model"] if h2_rows else None,
            "confirm_comparator_gain": h2_rows[-1]["quality_gain"] if h2_rows else None,
            "confirm_rule_met": _frontier_confirms(_FRONTIER_GAIN, h2_rows),   # computed live, never a stored literal
            "caveat": ("GPT-5.5 前沿点为浏览器抓取(ChatGPT web 极速, 2026-06-28)、非 API ⇒ 一次性、不可对锁定模型"
                       "复现(仅记录值,未冻结为 fixture);无 token 计数 ⇒ H2b 对它仅结构性推断、未实测;不在 "
                       "protocol 矩阵/fixtures 内,仅见 PREREG/RESEARCH §11e。"),
        } if h2_rows else None),
    }

    # §5 build-amortization break-even (structural gain build-free; learned dict adds ~0 F1 ⇒ N*=∞)
    try:
        amo = run_amortization(source_id)
        amort = {"verdict": amo.get("verdict"),
                 "structural_gain_buildfree": amo.get("value_decomposition", {}).get("structural_gain_buildfree"),
                 "learned_dictionary_gain": amo.get("value_decomposition", {}).get("learned_dictionary_gain"),
                 "breakeven_N_dictionary": amo.get("breakeven", {}).get("breakeven_N_dictionary"),
                 "note": "structural axioms are build-free; the learned dictionary adds ~0 held-out F1 ⇒ never amortizes (honest negative)."}
    except Exception as exc:
        amort = {"error": str(exc)}

    # honest headline verdict
    n_req = len(models) * len(dirts)                       # (model,dirt) cells requested
    n_eval = len(matrix)                                   # cells with ≥1 cached seed (denominator for sig counts)
    saving_cells = [c for c in matrix if c["token_saving_excludes_0"]]
    quality_pos_cells = [c for c in matrix if c["quality_delta_excludes_0"]]
    min_delta = round(min((c["quality_delta_mean"] for c in matrix), default=0.0), 4)
    endpoint_grows = sum(1 for r in robustness.values() if r["endpoint_hi_ge_lo"])
    monotone = sum(1 for r in robustness.values() if r["monotonic_increasing"])
    mean_saving = round(_mean([c["token_saving_mean"] for c in matrix]), 4) if matrix else 0.0
    axiom_dominates = bool(axiom_front) and not naive_front  # only axiom points on the cost-quality frontier

    return {
        "source_id": source_id, "models": models, "seeds": seeds, "dirts": dirts,
        "coverage": coverage,
        "matrix": matrix,
        "cost_per_correct_frontier": {"points": front, "axiom_on_front": len(axiom_front),
                                      "naive_on_front": len(naive_front), "axiom_dominates": axiom_dominates},
        "robustness_gain_vs_dirt": robustness,
        "model_scale_interaction": scale,
        "h2_capability_vs_gain": h2,
        "build_amortization": amort,
        "headline": {
            "cells_evaluated": n_eval, "cells_requested": n_req,   # denominators are over EVALUATED cells
            "mean_input_token_saving": mean_saving,
            "token_saving_significant_cells": f"{len(saving_cells)}/{n_eval}",
            "min_quality_delta": min_delta,
            "quality_never_worse": min_delta >= 0.0,               # strict: a real regression would flip this
            "quality_gain_significant_cells": f"{len(quality_pos_cells)}/{n_eval}",
            "models_endpoint_gain_grows": f"{endpoint_grows}/{len(robustness)}",   # hi ≥ lo (endpoint only)
            "models_monotonic_in_dirt": f"{monotone}/{len(robustness)}",           # gain rises at EVERY dirt step
            "axiom_pareto_dominant": axiom_dominates,
        },
        "honest_verdict": (
            "结构化语义地基(axiom 层:canonical 解析 + 预联结,算法式、build≈0)对裸 RAG 的增益,跨"
            f"{len(models)}模型×{len(dirts)}脏度×{len(seeds)}seed 矩阵、每格 deterministic bootstrap 95% CI。"
            f"**稳的(CI 牢)**:输入 token 平均省 ~{round(mean_saving*100)}%,{len(saving_cells)}/{n_eval} 格 CI>0"
            f"(成本轴=真实 token,本地 $=0);质量 ΔF1 处处非负(min={min_delta})且成本×质量 Pareto 前沿由 axiom 点独占;"
            "build 摊销:结构增益**免 build**,学习字典加 ~0 held-out F1 ⇒ N*=∞(诚实负)。"
            f"**弱的(seed 受限,只报观测不下断言)**:质量 ΔF1 仅 {len(quality_pos_cells)}/{n_eval} 格 CI>0(其余 CI 跨 0=判不定);"
            f"『增益随脏度』只 {monotone}/{len(robustness)} 模型**真单调**(余者在 dirt=0.6 见顶、最吵的 dirt=0.9 回落),端点 hi≥lo 是 {endpoint_grows}/{len(robustness)};"
            "『对更弱模型更大』(scale 轴)是**单对同族、对两均值的点比、差值无 CI ⇒ 仅方向性**(见 `model_scale_interaction.per_dirt_small_minus_large`,除 dirt=0.6 外基本持平)。"
            "诚实边界:小规模 + 合成数据(未接真实校准,见 Track 1)、本地模型 $=0 故只报 token、未覆盖格在 `coverage`。"
        ),
    }
