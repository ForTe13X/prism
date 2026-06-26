import { useEffect, useMemo, useState } from "react";
import { fetchData, fetchTimeline } from "./api";
import OntologyGraph from "./OntologyGraph";
import { frameLabel, stepUnit } from "./time";
import type { Entity, Row, Spec, Temporal, View } from "./types";
import { renderWidget } from "./widgets";

// A synthetic tab id for the built-in ontology graph view (P2). Never collides with a spec view id
// (those are plain slugs), so it lives alongside the spec's own views.
const GRAPH_TAB = "__prism_graph__";

function EntityCard({ entity, row }: { entity: Entity; row: Row }) {
  const idAttr = entity.attributes.find((a) => a.semantic_type === "identifier");
  const rest = entity.attributes.filter((a) => a !== idAttr);
  return (
    <div className="pr-card">
      <div className="pr-card-head">
        <span className="pr-card-icon">{entity.icon ?? "◆"}</span>
        <span className="pr-card-title">{idAttr ? String(row[idAttr.name]) : String(row._id)}</span>
      </div>
      <dl className="pr-card-body">
        {rest.map((attr) => (
          <div className="pr-field" key={attr.name}>
            <dt>{attr.label}</dt>
            <dd>{renderWidget(attr, row[attr.name])}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function EntityTable({ entity, rows }: { entity: Entity; rows: Row[] }) {
  return (
    <div className="pr-table-wrap">
      <table className="pr-table">
        <thead>
          <tr>
            {entity.attributes.map((a) => (
              <th key={a.name}>{a.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row._id)}>
              {entity.attributes.map((a) => (
                <td key={a.name}>{renderWidget(a, row[a.name])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// The replay slider: one shared frame across every widget. Domain-agnostic — it only knows the
// {frames, now, step} axis the spec declared, never anything about the domain itself.
function ReplaySlider({
  timeline,
  frame,
  onFrame,
  playing,
  onTogglePlay,
}: {
  timeline: Temporal;
  frame: number;
  onFrame: (f: number) => void;
  playing: boolean;
  onTogglePlay: () => void;
}) {
  const { frames, now, step } = timeline;
  const max = frames - 1;
  const nowPct = max > 0 ? (now / max) * 100 : 0;
  return (
    <div className="pr-replay">
      <button
        className="pr-play"
        onClick={onTogglePlay}
        aria-label={playing ? "暂停" : "播放"}
        title={playing ? "暂停" : "逐帧播放"}
      >
        {playing ? "⏸" : "▶"}
      </button>
      <div className="pr-replay-track">
        <input
          className="pr-range"
          type="range"
          min={0}
          max={max}
          step={1}
          value={frame}
          aria-label="回放帧"
          onChange={(e) => onFrame(Number(e.target.value))}
        />
        <span className="pr-now-mark" style={{ left: `${nowPct}%` }} title="现在" />
      </div>
      <div className="pr-replay-meta">
        <span className="pr-frame-label">{frameLabel(frame, now, step)}</span>
        <span className="pr-frame-count">
          帧 {frame} / {max} · 每帧 1 {stepUnit(step)}
        </span>
      </div>
    </div>
  );
}

function ViewPanel({ spec, view, frame }: { spec: Spec; view: View; frame?: number }) {
  const entity = useMemo(() => spec.entities.find((e) => e.type === view.entity), [spec, view]);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string>("");

  // Show the loader only when the dataset itself changes (domain / entity). Frame changes keep the
  // previous rows on screen and swap them in when the new frame arrives — no flicker while scrubbing.
  useEffect(() => {
    setRows(null);
    setError("");
  }, [spec.id, view.entity]);

  useEffect(() => {
    let cancelled = false;
    fetchData(spec.id, view.entity, frame)
      // clear any prior error on success — otherwise one transient failure mid-scrub would latch
      // the error screen even as later frames fetch fine.
      .then((r) => {
        if (cancelled) return;
        setError("");
        setRows(r);
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [spec.id, view.entity, frame]);

  if (!entity) return <p className="pr-muted">spec 中无实体 “{view.entity}”。</p>;
  if (error) return <p className="pr-error">加载失败:{error}</p>;
  if (!rows) return <p className="pr-muted">加载中…</p>;

  return (
    <>
      <p className="pr-view-meta">
        {entity.icon} {entity.label} · {rows.length} 行 · 布局 <code>{view.layout}</code> · 控件由各属性的
        <code> semantic_type </code>自动决定
      </p>
      {view.layout === "table" ? (
        <EntityTable entity={entity} rows={rows} />
      ) : (
        <div className="pr-grid">
          {rows.map((row) => (
            <EntityCard key={String(row._id)} entity={entity} row={row} />
          ))}
        </div>
      )}
    </>
  );
}

export default function Cockpit({ spec }: { spec: Spec }) {
  const [activeId, setActiveId] = useState(spec.views[0]?.id);
  const [timeline, setTimeline] = useState<Temporal | null>(null);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);

  // reset to the first view whenever the domain (spec) changes
  useEffect(() => setActiveId(spec.views[0]?.id), [spec.id]);

  // load the replay axis for this domain; park the slider at `now` and stop any playback
  useEffect(() => {
    let cancelled = false;
    setPlaying(false);
    setTimeline(null);
    fetchTimeline(spec.id)
      .then((t) => {
        if (cancelled) return;
        setTimeline(t);
        setFrame(t.now);
      })
      .catch(() => !cancelled && setTimeline(null));
    return () => {
      cancelled = true;
    };
  }, [spec.id]);

  // playback: advance one frame at a time, looping back to the start at the end
  const frames = timeline?.frames ?? 1;
  useEffect(() => {
    if (!playing || frames <= 1) return;
    const id = setInterval(() => setFrame((f) => (f + 1 >= frames ? 0 : f + 1)), 700);
    return () => clearInterval(id);
  }, [playing, frames]);

  const isGraph = activeId === GRAPH_TAB;
  const view = isGraph ? undefined : spec.views.find((v) => v.id === activeId) ?? spec.views[0];
  const hasAxis = !!timeline && timeline.frames > 1;
  const showGraphTab = spec.entities.length > 0;

  return (
    <section className="pr-cockpit">
      {hasAxis && (
        <ReplaySlider
          timeline={timeline}
          frame={frame}
          onFrame={(f) => {
            setPlaying(false);
            setFrame(f);
          }}
          playing={playing}
          onTogglePlay={() => setPlaying((p) => !p)}
        />
      )}
      <nav className="pr-tabs">
        {spec.views.map((v) => (
          <button
            key={v.id}
            className={v.id === view?.id ? "pr-tab is-active" : "pr-tab"}
            onClick={() => setActiveId(v.id)}
          >
            {v.title}
          </button>
        ))}
        {showGraphTab && (
          <button
            key={GRAPH_TAB}
            className={isGraph ? "pr-tab is-active" : "pr-tab"}
            onClick={() => setActiveId(GRAPH_TAB)}
          >
            🕸 本体图谱
          </button>
        )}
      </nav>
      {isGraph && showGraphTab ? (
        <OntologyGraph spec={spec} frame={hasAxis ? frame : undefined} />
      ) : view ? (
        <ViewPanel spec={spec} view={view} frame={hasAxis ? frame : undefined} />
      ) : (
        <p className="pr-muted">该 spec 未定义视图。</p>
      )}
    </section>
  );
}
