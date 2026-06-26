import { useEffect, useMemo, useRef, useState } from "react";
import { runSimulation } from "./api";
import { bandPath, type ChartDims, linePath, trajectoryColor, verdictBreaches, xOf, yOf } from "./sim";
import { stepUnit } from "./time";
import type { Attribute, SimResult, SimScenario, Spec } from "./types";

const NUMERIC = new Set(["metric", "gauge", "timeseries"]);
const isNumeric = (a: Attribute) => NUMERIC.has(a.semantic_type);
const DIMS: ChartDims = { width: 760, height: 320, padL: 46, padR: 18, padT: 16, padB: 30 };

// Scenario identity is a stable client-side id (NOT the user-editable label) so React keys, focus,
// and trajectory matching survive renames and removals without collisions.
type Scenario = SimScenario & { id: number };

function defaultTarget(spec: Spec): { entityType: string; attribute: string } | null {
  for (const e of spec.entities) {
    const g = e.attributes.find((a) => a.semantic_type === "gauge" && a.threshold?.limit != null);
    if (g) return { entityType: e.type, attribute: g.name };
  }
  for (const e of spec.entities) {
    const n = e.attributes.find(isNumeric);
    if (n) return { entityType: e.type, attribute: n.name };
  }
  return null;
}

export default function SimView({ spec }: { spec: Spec }) {
  const target0 = useMemo(() => defaultTarget(spec), [spec]);
  const [entityType, setEntityType] = useState(target0?.entityType ?? "");
  const [attribute, setAttribute] = useState(target0?.attribute ?? "");
  const [rowIndex, setRowIndex] = useState<number | null>(null); // null = engine picks most-at-risk
  const [horizon, setHorizon] = useState(16);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState("");
  const [focus, setFocus] = useState(0); // trajectory INDEX (0 = baseline)
  const nextId = useRef(1);

  // reset to the domain's default target when the spec changes
  useEffect(() => {
    const t = defaultTarget(spec);
    setEntityType(t?.entityType ?? "");
    setAttribute(t?.attribute ?? "");
    setRowIndex(null);
    setScenarios([]);
    setResult(null);
    setError("");
    setFocus(0);
    nextId.current = 1;
  }, [spec]);

  const entity = spec.entities.find((e) => e.type === entityType);
  const attr = entity?.attributes.find((a) => a.name === attribute);
  const numericEntities = spec.entities.filter((e) => e.attributes.some(isNumeric));
  const numericAttrs = entity?.attributes.filter(isNumeric) ?? [];

  const scenKey = JSON.stringify(scenarios.map(({ id: _id, ...s }) => s));
  useEffect(() => {
    if (!entityType || !attribute) {
      setResult(null);
      return;
    }
    let cancelled = false;
    const wire = scenarios.map(({ id: _id, ...s }) => s);
    runSimulation(spec.id, { entity_type: entityType, attribute, horizon, row_index: rowIndex, scenarios: wire })
      .then((r) => {
        if (cancelled) return;
        setError("");
        setResult(r);
      })
      .catch((e) => !cancelled && setError(String(e.message ?? e)));
    return () => {
      cancelled = true;
    };
    // scenarios serialized into scenKey so the effect re-runs on edits
  }, [spec.id, entityType, attribute, rowIndex, horizon, scenKey]);

  function changeEntity(t: string) {
    setEntityType(t);
    const e = spec.entities.find((x) => x.type === t);
    const first = e?.attributes.find(isNumeric);
    setAttribute(first?.name ?? "");
    setRowIndex(null);
    setFocus(0);
  }

  function addScenario() {
    const span = attr?.range ? attr.range[1] - attr.range[0] : 10;
    const id = nextId.current++;
    setScenarios((s) => [
      ...s,
      { id, label: `情景 ${id}`, at: Math.min(2, horizon), delta: Math.round(span * 0.25 * 100) / 100, mode: "shift" },
    ]);
  }
  function updateScenario(i: number, patch: Partial<SimScenario>) {
    setScenarios((s) => s.map((sc, j) => (j === i ? { ...sc, ...patch } : sc)));
  }
  function removeScenario(i: number) {
    setScenarios((s) => s.filter((_, j) => j !== i));
    setFocus(0);
  }

  if (!target0) return <p className="pr-muted">该领域没有可仿真的数值属性(metric / gauge / timeseries)。</p>;

  const [rLo, rHi] = (attr?.range ?? result?.range ?? [0, 100]) as [number, number];
  const step = stepUnit(spec.temporal?.step ?? "frame");
  const limit = attr?.threshold?.limit ?? result?.threshold?.limit;
  const warn = attr?.threshold?.warn ?? result?.threshold?.warn;
  const count = entity?.count ?? 0;
  // only draw a result that actually belongs to the current selection (avoid charting stale
  // trajectories against a different attribute's range/threshold while a refetch is in flight)
  const fresh =
    !!result && result.spec_id === spec.id && result.entity_type === entityType && result.attribute === attribute;
  const bandBreaches = (frames: SimResult["trajectories"][number]["frames"]) =>
    limit != null && frames.some((f) => f.hi >= limit);

  return (
    <>
      <p className="pr-view-meta">
        预测·仿真 · 对一个数值属性外推 <code>{horizon}</code> 帧未来 · 基线 + what-if 情景各带不确定带 ·
        动力学(<code>mean_revert</code>)与阈值取自 spec,<b>非实测,确定性合成示意</b>
      </p>

      <div className="pr-sim">
        <div className="pr-sim-controls">
          <label>
            <span>实体</span>
            <select value={entityType} onChange={(e) => changeEntity(e.target.value)}>
              {numericEntities.map((e) => (
                <option key={e.type} value={e.type}>
                  {e.icon} {e.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>属性</span>
            <select value={attribute} onChange={(e) => setAttribute(e.target.value)}>
              {numericAttrs.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>对象</span>
            <select
              value={rowIndex == null ? "auto" : String(rowIndex)}
              onChange={(e) => setRowIndex(e.target.value === "auto" ? null : Number(e.target.value))}
            >
              <option value="auto">自动(最高基线)</option>
              {Array.from({ length: count }, (_, i) => (
                <option key={i} value={i}>
                  #{i + 1}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>视野 {horizon}</span>
            <input
              type="range"
              min={4}
              max={48}
              step={1}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="pr-range"
            />
          </label>
          <button className="pr-sim-add" onClick={addScenario}>
            ＋ 加 what-if 情景
          </button>
        </div>

        {scenarios.length > 0 && (
          <div className="pr-sim-scenarios">
            {scenarios.map((sc, i) => (
              <div className="pr-sim-scenario" key={sc.id} style={{ ["--sc" as string]: trajectoryColor(i + 1) }}>
                <span className="pr-sim-swatch" />
                <input
                  className="pr-sim-label"
                  value={sc.label}
                  onChange={(e) => updateScenario(i, { label: e.target.value })}
                  aria-label="情景名"
                />
                <label className="pr-sim-field">
                  起始帧
                  <input
                    type="number"
                    min={0}
                    max={horizon}
                    value={sc.at}
                    onChange={(e) => updateScenario(i, { at: Number.isFinite(e.target.valueAsNumber) ? e.target.valueAsNumber : 0 })}
                  />
                </label>
                <label className="pr-sim-field">
                  幅度 Δ
                  <input
                    type="number"
                    step={0.1}
                    value={sc.delta}
                    onChange={(e) => updateScenario(i, { delta: Number.isFinite(e.target.valueAsNumber) ? e.target.valueAsNumber : 0 })}
                  />
                </label>
                <label className="pr-sim-field">
                  方式
                  <select value={sc.mode} onChange={(e) => updateScenario(i, { mode: e.target.value as SimScenario["mode"] })}>
                    <option value="shift">设定点</option>
                    <option value="pulse">脉冲</option>
                  </select>
                </label>
                <button className="pr-sim-del" onClick={() => removeScenario(i)} aria-label="删除情景">
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {error && <p className="pr-error">仿真失败:{error}</p>}
        {!error && !fresh && <p className="pr-muted">加载中…</p>}

        {!error && fresh && result && (
          <>
            <div className="pr-sim-chart">
              <svg viewBox={`0 0 ${DIMS.width} ${DIMS.height}`} className="pr-sim-svg" role="img" aria-label="仿真轨迹">
                {/* y gridlines: range bounds */}
                {[rLo, rHi].map((v) => (
                  <g key={v}>
                    <line className="pr-sim-grid" x1={DIMS.padL} x2={DIMS.width - DIMS.padR} y1={yOf(v, rLo, rHi, DIMS)} y2={yOf(v, rLo, rHi, DIMS)} />
                    <text className="pr-sim-axis" x={DIMS.padL - 6} y={yOf(v, rLo, rHi, DIMS) + 3} textAnchor="end">
                      {v}
                    </text>
                  </g>
                ))}
                {warn != null && (
                  <line className="pr-sim-warn" x1={DIMS.padL} x2={DIMS.width - DIMS.padR} y1={yOf(warn, rLo, rHi, DIMS)} y2={yOf(warn, rLo, rHi, DIMS)} />
                )}
                {limit != null && (
                  <line className="pr-sim-limit" x1={DIMS.padL} x2={DIMS.width - DIMS.padR} y1={yOf(limit, rLo, rHi, DIMS)} y2={yOf(limit, rLo, rHi, DIMS)} />
                )}
                <line className="pr-sim-now" x1={DIMS.padL} x2={DIMS.padL} y1={DIMS.padT} y2={DIMS.height - DIMS.padB} />
                <text className="pr-sim-axis" x={DIMS.padL} y={DIMS.height - 10} textAnchor="start">
                  现在
                </text>
                <text className="pr-sim-axis" x={DIMS.width - DIMS.padR} y={DIMS.height - 10} textAnchor="end">
                  +{result.horizon} {step}
                </text>

                {/* a faint uncertainty band for EVERY trajectory (focused one emphasized) — never
                    present a scenario as a single confident line */}
                {result.trajectories.map((t, i) => (
                  <path
                    key={`band-${i}`}
                    className={`pr-sim-band${i === focus ? " is-focus" : ""}`}
                    d={bandPath(t.frames, result.horizon, rLo, rHi, DIMS)}
                    style={{ fill: trajectoryColor(i) }}
                  />
                ))}
                {/* median lines */}
                {result.trajectories.map((t, i) => (
                  <path
                    key={`line-${i}`}
                    className={`pr-sim-line${i === focus ? " is-focus" : ""}`}
                    d={linePath(t.frames, "mid", result.horizon, rLo, rHi, DIMS)}
                    style={{ stroke: trajectoryColor(i) }}
                  />
                ))}
                {/* breach markers (median crosses limit) */}
                {result.trajectories.map((t, i) =>
                  t.breach_frame != null ? (
                    <circle
                      key={`breach-${i}`}
                      className="pr-sim-breach"
                      cx={xOf(t.breach_frame, result.horizon, DIMS)}
                      cy={yOf(t.frames[t.breach_frame].mid, rLo, rHi, DIMS)}
                      r={4}
                      style={{ fill: trajectoryColor(i) }}
                    >
                      <title>{`${t.label} 在帧 ${t.breach_frame} 越限(中位)`}</title>
                    </circle>
                  ) : null,
                )}
              </svg>
            </div>

            <div className="pr-sim-foot">
              <div className={`pr-sim-verdict ${verdictBreaches(result.verdict) ? "is-warn" : "is-good"}`}>
                <strong>判定:</strong> 最优 = <b>{result.verdict.best_label}</b> · {result.verdict.reason}
                <span className="pr-muted"> (目标:{result.verdict.objective === "avoid_breach" ? "优先不越限" : "终值最低"})</span>
              </div>
              <ul className="pr-sim-legend">
                {result.trajectories.map((t, i) => (
                  <li key={`legend-${i}`}>
                    <button
                      className={`pr-sim-legend-item${i === focus ? " is-focus" : ""}`}
                      onClick={() => setFocus(i)}
                      title="高亮该轨迹的不确定带"
                    >
                      <span className="pr-sim-swatch" style={{ background: trajectoryColor(i) }} />
                      {t.label}
                      <span className="pr-muted">
                        {" "}
                        终值 {t.terminal_mid}
                        {t.breach_frame != null
                          ? ` · 越限@${t.breach_frame}`
                          : bandBreaches(t.frames)
                            ? " · 中位不越限·带触限"
                            : " · 中位不越限"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              <p className="pr-sim-honesty">
                <span className="pr-badge tone-warn">确定性合成示意</span> 不确定带 = {result.confidence.rolls}{" "}
                次确定性 roll 的 min/中位/max;越限按中位判定;基线为独立合成,接 live 状态前非实测。
              </p>
            </div>
          </>
        )}
      </div>
    </>
  );
}
