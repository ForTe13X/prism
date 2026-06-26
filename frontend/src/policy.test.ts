import { describe, expect, it } from "vitest";
import { bestStillBreaches, pctSpan } from "./policy";
import type { PolicyResult } from "./types";

const base = (best: string, metrics: PolicyResult["verdict"]["metrics"]): PolicyResult =>
  ({
    ok: true,
    spec_id: "s",
    entity_type: "e",
    attribute: "a",
    row_index: 0,
    baseline: 0,
    now: 0,
    horizon: 10,
    dynamics: { model: "mean_revert", rate: 0.2, trend: 0, volatility: 0.1 },
    policies: [],
    verdict: { objective: "avoid_breach", best_label: best, reason: "", metrics },
    sensitivity: { perturbed: { rate: 0.1, volatility: 0.15 }, best_label_perturbed: best, stable: true, note: "" },
    confidence: { rolls: 9, note: "" },
  }) as PolicyResult;

describe("bestStillBreaches (honesty: a breaching best is never 'good')", () => {
  it("false when the best policy avoids breaches", () => {
    expect(bestStillBreaches(base("relief", { relief: { breach_rate: 0, worst_terminal: 6, terminal_mid: 6 } }))).toBe(false);
  });
  it("true when even the best policy still breaches", () => {
    expect(bestStillBreaches(base("relief", { relief: { breach_rate: 0.4, worst_terminal: 11, terminal_mid: 10 } }))).toBe(true);
  });
});

describe("pctSpan", () => {
  it("formats signed fractions of span as percents", () => {
    expect(pctSpan(-0.3)).toBe("−30%");
    expect(pctSpan(0.25)).toBe("+25%");
    expect(pctSpan(0)).toBe("0%");
  });
});
