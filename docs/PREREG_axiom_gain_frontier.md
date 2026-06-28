# PRE-REGISTRATION · axiom-gain H2 (does the gain shrink as the model gets more capable?)

> A pre-registration in the §6c spirit: state the falsifiable prediction + the decision rule **before** the
> test point exists, so a confirmed *shrinkage* reads as a **predicted result, not a loss**. OBSERVER §15 P1.
> Registered: 2026-06-28, against build `7bffcda`. The registered TEST is a **frontier model not yet run**;
> the existing 8B–31B trend below is labelled **already-observed (motivating, NOT pre-registered)** — its
> fixtures predate this hypothesis, so it cannot count as a pre-registered confirmation.

## The load-bearing generalization question

The surviving line's headline is *"a structured semantic foundation lets a small LLM save ~61% input tokens
at equal-or-better quality."* The one un-tested generalization (OBSERVER §15 A): **that evidence is almost
entirely small LOCAL models** (qwen3-8b, gemma-12b/31b-qat). A frontier model can already read messy,
unresolved context — so it may not *need* the pre-resolution. Does the benefit survive at higher capability?

## Hypotheses (falsifiable, with a decision rule)

Capability proxy = **per-model mean naive-RAG F1** (how well the model does the cross-source task WITHOUT the
axiom layer — i.e. task competence on raw context). Higher naive-F1 = more capable *at this task*. (Params are
a poor proxy here: qwen3-8b already out-competes gemma-12b on naive F1 despite fewer params.) **Caveat: this
proxy is TASK-LOCAL** — it is measured on the same fixtures the gain is computed on, so "capability" here means
"competence at THIS cross-source task," not general capability; a frontier model could rank differently on a
different task.

- **H2a (quality gain shrinks with capability).** The *quality* gain `ΔF1 = axiom_F1 − naive_F1` is **monotone
  non-increasing** in capability. Mechanism: a more capable model extracts more of the cross-source answer
  from raw context itself, leaving less headroom for the resolver to add. **Confirm:** Spearman
  `corr(capability, ΔF1) ≤ 0` across the model set (and the frontier point's ΔF1 ≤ the most-capable current
  model's). **Refute:** the frontier model's quality gain is *larger* than gemma-31b's (gain grows with
  capability).
- **H2b (token saving is structural ⇒ model-independent).** The *input-token* saving is set by the context
  SIZE (axiom context ≈ 40% of naive), not the model, so it should stay **~flat** across capability (spread
  < 0.05). **Confirm:** the frontier point's token saving is within ±0.05 of the current mean (~0.61).
  **Refute:** it moves materially with the model. *(This is the honest nuance the headline must carry: "61%"
  is structural and survives any model; what H2a tests is whether the QUALITY benefit survives.)*

## Method (near-zero new code)

`backend/app/benchmark.py::run_ablation` already takes any `models=[...]` and `allow_live=True`;
`axiom_gain_protocol.run_protocol` already aggregates per-cell bootstrap CIs and (now) emits the
`h2_capability_vs_gain` axis. To run the registered test:
1. Point `llm_client` at a more-capable OpenAI-compatible endpoint (a frontier API, or the largest local
   model that fits — see the honest constraint below).
2. `run_split=run_ablation(models=[FRONTIER], seeds=[ho-0..7], dirts=[0,0.3,0.6,0.9], allow_live=True)` to
   freeze its fixtures (one model added to the matrix; **existing fixtures untouched, byte-identical**).
3. Re-read `run_protocol()`; inspect `h2_capability_vs_gain` for the monotone-decreasing flag + the frontier
   point's position.

## Already-observed trend (8B–31B, **motivating — NOT a pre-registered confirmation**)

Ordered by capability (mean naive-RAG F1), from the committed fixtures:

| model | capability (naive F1) | quality gain ΔF1 | token saving |
|---|---|---|---|
| gemma-4-12b-qat | 0.620 | **0.166** | 0.608 |
| qwen3-8b-instruct | 0.759 | 0.157 | 0.627 |
| gemma-4-31b-qat | 0.808 | **0.108** | 0.608 |

