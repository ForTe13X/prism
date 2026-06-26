import type { Graph, Row, Spec, SpecSummary, Temporal } from "./types";

// The Vite dev server talks to the Prism backend. Override with VITE_API_BASE if you change the port.
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8200";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return (await res.json()) as T;
}

export const fetchSpecs = () => getJSON<{ specs: SpecSummary[] }>("/api/specs").then((d) => d.specs);

export const fetchSpec = (specId: string) => getJSON<Spec>(`/api/spec/${specId}`);

export const fetchTimeline = (specId: string) =>
  getJSON<Temporal & { spec_id: string }>(`/api/timeline/${specId}`);

// Rows for one entity at a frame. Omit `frame` to let the backend default to the spec's `now`.
export const fetchData = (specId: string, entityType: string, frame?: number) =>
  getJSON<{ rows: Row[] }>(
    `/api/data/${specId}/${entityType}${frame == null ? "" : `?frame=${frame}`}`,
  ).then((d) => d.rows);

// The instance graph at a frame (nodes + edges). Omit `frame` to default to the spec's `now`.
export const fetchGraph = (specId: string, frame?: number) =>
  getJSON<Graph>(`/api/graph/${specId}${frame == null ? "" : `?frame=${frame}`}`);
