import { describe, expect, it } from "vitest";
import { bandPath, type ChartDims, linePath, trajectoryColor, verdictBreaches, xOf, yOf } from "./sim";
import type { SimFrame, SimVerdict } from "./types";

const D: ChartDims = { width: 700, height: 300, padL: 40, padR: 20, padT: 10, padB: 30 };

describe("xOf", () => {
  it("maps frame 0 to the left edge and horizon to the right edge", () => {
    expect(xOf(0, 12, D)).toBeCloseTo(D.padL);
    expect(xOf(12, 12, D)).toBeCloseTo(D.width - D.padR);
    expect(xOf(6, 12, D)).toBeCloseTo((D.padL + (D.width - D.padR)) / 2);
  });
  it("does not divide by zero at horizon 0", () => {
    expect(Number.isFinite(xOf(0, 0, D))).toBe(true);
  });
});

describe("yOf", () => {
  it("puts the low value at the bottom and high at the top (inverted axis)", () => {
    expect(yOf(0, 0, 12, D)).toBeCloseTo(D.height - D.padB);
    expect(yOf(12, 0, 12, D)).toBeCloseTo(D.padT);
  });
  it("does not divide by zero when range is degenerate", () => {
    expect(Number.isFinite(yOf(5, 5, 5, D))).toBe(true);
  });
});

const frames: SimFrame[] = [
  { f: 0, lo: 2, mid: 2, hi: 2 },
  { f: 1, lo: 1, mid: 3, hi: 5 },
  { f: 2, lo: 2, mid: 4, hi: 6 },
];

describe("linePath", () => {
  it("starts with M then L commands, one per frame", () => {
    const p = linePath(frames, "mid", 2, 0, 12, D);
    expect(p.startsWith("M ")).toBe(true);
    expect((p.match(/L /g) ?? []).length).toBe(2);
  });
});

describe("bandPath", () => {
  it("is a closed path covering hi (forward) then lo (back)", () => {
    const p = bandPath(frames, 2, 0, 12, D);
    expect(p.startsWith("M ")).toBe(true);
    expect(p.endsWith("Z")).toBe(true);
    // forward 3 points (M + 2 L) + reverse 3 points (3 L) = 5 L total
    expect((p.match(/L /g) ?? []).length).toBe(5);
  });
  it("is empty for no frames", () => {
    expect(bandPath([], 2, 0, 12, D)).toBe("");
  });
});

describe("verdictBreaches (honesty: a breaching best is never 'good')", () => {
  const mk = (best: string, breaches: Record<string, number | null>): SimVerdict => ({
    objective: "avoid_breach",
    best_label: best,
    breaches,
    reason: "",
  });
  it("is false when the chosen best does not breach", () => {
    expect(verdictBreaches(mk("cut", { baseline: 2, cut: null }))).toBe(false);
  });
  it("is true when the chosen best breaches", () => {
    expect(verdictBreaches(mk("cut", { baseline: 1, cut: 5 }))).toBe(true);
  });
  it("is true even when best IS the baseline but it breaches (the bug we fixed)", () => {
    expect(verdictBreaches(mk("baseline", { baseline: 0, spike: 0 }))).toBe(true);
  });
});

describe("trajectoryColor", () => {
  it("uses a neutral colour for the baseline (index 0) and cycles for scenarios", () => {
    expect(trajectoryColor(0)).toBe("var(--muted)");
    expect(trajectoryColor(1)).not.toBe(trajectoryColor(0));
    expect(trajectoryColor(1)).toBe(trajectoryColor(6)); // palette of 5 wraps
  });
});
