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

## Genuine frontier point — GPT-5.5 (browser-captured, 2026-06-28) — **H2a CONFIRMED**

The local candidates topped out at naive F1 0.81 (not actually frontier). With no frontier API, the user
drove a **GPT-5.5** session (ChatGPT web, "极速"/fast = low thinking effort) via the Chrome MCP to obtain a
genuinely-more-capable point. Slice: **dirt 0.6, 4 seeds (naive) + an axiom check** (browser-driving is slow,
so a small honest sample).

| model | naive F1 (dirt 0.6) | axiom F1 | quality gain |
|---|---|---|---|
| gemma-12b | 0.532 | — | 0.271 |
| qwen3.6-35b-a3b | 0.715 | — | 0.193 |
| qwen3-8b | 0.751 | — | 0.156 |
| gemma-31b | 0.777 | — | 0.130 |
| **GPT-5.5 (frontier)** | **0.950** | **≈1.0** | **≈ 0.00** |

- **H2a CONFIRMED at the frontier.** GPT-5.5 has the **highest** naive F1 (0.950 — it does the cross-source
  resolution itself, e.g. ho-0/ho-1/ho-3 = 1.0; ho-2 = 0.8 only because a true shipment was dirt-NULLED and
  it correctly refused to hallucinate it) and the **smallest** quality gain (≈ 0 — the axiom context just
  hands it an answer it already produces). The registered Confirm rule (*frontier ΔF1 ≤ gemma-31b's 0.108*)
  is **met** (≈0.00 ≤ 0.108). The structured-foundation **QUALITY** benefit **vanishes** at frontier
  capability — exactly H2a, now at a point that is genuinely more capable (unlike the qwen3.6 interior point).
- **H2b NOT measured here (and that's the honest gap).** The web UI exposes no token counts, so GPT-5.5's
  token *saving* is not measured. It is **structural** (the axiom context is ~40% the size regardless of
  model), so the ~61% saving would still apply — but for GPT-5.5 it would buy **token savings with ~no
  quality change**, which is the most useful honest framing of the whole H2 result.
- **Honesty caveats (loud).** Browser-captured from "ChatGPT GPT-5.5 极速 as of 2026-06-28", **not** API:
  one-off, **not** re-runnable against a pinned model (recorded values only, not frozen as fixtures);
  **no token counts**; **small sample** (dirt 0.6, 4 naive + 1 axiom); prompt newlines were flattened to
  spaces and one mojibake *distractor* per cell un-garbled (distractors don't affect the answer); this row
  is NOT in the protocol matrix/fixtures (it can't be reproduced offline) — it lives here as a disclosed
  manual measurement. The local API rows remain the reproducible record.
- **No silent grid-pruning (DON'T #4/§15).** If the frontier cell shows *no* gain, it is **kept and reported**
  (a confirmed H2a, the predicted outcome) — never deleted to preserve a prettier headline.
- **Win either way.** Confirm ⇒ a real cross-capability result (the structural 61% survives; the quality
  benefit concentrates where it should — on weaker models). Refute ⇒ a surprising, more-valuable finding
  (capable models *also* benefit). Both are reported.

## API corroboration point — deepseek-v4-pro (Ark, frozen 2026-06-28) — H2b MEASURED, capability TIED

With a real commercial **API** available (Volcengine Ark `deepseek-v4-pro-260425`, a large frontier-*tier*
model — though, as it turns out, not more *task-competent* here), the registered grid (8 seeds × 4 dirt) was
run live once and **frozen into fixtures** (reproducible offline at serve-time $0).
The headline expectation — "an API model will be a higher-capability point" — **did NOT hold over the full
grid**, and that negative is reported as loudly as a win:

| model (full grid) | capability (naive F1) | quality gain ΔF1 | token saving |
|---|---|---|---|
| gemma-4-31b-qat (local) | 0.8075 | 0.1082 | 0.6084 |
| **deepseek-v4-pro (API)** | **0.8083** | **0.1074** | **0.6349** |

- **Capability is TIED, not higher.** deepseek's full-grid naive F1 (0.8083) is within **0.001** of gemma-31b
  (0.8075) — a wash, not a frontier. The per-dirt profile differs (deepseek is *more* robust at heavy dirt
  d0.9 = 0.762 vs 0.708, but *weaker* at moderate dirt d0.3/0.6), netting a tie. **A 4-seed dirt-0.6 pilot
  showed 0.872 and looked frontier — the full 8-seed grid (0.758 at d0.6) corrected it.** Honest lesson: a
  small favourable slice overstated the edge; the registered grid is the number.
- **What it IS (still valuable): cross-model corroboration + a MEASURED H2b.** A completely different model
  (frontier API, different architecture) at the *same* task-competence shows the *same* quality gain
  (0.1074 ≈ gemma-31b's 0.1082) ⇒ H2a is not a local-model artefact. And the ~63% token saving is **measured
  from real API `prompt_tokens`** (not LM-Studio-local counts), so the structural H2b saving holds on a
  commercial API. Over the 5-point axis Spearman(capability, gain) = **−0.90**.
- **Honesty caveats (loud).** (1) `$≠0` to PRODUCE (a one-time paid Ark run); $0 to SERVE (frozen fixtures).
  (2) deepseek supports **no** `response_format` (neither json_schema nor json_object), so it used
  **prompt-JSON** + `_extract_json` — a disclosed construction difference vs the strict-schema local rows
  (the task prompt embeds the JSON shape, so F1/capability are measured identically and remain comparable).
  (3) It is a **reasoning model** and is **non-deterministic run-to-run** even at temperature 0 (the pilot and
  the freeze returned different per-cell F1) — the **frozen fixture pins ONE sampled run** for reproducibility,
  same as every other model here. (4) It is flagged per-row (`provenance.source = ark-api`) and **never merged
  silently** into the $0/strict-schema local series. The genuine *frontier* (extreme-capability) point remains
  the browser GPT-5.5 one (naive F1 0.95, gain ≈0); deepseek corroborates the *middle* of the curve.
