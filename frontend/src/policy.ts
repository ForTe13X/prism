// Pure, domain-agnostic helpers for the policy-comparison view. No React, no fetch — unit-tested.
import type { PolicyResult } from "./types";

// Does the chosen-best policy still breach? Drives the verdict tone. Honesty: a best policy that
// still breaches (because NO playbook avoids it) must NOT read as "good".
export function bestStillBreaches(result: PolicyResult): boolean {
  const m = result.verdict.metrics[result.verdict.best_label];
  return !!m && m.breach_rate > 0;
}

// Format a fraction-of-span Δ as a signed percent, e.g. -0.3 → "−30%".
export function pctSpan(by: number): string {
  const sign = by < 0 ? "−" : by > 0 ? "+" : "";
  return `${sign}${Math.round(Math.abs(by) * 100)}%`;
}
