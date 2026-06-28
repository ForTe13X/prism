// Pure helpers for the Axiom-Gain panel (kept separate so they're unit-testable, like graph.ts / sim.ts).
import type { SplitAblation, SplitCondition } from "./types";

/** Parse a "8/12" significance fraction into its parts + ratio (den=0 → ratio 0). */
export function parseFrac(s: string): { num: number; den: number; ratio: number } {
  const [num, den] = (s ?? "").split("/").map((x) => Number(x));
  const n = Number.isFinite(num) ? num : 0;
  const d = Number.isFinite(den) ? den : 0;
  return { num: n, den: d, ratio: d > 0 ? n / d : 0 };
}

export const pct = (x: number, digits = 0): string => `${(x * 100).toFixed(digits)}%`;

/** The two conditions for one model in the split ablation, as {naive, axiom}. */
export function splitPair(ab: SplitAblation, model: string): { naive?: SplitCondition; axiom?: SplitCondition } {
  const of = (cond: string) => ab.conditions.find((c) => c.model === model && c.condition === cond);
  return { naive: of("naive-RAG"), axiom: of("axiom-RAG") };
}

/** Distinct models in the split ablation, in first-seen order. */
export function splitModels(ab: SplitAblation): string[] {
  const seen: string[] = [];
  for (const c of ab.conditions) if (!seen.includes(c.model)) seen.push(c.model);
  return seen;
}
