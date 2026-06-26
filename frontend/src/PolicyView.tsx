import { useEffect, useMemo, useRef, useState } from "react";
import { compilePolicy, fetchLlmHealth, runPolicies } from "./api";
import { bestStillBreaches, pctSpan } from "./policy";
import { bandPath, type ChartDims, linePath, trajectoryColor, xOf, yOf } from "./sim";
import { stepUnit } from "./time";
import type { Attribute, LlmHealth, PolicyResult, Spec } from "./types";

const NUMERIC = new Set(["metric", "gauge", "timeseries"]);
const isNumeric = (a: Attribute) => NUMERIC.has(a.semantic_type);
const DIMS: ChartDims = { width: 760, height: 300, padL: 46, padR: 18, padT: 16, padB: 30 };
const OPS = [">=", "<=", ">", "<"];

type EditRule = { id: number; op: string; value: number; action: "shift" | "pulse"; by: number };
type EditPolicy = { id: number; label: string; rules: EditRule[]; llm?: boolean };

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

// a sensible starting trigger: the warn line if present, else the middle of the range
function triggerValue(attr?: Attribute): number {
  if (attr?.threshold?.warn != null) return attr.threshold.warn;
  const [lo, hi] = attr?.range ?? [0, 100];
  return Math.round(((lo + hi) / 2) * 10) / 10;
}

