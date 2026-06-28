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

// P6 LLM compile (POST /api/compile). The LLM turns NL → a policy IR (rules only, NO numbers); the
// result is a suggestion for the human to confirm/edit before the deterministic engine runs it.
export interface CompileRequest {
  entity_type: string;
  attribute: string;
  nl: string;
}

export interface CompileResult {
  ok: boolean;
  spec_id: string;
  entity_type: string;
  attribute: string;
  rules: PolicyRule[];
  model: string;
  source: string;
}

export interface LlmHealth {
  reachable: boolean;
  base_url: string;
  model: string;
  models: string[];
  compile_calls: number;
  compile_failures: number;
  last_error?: string | null;
}

// Phase-B cross-domain nexus view — per-bridge confidence for one coupled package (METRIC §8c/§8d).
export interface NexusUnit {
  idx: number;
  id: string;
  anchor: boolean;
}
export interface NexusBridge {
  a_idx: number;
  b_idx: number;
  a_id: string;
  b_id: string;
  shape: number;
  fingerprint: number;
  shape_fires: boolean;
  fingerprint_fires: boolean;
  confidence: "high" | "medium" | "coincidence";
  dissent: boolean;
}
export interface NexusView {
  seed: string;
  A: { prefix: string; metric: string; units: NexusUnit[] };
  B: { prefix: string; metric: string; units: NexusUnit[] };
  bridges: NexusBridge[];
  scorecard: {
    candidates: number;
    high: number;
    medium: number;
    coincidence: number;
    true_couplings: number;
    high_tier_precision: number | null;
    fdr_q: number;
    null_samples: number;
    expected_false_high: number;
  };
  caveat: string;
}

// Sinkhorn alignment — the animated "money moment" data (residual + transport snapshots per iteration).
export interface NexusAlignSnapshot {
  iter: number;
  residual: number;
  transport: number[][]; // [anchor-A index][anchor-B index] mass at this iteration
}
export interface NexusAlign {
  seed: string;
  n_anchor_a: number;
  n_anchor_b: number;
  iters: number;
  reg: number;
  residuals: number[];
  snapshots: NexusAlignSnapshot[];
  pairs: { a_idx: number; b_idx: number; transport: number; cost: number; real: boolean }[];
  note: string;
}

// Axiom-gain (RESEARCH_axiom_gain) — the surviving, citable line: structured semantic foundation vs bare RAG.
export interface AxiomMatrixCell {
  model: string;
  dirtiness: number;
  quality_delta_mean: number;
  quality_delta_ci95: [number, number];
  quality_delta_excludes_0: boolean;
  token_saving_mean: number;
  token_saving_excludes_0: boolean;
  naive_f1: number;
  axiom_f1: number;
}
export interface AxiomProtocol {
  models: string[];
  dirts: number[];
  matrix: AxiomMatrixCell[];
  headline: {
    mean_input_token_saving: number;
    token_saving_significant_cells: string;
    quality_gain_significant_cells: string;
    min_quality_delta: number;
    models_monotonic_in_dirt: string;
    axiom_pareto_dominant: boolean;
  };
  build_amortization: {
    breakeven_N_dictionary: number | null;
    structural_gain_buildfree: number;
    learned_dictionary_gain: number;
  };
  h2_capability_vs_gain: H2CapabilityAxis;
  honest_verdict: string;
}

// PREREG H2 (capability×gain): the QUALITY gain shrinks as the model gets more capable (H2a), while the TOKEN
// saving is structural ⇒ ~model-independent (H2b). `by_capability_ascending` is the reproducible (fixture)
// series; `frontier_manual` is a Tier-2 DISCLOSED MANUAL point (browser-captured GPT-5.5, NOT reproducible),
// flagged + never merged into the reproducible series.
export interface H2CapabilityRow {
  model: string;
  capability_naive_f1: number;
  quality_gain: number;
  token_saving: number;
  provenance: { source: string; cost: string; structured: string; reproducible: boolean };
}
export interface H2FrontierManual {
  model: string;
  source: string;
  reproducible: boolean;
  capability_naive_f1: number;
  quality_gain: number;
  token_saving: number | null;
  confirm_rule: string;
  confirm_comparator_model: string | null;
  confirm_comparator_gain: number | null;
  confirm_rule_met: boolean;
  caveat: string;
}
export interface H2CapabilityAxis {
  capability_proxy: string;
  by_capability_ascending: H2CapabilityRow[];
  spearman_capability_gain: number | null;
  quality_gain_monotone_decreasing: boolean;
  token_saving_spread: number;
  "token_saving_is_structural_flat(<0.05)": boolean;
  note: string;
  frontier_manual: H2FrontierManual | null;
}

// Coupling external validity on REAL paired data (§8j): a coupling-strength spectrum — near-duplicate vs genuine cross-aspect.
export interface NexusRealCouplingPoint {
  mean_cross_corr: number;
  same_base_diag_corr?: number;
  raw_value_match_auc: number;
  semantic_zscore_auc: number;
  resolver_top1_acc: number;
  resolver_mutual_acc: number;
}
export interface NexusRealCoupling {
  n: number;
  chance_top1: number;
  same_feature_near_duplicate: NexusRealCouplingPoint;
  disjoint_feature_cross_aspect: NexusRealCouplingPoint;
}

// §6c channel-blind discriminability gate (nexus): oracle recovers, naive baselines ~chance ⇒ difficulty well-posed.
export interface NexusGate {
  seeds: number;
  n_candidates: number;
  n_positives: number;
  prevalence: number;
  oracle_auc: number;
  time_auc: number;
  depth_auc: number;
  string_auc: number;
  gate_pass: boolean;
}

// Cross-domain coreference ablation on the split substrate — structured foundation ENABLES an impossible-from-raw task.
export interface SplitCondition {
  model: string;
  condition: string; // "naive-RAG" | "axiom-RAG"
  quality_f1: number;
  avg_in_tok: number;
  truncated_calls: number;
}
export interface SplitAblation {
  conditions: SplitCondition[];
  gains: { model: string; quality_delta: number; input_token_saving: number }[];
  resolver_accuracy: { link_precision: number; link_recall: number; answer_f1_mean: number };
  honest_verdict: string;
}
