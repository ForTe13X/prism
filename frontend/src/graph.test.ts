import { describe, expect, it } from "vitest";
import { graphHeight, layoutGraph, statusValue } from "./graph";
import type { Attribute, GraphNode } from "./types";

const mkNodes = (counts: Record<string, number>): GraphNode[] =>
  Object.entries(counts).flatMap(([type, n]) =>
    Array.from({ length: n }, (_, i) => ({ id: `${type}-${i}`, entity_type: type, row: { _id: `${type}-${i}` } })),
  );

const DIMS = { width: 760, height: 400, padX: 90, padY: 44 };

describe("statusValue", () => {
  const attrs: Attribute[] = [
    { name: "name", label: "N", semantic_type: "identifier" },
    { name: "state", label: "S", semantic_type: "status", values: [] },
  ];
  it("reads the first status attribute's value", () => {
    expect(statusValue(attrs, { state: "critical" })).toBe("critical");
  });
  it("is null when there is no status attribute", () => {
    expect(statusValue([{ name: "x", label: "X", semantic_type: "metric" }], { x: 5 })).toBeNull();
  });
  it("is null when the value is missing", () => {
    expect(statusValue(attrs, {})).toBeNull();
  });
});

describe("layoutGraph", () => {
  it("places every node within the padded bounds, one column per type", () => {
    const nodes = mkNodes({ a: 3, b: 5 });
    const pos = layoutGraph(nodes, ["a", "b"], DIMS);
    expect(pos.size).toBe(8);
    const xs = new Set([...pos.values()].map((p) => Math.round(p.x)));
    expect(xs.size).toBe(2); // two distinct columns
    for (const p of pos.values()) {
      expect(p.x).toBeGreaterThanOrEqual(DIMS.padX);
      expect(p.x).toBeLessThanOrEqual(DIMS.width - DIMS.padX);
      expect(p.y).toBeGreaterThanOrEqual(DIMS.padY);
      expect(p.y).toBeLessThanOrEqual(DIMS.height - DIMS.padY);
    }
  });
  it("centres a single column / single node", () => {
    const pos = layoutGraph(mkNodes({ solo: 1 }), ["solo"], DIMS);
    expect(pos.get("solo-0")).toEqual({ x: DIMS.width / 2, y: DIMS.height / 2 });
  });
  it("is deterministic and ignores types absent from the nodes", () => {
    const nodes = mkNodes({ a: 2 });
    const a = layoutGraph(nodes, ["ghost", "a"], DIMS);
    const b = layoutGraph(nodes, ["ghost", "a"], DIMS);
    expect([...a.entries()]).toEqual([...b.entries()]);
    // 'ghost' has no nodes, so 'a' is the only column → centred
    expect(a.get("a-0")?.x).toBe(DIMS.width / 2);
  });
});

describe("graphHeight", () => {
  it("grows with the fullest column and respects the floor", () => {
    expect(graphHeight(mkNodes({ a: 1, b: 1 }), ["a", "b"])).toBe(360); // floor
    expect(graphHeight(mkNodes({ a: 2, b: 14 }), ["a", "b"])).toBe(2 * 40 + 14 * 46);
  });
});
