import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Attribute } from "./types";
import { renderWidget } from "./widgets";

// Resolver = a pure function (semantic_type, value) → markup. We snapshot each branch so any
// accidental change to how a semantic_type renders is caught, and assert the load-bearing classes
// (status tone, gauge tone/width, sparkline breach) explicitly.
const html = (attr: Attribute, value: unknown) => renderToStaticMarkup(renderWidget(attr, value));

const A = (over: Partial<Attribute>): Attribute => ({
  name: "x",
  label: "X",
  semantic_type: "text",
  ...over,
});

describe("renderWidget snapshots", () => {
  it("identifier", () => {
    expect(html(A({ semantic_type: "identifier" }), "STN-001")).toMatchSnapshot();
  });
  it("category", () => {
    expect(html(A({ semantic_type: "category" }), "华北")).toMatchSnapshot();
  });
  it("metric with unit", () => {
    expect(html(A({ semantic_type: "metric", unit: "MPa" }), 42.5)).toMatchSnapshot();
  });
  it("gauge with threshold", () => {
    expect(
      html(A({ semantic_type: "gauge", unit: "MPa", range: [0, 12], threshold: { warn: 9, limit: 10 } }), 9.5),
    ).toMatchSnapshot();
  });
  it("timeseries", () => {
    expect(
      html(A({ semantic_type: "timeseries", range: [0, 12], threshold: { limit: 7 } }), [1, 5, 8, 3]),
    ).toMatchSnapshot();
  });
  it("text", () => {
    expect(html(A({ semantic_type: "text" }), "巡检正常")).toMatchSnapshot();
  });
});

describe("status tone is domain-agnostic", () => {
  const status = A({ semantic_type: "status", values: [] });
  it.each([
    ["normal", "tone-good"],
    ["warning", "tone-warn"],
    ["critical", "tone-bad"],
    ["available", "tone-good"],
    ["overdue", "tone-bad"],
    ["mystery_value", "tone-neutral"],
  ])("%s → %s", (value, tone) => {
    expect(html(status, value)).toContain(tone);
  });
});

describe("gauge encodes threshold breach", () => {
  const gauge = A({ semantic_type: "gauge", range: [0, 12], threshold: { warn: 9, limit: 10 } });
  it("at/above limit is bad", () => {
    expect(html(gauge, 11)).toContain("tone-bad");
  });
  it("between warn and limit is warn", () => {
    expect(html(gauge, 9.5)).toContain("tone-warn");
  });
  it("below warn is good", () => {
    expect(html(gauge, 3)).toContain("tone-good");
  });
});

describe("timeseries flags a breach", () => {
  const ts = A({ semantic_type: "timeseries", range: [0, 12], threshold: { limit: 7 } });
  it("marks the line as breached when a point crosses the limit", () => {
    expect(html(ts, [1, 2, 9, 3])).toContain("is-breach");
  });
  it("no breach class when all points stay under the limit", () => {
    expect(html(ts, [1, 2, 3, 4])).not.toContain("is-breach");
  });
});
