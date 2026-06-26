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

// P3 trajectory simulation (POST /api/sim). A baseline + N what-if scenarios projected `horizon`
// frames past `now`, each with a min/median/max uncertainty band and threshold-breach detection.
export interface SimScenario {
  label: string;
  at: number;
  delta: number;
  mode: "shift" | "pulse"; // shift = setpoint change from `at` onward; pulse = one-time at `at`
}

export interface SimFrame {
  f: number;
  lo: number;
  mid: number;
  hi: number;
}

export interface SimTrajectory {
  label: string;
  frames: SimFrame[];
  breach_frame: number | null;
  terminal_mid: number;
}

export interface SimVerdict {
  objective: "avoid_breach" | "min_terminal";
  best_label: string;
  breaches: Record<string, number | null>;
  reason: string;
  limit?: number;
}

export interface SimResult {
  ok: boolean;
  spec_id: string;
  entity_type: string;
  attribute: string;
  row_index: number;
  baseline: number;
  now: number;
  horizon: number;
  range?: [number, number];
  unit?: string;
  threshold?: Threshold;
  dynamics: { model: string; rate: number };
  trajectories: SimTrajectory[];
  verdict: SimVerdict;
  confidence: { rolls: number; note: string };
}

export interface SimRequest {
  entity_type: string;
  attribute: string;
  horizon: number;
  row_index?: number | null;
  scenarios: SimScenario[];
}

// P3.5 sequential policy comparison (POST /api/policy). A policy is a typed IR of conditional rules
// (when the target crosses a trigger → nudge its setpoint); the engine compares candidate policies by
// robustness and runs a sensitivity pass. See docs/DESIGN_what_if_sequential.md.
export interface PolicyRule {
  when: { op: string; value: number };
  do: { action: "shift" | "pulse"; by: number };
  note?: string;
}

export interface PolicyIR {
  label: string;
  rules: PolicyRule[];
}

export interface PolicyTrajectory {
  label: string;
  frames: SimFrame[];
  breach_frame: number | null;
  breach_rate: number;
  terminal_mid: number;
  worst_terminal: number;
  rule_count: number;
}

export interface PolicyMetric {
  breach_rate: number;
  worst_terminal: number;
  terminal_mid: number;
}

export interface PolicyVerdict {
  objective: "avoid_breach" | "min_terminal";
  best_label: string;
  reason: string;
  metrics: Record<string, PolicyMetric>;
}

export interface PolicySensitivity {
  perturbed: { rate: number; volatility: number };
  best_label_perturbed: string;
  stable: boolean;
  note: string;
}

export interface PolicyResult {
  ok: boolean;
  spec_id: string;
  entity_type: string;
  attribute: string;
  row_index: number;
  baseline: number;
  now: number;
  horizon: number;
  range?: [number, number];
  unit?: string;
  threshold?: Threshold;
  dynamics: { model: string; rate: number; trend: number; volatility: number };
  policies: PolicyTrajectory[];
  verdict: PolicyVerdict;
  sensitivity: PolicySensitivity;
  confidence: { rolls: number; note: string };
}

export interface PolicyRequest {
  entity_type: string;
  attribute: string;
  horizon: number;
  row_index?: number | null;
  policies: PolicyIR[];
  assumptions?: { rate?: number | null; trend?: number | null; volatility?: number | null };
}
