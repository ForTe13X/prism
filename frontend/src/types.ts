// The semantic-foundation spec — mirrors backend/specs/*.json. This is the ONLY domain knowledge
// in the app; every component below renders as a pure function of these shapes.

export type SemanticType =
  | "identifier"
  | "category"
  | "status"
  | "metric"
  | "gauge"
  | "timeseries"
  | "text";

export interface Threshold {
  warn?: number;
  limit?: number;
}

export interface Attribute {
  name: string;
  label: string;
  label_en?: string;
  semantic_type: SemanticType;
  unit?: string;
  values?: string[];
  range?: [number, number];
  points?: number;
  threshold?: Threshold;
  prefix?: string;
  // P1 time-frame model: opt an attribute into per-frame evolution (absent ⇒ frame-invariant).
  evolves?: boolean;
  drift?: number;
}

export interface Entity {
  type: string;
  label: string;
  label_en?: string;
  icon?: string;
  count: number;
  attributes: Attribute[];
}

export interface Relation {
  from: string;
  predicate: string;
  to: string;
}

export interface View {
  id: string;
  title: string;
  title_en?: string;
  entity: string;
  layout: "cards" | "table";
}

// The replay axis for a domain (from /api/timeline). frames=1 ⇒ no time axis, no slider.
export interface Temporal {
  frames: number;
  now: number;
  step: string;
}

export interface Spec {
  id: string;
  title: string;
  title_en?: string;
  version: string;
  accent?: string;
  description?: string;
  temporal?: Temporal;
  entities: Entity[];
  relations: Relation[];
  views: View[];
}

export interface SpecSummary {
  id: string;
  title: string;
  title_en?: string;
  accent?: string;
  entity_count: number;
  view_count: number;
}

export type Row = Record<string, unknown>;

// P2 ontology graph (from /api/graph). Nodes are entity instances at a frame; edges are deterministic
// relation mappings. Topology is identity-stable across frames; only node `row` state evolves.
export interface GraphNode {
  id: string;
  entity_type: string;
  row: Row;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  predicate: string;
}

export interface Graph {
  spec_id: string;
  frame: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}
