// The widget resolver: the ONE place that maps a semantic_type → a rendered widget. Add a new
// semantic type here and every spec that uses it renders — no per-domain code anywhere else.
import type { Attribute } from "./types";

// Status value tokens → a tone. Domain-agnostic: any spec's status values map by these conventions.
const GOOD = new Set(["normal", "ok", "available", "open", "healthy", "online", "good"]);
const WARN = new Set(["warning", "warn", "degraded", "busy", "on_loan", "pending", "elevated"]);
const BAD = new Set(["critical", "fault", "overdue", "closed", "error", "offline", "down"]);

export function statusTone(value: string): "good" | "warn" | "bad" | "neutral" {
  const v = String(value).toLowerCase();
  if (GOOD.has(v)) return "good";
  if (WARN.has(v)) return "warn";
  if (BAD.has(v)) return "bad";
  return "neutral";
}

function Sparkline({ series, range, limit }: { series: number[]; range?: [number, number]; limit?: number }) {
  const w = 140;
  const h = 36;
  const pad = 3;
  const lo = range?.[0] ?? Math.min(...series);
  const hi = range?.[1] ?? Math.max(...series);
  const span = hi - lo || 1;
  const x = (i: number) => pad + (i * (w - 2 * pad)) / Math.max(1, series.length - 1);
  const y = (v: number) => h - pad - ((v - lo) / span) * (h - 2 * pad);
  const pts = series.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const breach = limit != null && series.some((v) => v >= limit);
  return (
    <svg className="pr-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img">
      {limit != null && (
        <line className="pr-spark-limit" x1={pad} x2={w - pad} y1={y(limit)} y2={y(limit)} />
      )}
      <polyline className={breach ? "pr-spark-line is-breach" : "pr-spark-line"} points={pts} />
    </svg>
  );
}

function Gauge({ value, range, threshold }: { value: number; range?: [number, number]; threshold?: Attribute["threshold"] }) {
  const lo = range?.[0] ?? 0;
  const hi = range?.[1] ?? 100;
  const pct = Math.max(0, Math.min(1, (value - lo) / (hi - lo || 1)));
  // Convention: threshold values are UPPER bounds — at/above them is worse.
  let tone = "good";
  if (threshold?.limit != null && value >= threshold.limit) tone = "bad";
  else if (threshold?.warn != null && value >= threshold.warn) tone = "warn";
  else if (!threshold) tone = "accent";
  const mark = (t?: number) => (t == null ? null : ((t - lo) / (hi - lo || 1)) * 100);
  return (
    <div className="pr-gauge">
      <div className="pr-gauge-track">
        <div className={`pr-gauge-fill tone-${tone}`} style={{ width: `${pct * 100}%` }} />
        {threshold?.warn != null && <span className="pr-gauge-mark warn" style={{ left: `${mark(threshold.warn)}%` }} />}
        {threshold?.limit != null && <span className="pr-gauge-mark limit" style={{ left: `${mark(threshold.limit)}%` }} />}
      </div>
    </div>
  );
}

export function renderWidget(attr: Attribute, value: unknown) {
  switch (attr.semantic_type) {
    case "identifier":
      return <span className="pr-id">{String(value ?? "—")}</span>;
    case "category":
      return <span className="pr-pill">{String(value ?? "—")}</span>;
    case "status":
      return <span className={`pr-badge tone-${statusTone(String(value))}`}>{String(value ?? "—")}</span>;
    case "metric":
      return (
        <span className="pr-metric">
          <b>{typeof value === "number" ? value : "—"}</b>
          {attr.unit && attr.unit !== "—" ? <i className="pr-unit"> {attr.unit}</i> : null}
        </span>
      );
    case "gauge":
      return (
        <div className="pr-gauge-wrap">
          <Gauge value={Number(value)} range={attr.range} threshold={attr.threshold} />
          <span className="pr-gauge-val">
            {typeof value === "number" ? value : "—"}
            {attr.unit && attr.unit !== "—" ? <i className="pr-unit"> {attr.unit}</i> : null}
          </span>
        </div>
      );
    case "timeseries":
      return Array.isArray(value) ? (
        <Sparkline series={value as number[]} range={attr.range} limit={attr.threshold?.limit} />
      ) : (
        <span className="pr-muted">—</span>
      );
    case "text":
      return <span className="pr-muted">{String(value ?? "—")}</span>;
    default:
      return <span className="pr-muted">{String(value ?? "—")}</span>;
  }
}
