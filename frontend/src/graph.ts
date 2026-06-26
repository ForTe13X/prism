// Pure, domain-agnostic helpers for the ontology canvas. No React, no fetch — just geometry and
// the spec-driven rule for what colours a node. Kept separate so the layout math is unit-testable.
import type { Attribute, GraphNode, Row } from "./types";

export interface NodePos {
  x: number;
  y: number;
}

export interface LayoutDims {
  width: number;
  height: number;
  padX: number;
  padY: number;
}

// A node is coloured by its first `status`-typed attribute (the domain-agnostic convention shared
// with the widget resolver). Entities with no status attribute stay neutral.
export function statusValue(attributes: Attribute[], row: Row): string | null {
  const attr = attributes.find((a) => a.semantic_type === "status");
  if (!attr) return null;
  const v = row[attr.name];
  return v == null ? null : String(v);
}

// Deterministic layered layout: one column per entity type (in `typeOrder`), nodes spaced evenly
// down their column. Stable across frames — replay only recolours nodes, it never reflows the graph.
export function layoutGraph(
  nodes: GraphNode[],
  typeOrder: string[],
  dims: LayoutDims,
): Map<string, NodePos> {
  const { width, height, padX, padY } = dims;
  const columns = typeOrder.filter((t) => nodes.some((n) => n.entity_type === t));
  const pos = new Map<string, NodePos>();
  columns.forEach((type, ci) => {
    const colNodes = nodes.filter((n) => n.entity_type === type);
    const x = columns.length <= 1 ? width / 2 : padX + (ci * (width - 2 * padX)) / (columns.length - 1);
    colNodes.forEach((n, ri) => {
      const y =
        colNodes.length <= 1 ? height / 2 : padY + (ri * (height - 2 * padY)) / (colNodes.length - 1);
      pos.set(n.id, { x, y });
    });
  });
  return pos;
}

// Height that comfortably fits the fullest column (each node ~`rowGap` px tall, plus padding).
export function graphHeight(nodes: GraphNode[], typeOrder: string[], rowGap = 46, min = 360): number {
  const maxCol = Math.max(
    0,
    ...typeOrder.map((t) => nodes.filter((n) => n.entity_type === t).length),
  );
  return Math.max(min, 2 * 40 + maxCol * rowGap);
}
