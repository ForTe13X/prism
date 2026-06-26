// Pure geometry for the simulation chart — frame→x and value→y scales plus SVG path builders for a
// trajectory's median line and its lo–hi uncertainty band. No React, no domain knowledge; unit-tested.
import type { SimFrame, SimVerdict } from "./types";

// Does the verdict's chosen-best trajectory breach? Drives the verdict tone. Keyed SOLELY on the
// breach status of best_label — a breaching baseline must NOT read as "good" just for being baseline.
export function verdictBreaches(verdict: SimVerdict): boolean {
  return verdict.breaches[verdict.best_label] != null;
}

export interface ChartDims {
  width: number;
  height: number;
  padL: number;
  padR: number;
  padT: number;
  padB: number;
}

// frame 0 (now) sits at the left plot edge; frame `horizon` at the right edge.
export function xOf(f: number, horizon: number, d: ChartDims): number {
  const span = horizon || 1;
  return d.padL + (f / span) * (d.width - d.padL - d.padR);
}

// value `lo` at the bottom of the plot, `hi` at the top (y grows downward, so it's inverted).
export function yOf(v: number, lo: number, hi: number, d: ChartDims): number {
  const span = hi - lo || 1;
  return d.height - d.padB - ((v - lo) / span) * (d.height - d.padT - d.padB);
}

// Polyline through one band key ("lo" | "mid" | "hi") of a trajectory.
export function linePath(
  frames: SimFrame[],
  key: "lo" | "mid" | "hi",
  horizon: number,
  lo: number,
  hi: number,
  d: ChartDims,
): string {
  return frames
    .map((fr, i) => `${i ? "L" : "M"} ${xOf(fr.f, horizon, d).toFixed(1)} ${yOf(fr[key], lo, hi, d).toFixed(1)}`)
    .join(" ");
}

// Closed area between the hi (top) and lo (bottom) bounds — the uncertainty band.
export function bandPath(frames: SimFrame[], horizon: number, lo: number, hi: number, d: ChartDims): string {
  if (frames.length === 0) return "";
  const top = frames
    .map((fr, i) => `${i ? "L" : "M"} ${xOf(fr.f, horizon, d).toFixed(1)} ${yOf(fr.hi, lo, hi, d).toFixed(1)}`)
    .join(" ");
  const bottom = [...frames]
    .reverse()
    .map((fr) => `L ${xOf(fr.f, horizon, d).toFixed(1)} ${yOf(fr.lo, lo, hi, d).toFixed(1)}`)
    .join(" ");
  return `${top} ${bottom} Z`;
}

// Stable colour per trajectory by index — baseline (index 0) is neutral, scenarios cycle a palette.
const SCENARIO_COLORS = ["var(--accent)", "#8a5a2f", "#1f8a4c", "#7a3fb0", "#b7791f"];
export function trajectoryColor(index: number): string {
  return index === 0 ? "var(--muted)" : SCENARIO_COLORS[(index - 1) % SCENARIO_COLORS.length];
}