⇒ quality gain is **monotone decreasing** in capability (Spearman −1.0 across 3 points), token saving ~flat.
This is consistent with H2a/H2b, but it is **post-hoc** (the data predates this doc) and only spans local
models ≤ 31B — exactly why the registered test is a **higher-capability point**. **Fragility, surfaced
honestly:** the first step (gemma-12b 0.166 → qwen 0.157) is a margin of only **0.009 — within the per-cell
CIs** ⇒ a tiny wobble would flip that pair to a tie. The monotone flag is **carried mainly by the 31b drop**
(0.157 → 0.108); read "Spearman −1.0" as a 3-point ordering, not a powered effect.

## Honest constraints (registered up front)

- **Local-first / freeze risk.** This machine froze once while sizing a frontier-tier local model; loading a
  122B/397B model risks it again. The registered frontier point therefore needs **either** a frontier API
  endpoint (breaks the `$=0` local-only property — disclose the $ if used) **or** the largest local model
  that is verified to load safely. Until one is run, H2 stays **registered-but-untested** — that is the
  honest state, not a result.
- **Probe log (2026-06-28, this machine).** The **Q8_0** `unsloth/qwen3.6-35b-a3b` (≈42 GB at a 256K context)
  exceeded VRAM ⇒ <0.18 tok/s (CPU-bound), unusable. The user pointed to the **Q4_K_M** build
  `qwen/qwen3.6-35b-a3b` (~18–20 GB) which loads + runs at ~5.5 tok/s. Two harness fixes were needed first:
  (a) qwen3.6 is a **reasoning model** and LM Studio routes its json_schema answer into `reasoning_content`,
  leaving `content` empty (F1 0 for everything) — `llm_client` now falls back to `reasoning_content` when
  `content` is blank; (b) a `timeout` pass-through for the slow model. With those, the registered ablation ran.

## Result of the registered test (RUN 2026-06-28, `qwen/qwen3.6-35b-a3b`, 8 seeds × 4 dirt)

| model (↑ capability) | naive F1 | quality gain ΔF1 | token saving |
|---|---|---|---|
| gemma-12b | 0.620 | 0.166 | 0.608 |
| **qwen3.6-35b-a3b (new)** | **0.741** | **0.175** | 0.634 |
| qwen-8b | 0.759 | 0.157 | 0.627 |
| gemma-31b | 0.807 | 0.108 | 0.608 |

- **H2a — directionally SUPPORTED, strict monotonicity REFUTED.** Across 4 models `Spearman(capability, gain)
  = −0.80` (gain still falls with capability), but the new point is **off the monotone line** (gain 0.175 at
  capability 0.741, *above* gemma-12b's 0.166). So "monotone non-increasing" is **false**; the weaker
  directional claim holds. *This is the value of the pre-registration: monotone was predicted, the data says
  "negative-but-not-monotone," and that is what's reported.*
- **The candidate was NOT actually a frontier point.** Its naive F1 (0.741) lands **mid-axis, below
  gemma-31b's 0.807** — a 35B MoE with 3B active is **not** more task-competent than 31B dense here. So the
  registered Confirm rule (*"the frontier point's ΔF1 ≤ gemma-31b's 0.108"*) was **not exercised** — we added
  an interior point, not a higher-capability one. **The genuine frontier regime (naive F1 > 0.81) remains
  registered-but-untested** (needs a model that is actually more capable on this task).
- **H2b — CONFIRMED.** The new model's token saving (0.634) keeps the spread structural-flat (0.025 < 0.05);
  the ~61% headline is model-independent, as predicted.
- **No grid pruned.** The off-line point is kept and reported (it would have been tempting to drop it to
  preserve "monotone −1.0"); that would violate DON'T #4.
- **No silent grid-pruning (DON'T #4/§15).** If the frontier cell shows *no* gain, it is **kept and reported**
  (a confirmed H2a, the predicted outcome) — never deleted to preserve a prettier headline.
- **Win either way.** Confirm ⇒ a real cross-capability result (the structural 61% survives; the quality
  benefit concentrates where it should — on weaker models). Refute ⇒ a surprising, more-valuable finding
  (capable models *also* benefit). Both are reported.
