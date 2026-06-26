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

export interface Spec {
  id: string;
  title: string;
  title_en?: string;
  version: string;
  accent?: string;
  description?: string;
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