export default function PolicyView({ spec }: { spec: Spec }) {
  const target0 = useMemo(() => defaultTarget(spec), [spec]);
  const polId = useRef(1);
  const ruleId = useRef(1);
  const labelSeq = useRef(1); // monotonic → unique labels even after remove+add (A, B, C, …)
  const compileSeq = useRef(0); // invalidates an in-flight compile when the target changes
  const nextLabel = () => `策略 ${String.fromCharCode(64 + labelSeq.current++)}`;
  const newRule = (attr?: Attribute): EditRule => ({
    id: ruleId.current++,
    op: ">=",
    value: triggerValue(attr),
    action: "shift",
    by: -0.3,
  });
  const defaultPolicies = (attr?: Attribute): EditPolicy[] => {
    labelSeq.current = 1;
    return [{ id: polId.current++, label: nextLabel(), rules: [newRule(attr)] }];
  };

  const [entityType, setEntityType] = useState(target0?.entityType ?? "");
  const [attribute, setAttribute] = useState(target0?.attribute ?? "");
  const [rowIndex, setRowIndex] = useState<number | null>(null);
  const [horizon, setHorizon] = useState(20);
  const [policies, setPolicies] = useState<EditPolicy[]>([]);
  const [result, setResult] = useState<PolicyResult | null>(null);
  const [error, setError] = useState("");
  const [focus, setFocus] = useState(0); // trajectory index (0 = baseline)
  const [nl, setNl] = useState(""); // natural-language policy for the LLM to compile
  const [compiling, setCompiling] = useState(false);
  const [compileError, setCompileError] = useState("");
  const [llm, setLlm] = useState<LlmHealth | null>(null);

  useEffect(() => {
    fetchLlmHealth()
      .then(setLlm)
      .catch(() => setLlm(null));
  }, []);

  useEffect(() => {
    const t = defaultTarget(spec);
    const e = spec.entities.find((x) => x.type === t?.entityType);
    const a = e?.attributes.find((x) => x.name === t?.attribute);
    polId.current = 1;
    ruleId.current = 1;
    compileSeq.current++; // a spec switch invalidates any in-flight compile
    setEntityType(t?.entityType ?? "");
    setAttribute(t?.attribute ?? "");
    setRowIndex(null);
    setPolicies(defaultPolicies(a));
    setResult(null);
    setError("");
    setFocus(0);
    setNl("");
    setCompiling(false);
    setCompileError("");
  }, [spec]);

  const entity = spec.entities.find((e) => e.type === entityType);
  const attr = entity?.attributes.find((a) => a.name === attribute);
  const numericEntities = spec.entities.filter((e) => e.attributes.some(isNumeric));
  const numericAttrs = entity?.attributes.filter(isNumeric) ?? [];

  const wire = useMemo(
    () =>
      policies.map((p) => ({
        label: p.label,
        rules: p.rules.map((r) => ({ when: { op: r.op, value: r.value }, do: { action: r.action, by: r.by } })),
      })),
    [policies],
  );
  const wireKey = JSON.stringify(wire);

  useEffect(() => {
    if (!entityType || !attribute) {
      setResult(null);
      return;
    }
    let cancelled = false;
    runPolicies(spec.id, { entity_type: entityType, attribute, horizon, row_index: rowIndex, policies: wire })
      .then((r) => {
        if (cancelled) return;
        setError("");
        setResult(r);
      })
      .catch((e) => !cancelled && setError(String(e.message ?? e)));
    return () => {
      cancelled = true;
    };
  }, [spec.id, entityType, attribute, rowIndex, horizon, wireKey]);

  function changeEntity(t: string) {
    compileSeq.current++; // target changed → drop any in-flight compile result
    setEntityType(t);
    const e = spec.entities.find((x) => x.type === t);
    const a = e?.attributes.find(isNumeric);
    setAttribute(a?.name ?? "");
    setRowIndex(null);
    setPolicies(defaultPolicies(a));
    setFocus(0);
    setCompileError("");
  }
  function changeAttribute(name: string) {
    compileSeq.current++;
    setAttribute(name);
    setPolicies(defaultPolicies(entity?.attributes.find((a) => a.name === name)));
    setFocus(0);
    setCompileError("");
  }
  function addPolicy() {
    if (policies.length >= 4) return;
    setPolicies((s) => [...s, { id: polId.current++, label: nextLabel(), rules: [newRule(attr)] }]);
  }

  // The human-confirm gate: the LLM-compiled IR lands as a NORMAL, fully-editable policy card marked
  // with its LLM provenance — the user reads/edits/removes it. The only thing that "runs" is the
  // reversible, side-effect-free deterministic comparison (same live-recompute as any manual edit),
  // and the NUMBERS come from the engine, never the LLM. An in-flight compile is dropped if the user
  // changes target meanwhile (request-id guard), so a card never lands on the wrong attribute.
  function doCompile() {
    if (!nl.trim() || !entityType || !attribute || policies.length >= 4) return;
    const myId = ++compileSeq.current;
    setCompiling(true);
    setCompileError("");
    compilePolicy(spec.id, { entity_type: entityType, attribute, nl })
      .then((res) => {
        if (compileSeq.current !== myId) return; // target changed / superseded → discard stale result
        const editRules: EditRule[] = res.rules.map((r) => ({
          id: ruleId.current++,
          op: r.when.op,
          value: r.when.value,
          action: r.do.action,
          by: r.do.by,
        }));
        if (editRules.length === 0) {
          setCompileError("LLM 没产出可用规则,请改写或手填。");
          return;
        }
        // atomic hard cap (the compile button is already disabled at 4; this guards the rare case of
        // adding policies while a compile was in flight). The updater runs async, so don't read a flag
        // back out of it — just clear the NL on a successful compile.
        setPolicies((s) => (s.length >= 4 ? s : [...s, { id: polId.current++, label: `${nextLabel()} · LLM`, rules: editRules, llm: true }]));
        setNl("");
      })
      .catch((e) => compileSeq.current === myId && setCompileError(String(e.message ?? e)))
      .finally(() => compileSeq.current === myId && setCompiling(false));
  }
  function removePolicy(i: number) {
    setPolicies((s) => s.filter((_, j) => j !== i));
    setFocus(0);
  }
  function patchPolicy(i: number, patch: Partial<EditPolicy>) {
    setPolicies((s) => s.map((p, j) => (j === i ? { ...p, ...patch } : p)));
  }
  function addRule(i: number) {
    patchPolicy(i, { rules: [...policies[i].rules, newRule(attr)] });
  }
  function removeRule(i: number, ri: number) {
    patchPolicy(i, { rules: policies[i].rules.filter((_, k) => k !== ri) });
  }
  function patchRule(i: number, ri: number, patch: Partial<EditRule>) {
    patchPolicy(i, { rules: policies[i].rules.map((r, k) => (k === ri ? { ...r, ...patch } : r)) });
  }
  const num = (e: React.ChangeEvent<HTMLInputElement>, fallback: number) =>
    Number.isFinite(e.target.valueAsNumber) ? e.target.valueAsNumber : fallback;

  if (!target0) return <p className="pr-muted">该领域没有可仿真的数值属性(metric / gauge / timeseries)。</p>;

  const [rLo, rHi] = (attr?.range ?? result?.range ?? [0, 100]) as [number, number];
  const step = stepUnit(spec.temporal?.step ?? "frame");
  const limit = attr?.threshold?.limit ?? result?.threshold?.limit;
  const warn = attr?.threshold?.warn ?? result?.threshold?.warn;
  const count = entity?.count ?? 0;
  const fresh =
    !!result && result.spec_id === spec.id && result.entity_type === entityType && result.attribute === attribute;
  const hasLimit = limit != null;

  return (
    <>
      <p className="pr-view-meta">
        策略对比 · 写 2–3 条候选打法(<code>当 … → 调设定点</code>),引擎在不确定性下各 roll 一遍,<b>比谁更扛</b>(越限率 /
        最坏终值)· <b>参考,非替你拍板</b> · 数字只来自确定性引擎,合成示意非实测
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
            <span>目标量</span>
            <select value={attribute} onChange={(e) => changeAttribute(e.target.value)}>
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
            <input type="range" min={4} max={48} step={1} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="pr-range" />
          </label>
          <button className="pr-sim-add" onClick={addPolicy} disabled={policies.length >= 4}>
            ＋ 加候选策略
          </button>
        </div>

        <div className="pr-compile">
          <div className="pr-compile-head">
            <span>🗣️ 用人话写打法 → LLM 编译成可确认的规则(P6)</span>
            <span className={`pr-compile-llm ${llm && !llm.reachable ? "is-down" : ""}`}>
              {llm == null ? "LLM 状态…" : llm.reachable ? `LLM:${llm.model} · 可用` : `LLM 不可用(${llm.base_url})`}
            </span>
          </div>
          <div className="pr-compile-row">
            <textarea
              className="pr-compile-nl"
              value={nl}
              onChange={(e) => setNl(e.target.value)}
              rows={2}
              placeholder={`例:当${attr?.label ?? "目标量"}接近上限就把设定点下调 15%,再冲高就多砍 20%`}
            />
            <button
              className="pr-sim-add"
              onClick={doCompile}
              disabled={compiling || !nl.trim() || policies.length >= 4 || (llm != null && !llm.reachable)}
            >
              {compiling ? "编译中…" : "用 LLM 编译"}
            </button>
          </div>
          {compileError && <p className="pr-error pr-compile-err">编译失败:{compileError}(可手填规则)</p>}
          <p className="pr-compile-note pr-muted">
            LLM 只把人话翻成规则(IR),<b>不产生任何数字</b>;编译结果是<b>建议,需你确认 / 改</b>;轨迹与判定仍来自确定性引擎。
          </p>
        </div>

        <div className="pr-policy-editor">
          {policies.map((p, i) => (
            <div className="pr-policy-card" key={p.id} style={{ ["--sc" as string]: trajectoryColor(i + 1) }}>
              <div className="pr-policy-head">
                <span className="pr-sim-swatch" />
                <input className="pr-sim-label" value={p.label} onChange={(e) => patchPolicy(i, { label: e.target.value })} aria-label="策略名" />
                {p.llm && (
                  <span className="pr-policy-llm" title="LLM 把人话编译成的规则 —— 请核对 / 改;轨迹与数字来自确定性引擎">
                    🤖 LLM 译
                  </span>
                )}
                <button className="pr-sim-del" onClick={() => removePolicy(i)} aria-label="删除策略">
                  ✕
                </button>
              </div>
              {p.rules.map((r, ri) => (
                <div className="pr-policy-rule" key={r.id}>
                  <span className="pr-muted">当 当前值</span>
                  <select value={r.op} onChange={(e) => patchRule(i, ri, { op: e.target.value })} aria-label="比较">
                    {OPS.map((op) => (
                      <option key={op} value={op}>
                        {op}
                      </option>
                    ))}
                  </select>
                  <input type="number" step={0.1} value={r.value} onChange={(e) => patchRule(i, ri, { value: num(e, 0) })} aria-label="阈值" />
                  <span className="pr-muted">→</span>
                  <select value={r.action} onChange={(e) => patchRule(i, ri, { action: e.target.value as EditRule["action"] })} aria-label="动作">
                    <option value="shift">设定点</option>
                    <option value="pulse">脉冲</option>
                  </select>
                  <span className="pr-muted">Δ</span>
                  <input type="number" step={0.05} value={r.by} onChange={(e) => patchRule(i, ri, { by: num(e, 0) })} aria-label="幅度(×跨度)" />
                  <span className="pr-muted">×跨度 ({pctSpan(r.by)})</span>
                  <button className="pr-sim-del" onClick={() => removeRule(i, ri)} aria-label="删除规则">
                    ✕
                  </button>
                </div>
              ))}
              <button className="pr-policy-addrule" onClick={() => addRule(i)}>
                ＋ 规则
              </button>
            </div>
          ))}
        </div>

        {error && <p className="pr-error">评估失败:{error}</p>}
        {!error && !fresh && <p className="pr-muted">加载中…</p>}

        {!error && fresh && result && (
          <>
            <div className="pr-sim-chart">
              <svg viewBox={`0 0 ${DIMS.width} ${DIMS.height}`} className="pr-sim-svg" role="img" aria-label="策略轨迹对比">
                {[rLo, rHi].map((v) => (
                  <g key={v}>
                    <line className="pr-sim-grid" x1={DIMS.padL} x2={DIMS.width - DIMS.padR} y1={yOf(v, rLo, rHi, DIMS)} y2={yOf(v, rLo, rHi, DIMS)} />
                    <text className="pr-sim-axis" x={DIMS.padL - 6} y={yOf(v, rLo, rHi, DIMS) + 3} textAnchor="end">
                      {v}
                    </text>
                  </g>
                ))}
                {warn != null && <line className="pr-sim-warn" x1={DIMS.padL} x2={DIMS.width - DIMS.padR} y1={yOf(warn, rLo, rHi, DIMS)} y2={yOf(warn, rLo, rHi, DIMS)} />}
                {limit != null && <line className="pr-sim-limit" x1={DIMS.padL} x2={DIMS.width - DIMS.padR} y1={yOf(limit, rLo, rHi, DIMS)} y2={yOf(limit, rLo, rHi, DIMS)} />}
                <line className="pr-sim-now" x1={DIMS.padL} x2={DIMS.padL} y1={DIMS.padT} y2={DIMS.height - DIMS.padB} />
                <text className="pr-sim-axis" x={DIMS.padL} y={DIMS.height - 10} textAnchor="start">
                  现在
                </text>
                <text className="pr-sim-axis" x={DIMS.width - DIMS.padR} y={DIMS.height - 10} textAnchor="end">
                  +{result.horizon} {step}
                </text>
                {result.policies.map((t, i) => (
                  <path key={`band-${i}`} className={`pr-sim-band${i === focus ? " is-focus" : ""}`} d={bandPath(t.frames, result.horizon, rLo, rHi, DIMS)} style={{ fill: trajectoryColor(i) }} />
                ))}
                {result.policies.map((t, i) => (
                  <path key={`line-${i}`} className={`pr-sim-line${i === focus ? " is-focus" : ""}`} d={linePath(t.frames, "mid", result.horizon, rLo, rHi, DIMS)} style={{ stroke: trajectoryColor(i) }} />
                ))}
                {result.policies.map((t, i) =>
                  t.breach_frame != null ? (
                    <circle key={`breach-${i}`} className="pr-sim-breach" cx={xOf(t.breach_frame, result.horizon, DIMS)} cy={yOf(t.frames[t.breach_frame].mid, rLo, rHi, DIMS)} r={4} style={{ fill: trajectoryColor(i) }}>
                      <title>{`${t.label} 中位在帧 ${t.breach_frame} 越限`}</title>
                    </circle>
                  ) : null,
                )}
              </svg>
            </div>

            <div className="pr-sim-foot">
              <table className="pr-policy-table">
                <thead>
                  <tr>
                    <th>策略</th>
                    <th>规则</th>
                    {hasLimit && <th>越限率</th>}
                    <th>终值(中位)</th>
                    <th>最坏终值</th>
                  </tr>
                </thead>
                <tbody>
                  {result.policies.map((t, i) => (
                    <tr key={t.label} className={`${t.label === result.verdict.best_label ? "is-best" : ""}${i === focus ? " is-focus" : ""}`} onClick={() => setFocus(i)}>
                      <td>
                        <span className="pr-sim-swatch" style={{ background: trajectoryColor(i) }} /> {t.label}
                        {t.label === result.verdict.best_label && (
                          <span className="pr-policy-badge">{hasLimit ? "最优" : "终值最低"}</span>
                        )}
                      </td>
                      <td className="pr-muted">{t.rule_count}</td>
                      {hasLimit && <td className={t.breach_rate > 0 ? "pr-policy-bad" : "pr-policy-ok"}>{Math.round(t.breach_rate * 100)}%</td>}
                      <td>{t.terminal_mid}</td>
                      <td>{t.worst_terminal}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* green "good" only when there's a real threshold and the winner avoids it; with no
                  threshold the ranking hangs on an unstated "lower is better" → stay neutral */}
              <div className={`pr-sim-verdict ${!hasLimit ? "" : bestStillBreaches(result) ? "is-warn" : "is-good"}`}>
                <strong>判定:</strong> {hasLimit ? "最稳" : "终值最低"} = <b>{result.verdict.best_label}</b> ·{" "}
                {result.verdict.reason}
                <span className="pr-muted">
                  {" "}
                  (目标:{result.verdict.objective === "avoid_breach" ? "越限率最低" : "终值最低,假设越低越好"})
                </span>
              </div>

              <div className={`pr-policy-sens ${result.sensitivity.stable ? "is-stable" : "is-fragile"}`}>
                <strong>敏感性:</strong> {result.sensitivity.note}
              </div>

              <p className="pr-sim-honesty">
                <span className="pr-badge tone-warn">确定性合成示意</span> 数字只来自确定性引擎(LLM 不编数);
                {result.confidence.note}
              </p>
            </div>
          </>
        )}
      </div>
    </>
  );
}
