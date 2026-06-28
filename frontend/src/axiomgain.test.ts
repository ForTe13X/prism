import { describe, expect, it } from "vitest";
import { parseFrac, pct, splitModels, splitPair } from "./axiomgain";
import type { SplitAblation } from "./types";

describe("parseFrac", () => {
  it("parses a significance fraction into parts + ratio", () => {
    expect(parseFrac("8/12")).toEqual({ num: 8, den: 12, ratio: 8 / 12 });
    expect(parseFrac("12/12").ratio).toBe(1);
  });
  it("is safe on empty / malformed input (no NaN, no divide-by-zero)", () => {
    expect(parseFrac("")).toEqual({ num: 0, den: 0, ratio: 0 });
    expect(parseFrac("3/0").ratio).toBe(0);
  });
});

describe("pct", () => {
  it("formats a 0..1 ratio as a percentage", () => {
    expect(pct(0.6147)).toBe("61%");
    expect(pct(0.852, 1)).toBe("85.2%");
  });
});

const AB: SplitAblation = {
  conditions: [
    { model: "qwen-3-8b-instruct", condition: "naive-RAG", quality_f1: 0.0, avg_in_tok: 3501, truncated_calls: 0 },
    { model: "qwen-3-8b-instruct", condition: "axiom-RAG", quality_f1: 0.656, avg_in_tok: 536, truncated_calls: 0 },
    { model: "google/gemma-4-12b-qat", condition: "naive-RAG", quality_f1: 0.113, avg_in_tok: 3532, truncated_calls: 5 },
    { model: "google/gemma-4-12b-qat", condition: "axiom-RAG", quality_f1: 0.505, avg_in_tok: 524, truncated_calls: 3 },
  ],
  gains: [
    { model: "qwen-3-8b-instruct", quality_delta: 0.656, input_token_saving: 0.847 },
    { model: "google/gemma-4-12b-qat", quality_delta: 0.392, input_token_saving: 0.852 },
  ],
  resolver_accuracy: { link_precision: 0.692, link_recall: 0.75, answer_f1_mean: 0.662 },
  honest_verdict: "…",
};

describe("split helpers", () => {
  it("lists distinct models in first-seen order", () => {
    expect(splitModels(AB)).toEqual(["qwen-3-8b-instruct", "google/gemma-4-12b-qat"]);
  });
  it("pairs naive + axiom for a model", () => {
    const { naive, axiom } = splitPair(AB, "qwen-3-8b-instruct");
    expect(naive?.quality_f1).toBe(0.0);
    expect(axiom?.quality_f1).toBe(0.656);
    expect(axiom?.truncated_calls).toBe(0);
  });
});
