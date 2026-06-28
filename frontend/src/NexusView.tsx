import { Component, Suspense, lazy, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { fetchNexusAlign, fetchNexusGate, fetchNexusRealCoupling, fetchNexusView } from "./api";
import type { NexusAlign, NexusGate, NexusRealCoupling, NexusView as NexusViewData, NexusUnit } from "./types";

// the heavy three.js galaxy is a lazy chunk — it never enters the main bundle, and we fall back to the SVG
// when WebGL is unavailable (DESIGN_visual_fusion §5: the 2D form is the accessibility/no-WebGL fallback).
const NexusGalaxy = lazy(() => import("./NexusGalaxy"));

function hasWebGL(): boolean {
  try {
    const c = document.createElement("canvas");
    const gl = (c.getContext("webgl") || c.getContext("experimental-webgl")) as WebGLRenderingContext | null;
    if (!gl) return false;
    gl.getExtension("WEBGL_lose_context")?.loseContext(); // don't leak the probe context
    return true;
  } catch {
    return false;
  }
}

// A probe passing does NOT guarantee the real Canvas + postprocessing pipeline initialises; a runtime
// WebGL/EffectComposer failure (context exhaustion, driver blocklist, context loss) throws during render,
// and Suspense does NOT catch that. This boundary delivers the actual §5 contract: on any galaxy error,
// fall back to the 2D SVG instead of blanking the whole cockpit.
class GalaxyBoundary extends Component<{ onError: () => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

// The two domains live at fixed columns; each bulges toward the centre so the gap between them is the
// "collision zone" where verified bridges light. Cold cyan = INFRA, warm amber = LIBRARY (the only
// hard-coded colours — they encode the two domains, nothing else).
const W = 920;
const H = 600;
const COLD = "#39a7c8";
const WARM = "#d29240";
const SEEDS = Array.from({ length: 8 }, (_, i) => `xe-${i}`);

function pos(idx: number, n: number, side: "A" | "B") {
  const t = n > 1 ? idx / (n - 1) : 0.5;
  const y = 70 + t * (H - 140);
  const bulge = 56 * Math.sin(t * Math.PI);
  const x = side === "A" ? 250 + bulge : W - 250 - bulge;
  return { x, y };
}

function NexusViz() {
  const [seed, setSeed] = useState(SEEDS[0]);
  const [data, setData] = useState<NexusViewData | null>(null);
  const [error, setError] = useState("");
  const webgl = useMemo(() => hasWebGL(), []);
  const [mode, setMode] = useState<"3d" | "2d">("3d");
  const [galaxyFailed, setGalaxyFailed] = useState(false);
  const show3d = mode === "3d" && webgl && !galaxyFailed;
  // alignment replay (the money moment): the galaxy collides as the real Sinkhorn residual converges
  const [replay, setReplay] = useState(false);
  const [align, setAlign] = useState<NexusAlign | null>(null);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const nSteps = align?.snapshots.length ?? 0;

  // fetch the Sinkhorn snapshots lazily when replay turns on (or the seed changes while replaying)
  useEffect(() => {
    if (!replay || !show3d) return;
    let cancelled = false;
    setAlign(null);
    setStep(0);
    fetchNexusAlign(seed)
      .then((a) => { if (!cancelled) { setAlign(a); setStep(0); setPlaying(true); } })
      .catch(() => !cancelled && setReplay(false));
    return () => { cancelled = true; };
  }, [replay, show3d, seed]);

  // playback: advance one iteration at a time, stop at convergence (the last snapshot)
  useEffect(() => {
    if (!playing || nSteps <= 1) return;
    const id = setInterval(() => setStep((s) => (s + 1 >= nSteps ? (setPlaying(false), nSteps - 1) : s + 1)), 280);
    return () => clearInterval(id);
  }, [playing, nSteps]);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError("");
    fetchNexusView(seed)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [seed]);

  const layout = useMemo(() => {
    if (!data) return null;
    const aPos = new Map<number, { x: number; y: number }>();
    const bPos = new Map<number, { x: number; y: number }>();
    data.A.units.forEach((u: NexusUnit) => aPos.set(u.idx, pos(u.idx, data.A.units.length, "A")));
    data.B.units.forEach((u: NexusUnit) => bPos.set(u.idx, pos(u.idx, data.B.units.length, "B")));
    // draw ghosts first (behind), then medium, then the glowing high bridges on top
    const order = { coincidence: 0, medium: 1, high: 2 } as const;
    const bridges = [...data.bridges].sort((p, q) => order[p.confidence] - order[q.confidence]);
    return { aPos, bPos, bridges };
  }, [data]);

  const sc = data?.scorecard;

  return (
    <div className="pr-nexus">
      <div className="pr-nexus-bar">
        <span className="pr-nexus-title">星系碰撞 · 跨域 nexus（INFRA × LIBRARY）</span>
        <div className="pr-nexus-controls">
          {webgl && (
            <div className="pr-nexus-modes" role="group" aria-label="渲染模式">
              <button className={show3d ? "is-active" : ""} onClick={() => { setGalaxyFailed(false); setMode("3d"); }} title="3D 银河碰撞">3D</button>
              <button className={!show3d ? "is-active" : ""} onClick={() => setMode("2d")} title="2D SVG">2D</button>
            </div>
          )}
          {show3d && (
            <button className={replay ? "pr-nexus-replaybtn is-active" : "pr-nexus-replaybtn"}
              onClick={() => { setReplay((r) => !r); setPlaying(false); }} title="按真实 Sinkhorn 对齐迭代回放碰撞">
              ✦ 对齐回放
            </button>
          )}
          <label className="pr-nexus-seed">
            种子
            <select value={seed} onChange={(e) => setSeed(e.target.value)}>
              {SEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {show3d && replay && (
        <div className="pr-nexus-replay">
          <button className="pr-play" onClick={() => setPlaying((p) => !p)} aria-label={playing ? "暂停" : "播放对齐"} disabled={nSteps === 0}>
            {playing ? "⏸" : "▶"}
          </button>
          <input className="pr-range" type="range" min={0} max={Math.max(0, nSteps - 1)} step={1} value={step}
            disabled={nSteps === 0} aria-label="Sinkhorn 迭代"
            onChange={(e) => { setPlaying(false); setStep(Number(e.target.value)); }} />
          <span className="pr-nexus-replay-meta">
            {nSteps === 0 ? "对齐计算中…" : `迭代 ${align?.snapshots[step]?.iter ?? 0} · 残差 ${(align?.snapshots[step]?.residual ?? 0).toFixed(4)} · 动画=真实对齐回放`}
          </span>
        </div>
      )}

      {error && <p className="pr-error">加载失败:{error}</p>}
      {!data && !error && <p className="pr-muted">加载中…</p>}

      {data && (
        <div className="pr-nexus-stage">
          {show3d ? (
            <GalaxyBoundary onError={() => setGalaxyFailed(true)}>
              <Suspense fallback={<div className="pr-nexus-svg pr-nexus-loading">渲染银河…</div>}>
                <NexusGalaxy data={data} align={replay ? align : null} step={replay ? step : undefined} />
              </Suspense>
            </GalaxyBoundary>
          ) : layout ? (
          <svg viewBox={`0 0 ${W} ${H}`} className="pr-nexus-svg" role="img" aria-label="跨域 nexus 碰撞视图">
            <defs>
              <filter id="nexglow" x="-60%" y="-60%" width="220%" height="220%">
                <feGaussianBlur stdDeviation="3.4" result="b" />
                <feMerge>
                  <feMergeNode in="b" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <rect x={0} y={0} width={W} height={H} className="pr-nexus-bg" />
            {/* candidate bridges */}
            {layout.bridges.map((br, i) => {
              const a = layout.aPos.get(br.a_idx);
              const b = layout.bPos.get(br.b_idx);
              if (!a || !b) return null;
              if (br.confidence === "coincidence")
                return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#8a86b8" strokeWidth={0.5} strokeOpacity={0.05} />;
              if (br.confidence === "medium")
                return (
                  <line
                    key={i}
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    stroke={br.shape_fires ? COLD : WARM}
                    strokeWidth={1}
                    strokeOpacity={0.22}
                    strokeDasharray={br.dissent ? "3 4" : undefined}
                  />
                );
              // high = both channels fired → a verified nexus; the only thing allowed to glow
              return (
                <line
                  key={i}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="#f5f7ff"
                  strokeWidth={2.2}
                  strokeOpacity={0.95}
                  filter="url(#nexglow)"
                />
              );
            })}
            {/* domain stars */}
            {data.A.units.map((u) => {
              const p = layout.aPos.get(u.idx)!;
              return <circle key={`a${u.idx}`} cx={p.x} cy={p.y} r={u.anchor ? 4.5 : 2.6} fill={COLD} fillOpacity={u.anchor ? 0.95 : 0.5} filter={u.anchor ? "url(#nexglow)" : undefined} />;
            })}
            {data.B.units.map((u) => {
              const p = layout.bPos.get(u.idx)!;
              return <circle key={`b${u.idx}`} cx={p.x} cy={p.y} r={u.anchor ? 4.5 : 2.6} fill={WARM} fillOpacity={u.anchor ? 0.95 : 0.5} filter={u.anchor ? "url(#nexglow)" : undefined} />;
            })}
            <text x={250} y={44} className="pr-nexus-domlabel" textAnchor="middle" fill={COLD}>
              {data.A.prefix} · {data.A.metric}
            </text>
            <text x={W - 250} y={44} className="pr-nexus-domlabel" textAnchor="middle" fill={WARM}>
              {data.B.prefix} · {data.B.metric}
            </text>
          </svg>
          ) : null}

          {sc && (
            <div className="pr-nexus-hud">
              <h4>诚实计分板</h4>
              <dl>
                <div><dt>候选桥</dt><dd>{sc.candidates}</dd></div>
                <div className="pr-hud-high"><dt>发光真桥（过 FDR）</dt><dd>{sc.high}</dd></div>
                <div><dt>相对高但未显著（dim）</dt><dd>{sc.medium}</dd></div>
                <div><dt>巧合（虚影）</dt><dd>{sc.coincidence}</dd></div>
                <div><dt>实际耦合数</dt><dd>{sc.true_couplings}</dd></div>
                <div><dt>点亮集精度</dt><dd>{sc.high_tier_precision == null ? "—" : sc.high_tier_precision}</dd></div>
                <div><dt>FDR q · 期望假高</dt><dd>{sc.fdr_q} · {sc.expected_false_high}</dd></div>
              </dl>
              <p className="pr-nexus-caveat">{data.caveat}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Architect / PM register summary of the nexus arc — same honesty, decision framing. Live-fetches the fast
// §6c gate (~1s) + a per-package scorecard (instant); the 10s convergence + the Track-1 collapse are reported
// as RECORDED deterministic results with reproducibility pointers (kept off the blocking path on purpose).
function NexusSummary() {
  const [gate, setGate] = useState<NexusGate | null>(null);
  const [view, setView] = useState<NexusViewData | null>(null);
  const [realc, setRealc] = useState<NexusRealCoupling | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchNexusGate(), fetchNexusView(SEEDS[0]), fetchNexusRealCoupling()])
      .then(([g, v, rc]) => { if (!cancelled) { setGate(g); setView(v); setRealc(rc); } })
      .catch((e) => !cancelled && setError(String(e)));
    return () => { cancelled = true; };
  }, []);
  const a2 = (x: number) => x.toFixed(2);
  const a3 = (x: number) => x.toFixed(3);
  return (
    <div className="pr-ag-plain">
      <p className="pr-ag-plain-lead">
        命题:把「真·跨域 nexus」与「时间巧合」区分开,靠的是<b>收敛效度</b>(≥2/3 条<b>读不同存储、互相独立</b>的渠道同意),
        而非任何单一信号。下面是这条线的诚实账本 + 边界;星系可视化与对齐回放见右侧「🌌 可视化」。
      </p>
      {error && <p className="pr-error">加载失败:{error}（先启动后端 :8200）</p>}
      <div className="pr-ag-plain-card is-caveat">
        <h4>① 先量「笨 baseline」,让它杀前提(诚实负结果)</h4>
        <p>
          <b>M0:</b>真桥按构造即「时间同现」⇒ 时间戳是充分统计量,单靠 Δframe 就近满分(time-coincidence AUC ~0.94–0.99)。
          <b>这是个让度量难堪的负结果,照实写下</b>——意味着「时间」不能作为发现依据。<b>M1:</b>时间无关的语义透镜(L4)AUC=0.36(<b>低于随机</b>),也照报。
        </p>
        <p className="pr-ag-plain-analogy">
          ▸ 架构含义:朴素信号要么是<b>充分统计量(等于作弊)</b>、要么<b>低于随机</b>;任何「真发现」必须靠<b>多条独立渠道收敛</b>,不能信单通道。
        </p>
      </div>
      <div className="pr-ag-plain-card">
        <h4>② §6c 难度门 + 三渠道收敛(在合成 substrate 上,可证伪)</h4>
        <p>
          channel-blind 难度门(实测,{gate ? `${gate.seeds} seed 池化` : "加载中"}):oracle(见 latent)recover <b>AUC {gate ? a2(gate.oracle_auc) : "…"}</b>,
          朴素 baseline(time/depth/string)~随机(<b>{gate ? `${a2(gate.time_auc)}/${a2(gate.depth_auc)}/${a2(gate.string_auc)}` : "…"}</b>)
          ⇒ 难度<b>良定义</b>、{gate?.gate_pass ? "门通过" : "—"}。三条独立渠道(shape=时序、fingerprint=SQL 直方图、relational=tags;两两相关仅 0.13–0.19):
          <b>2-way 收敛 margin 的 CI 跨 0.05(判不定)</b>;加入第三条独立渠道后,<b>3-way margin +0.073、CI 整段 &gt;0.05 ⇒ 稳过</b>;
          反「reverse-trap」控制(同功率但相关的 placebo 渠道<b>不</b>过线)证明胜在<b>独立性而非功率</b>。
          {view?.scorecard && <> 当前包计分板:候选桥 {view.scorecard.candidates}、发光真桥(过 FDR 显著)<b>{view.scorecard.high}</b>、点亮集精度 <b>{view.scorecard.high_tier_precision ?? "—"}</b>、实际耦合 {view.scorecard.true_couplings}(期望假高≈{view.scorecard.expected_false_high})。</>}
        </p>
        <p className="pr-ag-plain-analogy">
          ▸ 含义:在<b>受控合成</b>上,度量能把「3 条独立证据同时指向」与「时间巧合 / 单通道」分开——这是「收敛效度是戏」批评的<b>真修复</b>。
          各渠道<b>功率</b>是工程构造(常量带可见性调参),<b>独立性与 margin-vs-floor 未调、可证伪</b>。
        </p>
        <p className="pr-ag-plain-analogy">
          ▸ §13 修复(发光诚实):点火从「相对 top-decile」(任何对都强行点亮 ~10%,零耦合对也不熄)换成
          <b>绝对显著阈 + Benjamini–Hochberg FDR(CACE)</b>——置换零分布(本 A × 无关 B)→ Fisher 合并 3 渠道 p → 控 FDR。
          <b>零耦合对现在熄灭</b>(实测「高」桥 8.27→<b>0.03</b>,精度 0.66→<b>0.96</b>),「只有已验证的桥发光」终于为真;代价是 recall 降(FDR 保守)。
          (可经 <code>/api/nexus_xdom/fdr_check</code> 复现。)
        </p>
      </div>
      <div className="pr-ag-plain-card is-caveat">
        <h4>③ 外部效度 · 两面都用真实数据测过(诚实结论)</h4>
        <p>
          <b>(a) 边缘校准 → 收敛翻车:</b>把 substrate 的可观测边缘<b>校准到真实数据</b>(breast_cancer,变异系数 ~14× 高于手设)后,
          <b>3-way 收敛塌回判不定</b>——之前的胜利部分靠「手设的不真实低噪声」(可经 <code>/api/nexus_xdom/calibrate</code> 复现)。
        </p>
        <p>
          <b>(b) 耦合换真实 → 信号衰减:</b>把跨域耦合从设计潜变量换成<b>真实配对数据</b>(同一肿瘤的两特征视图),沿强度谱实测{realc ? "" : "中…"}
          {realc && (
            <> ——收敛信号随「越真越跨切面」单调衰减:近重复 softball 语义 AUC <b>{a2(realc.same_feature_near_duplicate.semantic_zscore_auc)}</b>
              (对齐 corr ≈{realc.same_feature_near_duplicate.same_base_diag_corr ?? "—"})→ <b>真·跨切面</b> AUC <b>{a2(realc.disjoint_feature_cross_aspect.semantic_zscore_auc)}</b>、
              top-1 <b>{a3(realc.disjoint_feature_cross_aspect.resolver_top1_acc)}</b>(≈随机 {a3(realc.chance_top1)}，唯一解析基本不可能)。
              即合成的 ~0.99 <b>严重高估真实跨域耦合强度</b>。</>
          )}
        </p>
        <p className="pr-ag-plain-analogy">
          ▸ 选型含义:<b>度量本身严谨</b>(受控合成上能区分 nexus vs 巧合),且<b>两面外部效度都用真实数据探过</b>;
          但真实<b>跨切面</b>耦合既弱又难唯一解析 ⇒ 任何「野外跨域发现」须自带真实校准,本地、确定性,<b>非生产证据</b>。
        </p>
      </div>
    </div>
  );
}

export default function NexusView() {
  const [tab, setTab] = useState<"summary" | "viz">("summary"); // accessible architect/PM summary first
  return (
    <div>
      <nav className="pr-ag-subtabs" role="tablist" aria-label="nexus 子标签">
        <button role="tab" aria-selected={tab === "summary"} className={tab === "summary" ? "pr-ag-subtab is-active" : "pr-ag-subtab"} onClick={() => setTab("summary")}>
          📋 摘要 · 架构/PM 视角
        </button>
        <button role="tab" aria-selected={tab === "viz"} className={tab === "viz" ? "pr-ag-subtab is-active" : "pr-ag-subtab"} onClick={() => setTab("viz")}>
          🌌 可视化（星系碰撞 + 对齐回放）
        </button>
      </nav>
      {tab === "summary" ? <NexusSummary /> : <NexusViz />}
    </div>
  );
}
