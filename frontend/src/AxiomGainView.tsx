import { useEffect, useState } from "react";
import { fetchAxiomProtocol, fetchSplitAblation } from "./api";
import { parseFrac, pct, splitModels, splitPair } from "./axiomgain";
import type { AxiomProtocol, SplitAblation } from "./types";

// The surviving, citable line (OBSERVER §12): structured semantic foundation vs bare RAG. This lab tab
// surfaces the two honest results — Track 2 (cross-model token-savings frontier) and the split-substrate
// cross-domain coreference (enablement) — with their caveats VISIBLE, never buried (honesty = the steering
// wheel). Spec-independent: the experiment is the same regardless of the selected domain.
const shortModel = (m: string) => m.replace(/^.*\//, "").replace(/-instruct|-qat$/g, "");
// SVG diamond path (the Tier-2 frontier marker — hollow/dashed/muted, never a filled climax)
const diamond = (cx: number, cy: number, r: number) => `M${cx} ${cy - r}L${cx + r} ${cy}L${cx} ${cy + r}L${cx - r} ${cy}Z`;

function Bar({ frac, kind, label }: { frac: number; kind: "save" | "qual" | "qual-weak" | "naive" | "axiom"; label: string }) {
  return (
    <div className="pr-ag-bar">
      <span className="pr-ag-bar-label">{label}</span>
      <div className="pr-ag-bar-track">
        <div className={`pr-ag-bar-fill is-${kind}`} style={{ width: `${Math.max(0, Math.min(1, frac)) * 100}%` }} />
      </div>
    </div>
  );
}

function Protocol({ p }: { p: AxiomProtocol }) {
  const h = p.headline;
  const tokSig = parseFrac(h.token_saving_significant_cells);
  const qualSig = parseFrac(h.quality_gain_significant_cells);
  const mono = parseFrac(h.models_monotonic_in_dirt);
  const nStar = p.build_amortization.breakeven_N_dictionary;
  return (
    <section className="pr-ag-card">
      <h3>① 结构化语义地基 vs 裸 RAG（logistics · 跨模型矩阵 + 每格 bootstrap 95% CI）</h3>
      <div className="pr-ag-chips">
        <span className="pr-ag-chip is-firm">输入 token 平均省 <b>{pct(h.mean_input_token_saving)}</b> · CI&gt;0 {tokSig.num}/{tokSig.den}</span>
        <span className="pr-ag-chip is-firm">成本×质量 Pareto 前沿 {h.axiom_pareto_dominant ? "由 axiom 独占 ✓" : "未独占"}</span>
        <span className="pr-ag-chip is-firm">学习字典 build 摊销 N*{nStar == null ? "=∞（诚实负）" : `=${nStar}`}</span>
        <span className="pr-ag-chip is-soft">质量 ΔF1 处处非负（min +{h.min_quality_delta.toFixed(3)}）· CI&gt;0 仅 {qualSig.num}/{qualSig.den}</span>
        <span className="pr-ag-chip is-soft">随脏度真单调 {mono.num}/{mono.den} 模型（其余在 dirt=0.6 见顶）</span>
      </div>
      <div className="pr-ag-matrix">
        <div className="pr-ag-matrix-head"><span>模型 · 脏度</span><span>输入 token 省</span><span>质量 ΔF1（条形 /0.5 缩放;CI&gt;0?）</span></div>
        {p.matrix.map((c) => (
          <div className="pr-ag-row" key={`${c.model}-${c.dirtiness}`}>
            <span className="pr-ag-cellname">{shortModel(c.model)} · d{c.dirtiness}</span>
            <div className="pr-ag-cellbar"><Bar frac={c.token_saving_mean} kind="save" label={pct(c.token_saving_mean)} /></div>
            <div className="pr-ag-cellbar">
              {/* indeterminate cells (CI straddles 0) get a HATCHED/muted fill so bar prominence tracks
                  confidence, not just point-estimate magnitude — else the noisiest cell looks like the biggest win */}
              <Bar frac={c.quality_delta_mean / 0.5} kind={c.quality_delta_excludes_0 ? "qual" : "qual-weak"} label={`+${c.quality_delta_mean.toFixed(3)}`} />
              <span className={c.quality_delta_excludes_0 ? "pr-ag-sig is-yes" : "pr-ag-sig is-no"} title={c.quality_delta_excludes_0 ? "95% CI 整段 >0" : "CI 跨 0 ⇒ 判不定（条形已弱化）"}>
                {c.quality_delta_excludes_0 ? "●" : "○"}
              </span>
            </div>
          </div>
        ))}
      </div>
      <p className="pr-ag-verdict">{p.honest_verdict}</p>
    </section>
  );
}

function Split({ ab }: { ab: SplitAblation }) {
  const ceil = ab.resolver_accuracy.answer_f1_mean;
  return (
    <section className="pr-ag-card">
      <h3>② 跨域共指 · 结构地基<b>使能</b>裸 RAG 干不了的任务（split substrate）</h3>
      <p className="pr-ag-sub">
        A 实体 ≡ B 实体（变体改写、无共享键）→ 列 B 标签。naive-RAG 给两域原始记录（LLM 须自行跨域匹配，
        表面不可桥）；axiom-RAG 给确定性 resolver（≈{ceil.toFixed(3)} F1 上界）预解析。
      </p>
      {splitModels(ab).map((m) => {
        const { naive, axiom } = splitPair(ab, m);
        const save = ab.gains.find((g) => g.model === m)?.input_token_saving ?? 0;
        return (
          <div className="pr-ag-splitrow" key={m}>
            <div className="pr-ag-splitname">{shortModel(m)}<span className="pr-ag-save">省 {pct(save)} token</span></div>
            <Bar frac={(naive?.quality_f1 ?? 0) / Math.max(ceil, 0.001)} kind="naive" label={`naive ${(naive?.quality_f1 ?? 0).toFixed(3)}`} />
            <Bar frac={(axiom?.quality_f1 ?? 0) / Math.max(ceil, 0.001)} kind="axiom" label={`axiom ${(axiom?.quality_f1 ?? 0).toFixed(3)}`} />
            {axiom && axiom.truncated_calls > 0 && (
              <span className="pr-ag-trunc" title="该模型在部分 seed 上过量生成、超 token cap；salvage 按已完成条目计分，截断数照实报">
                ⚠ {axiom.truncated_calls}/8 seed 截断（过量生成）
              </span>
            )}
          </div>
        );
      })}
      <p className="pr-ag-verdict">{ab.honest_verdict}</p>
    </section>
  );
}

// ③ The H2 "money moment": as the model gets MORE CAPABLE, the structured foundation's QUALITY benefit shrinks
// toward 0 (H2a — a capable model resolves the cross-source task itself), while the TOKEN saving is structural
// (context-size-bound) and stays ~flat (H2b — the ~61% survives any model). The fork between the two lines IS the
// result. HONESTY guards baked in: (a) the reproducible local points carry full visual weight; the Tier-2 manual
// frontier point (GPT-5.5, browser-captured, NOT reproducible, token UNMEASURED) is MUTED + hollow + never merged
// into the live series — prominence tracks CONFIDENCE, not story-weight; (b) the qwen3.6 interior point is RENDERED
// (not hidden) so the monotonicity-breaking wobble is visible, matching the Spearman shown (DON'T #4); (c) gain≈0
// is shown as "≈0" (a 4-naive+1-axiom slice, not a mean±CI); (d) the H2b flat-line caveat sits next to the line.
function CapGain({ p }: { p: AxiomProtocol }) {
  // Fetch the wobble-visible 4-model variant for THIS axis only (tabs ①② keep the default 3-model headline set).
  // Render from `p4 ?? p`: the chart upgrades 3→4 points when it arrives, and falls back gracefully if it fails.
  const [p4, setP4] = useState<AxiomProtocol | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchAxiomProtocol("logistics_demo", true).then((r) => !cancelled && setP4(r)).catch(() => {});
    return () => { cancelled = true; };
  }, []);
  const view = p4 ?? p;
  const h2 = view.h2_capability_vs_gain;
  const rows = h2.by_capability_ascending;
  const fm = h2.frontier_manual;
  const last = rows[rows.length - 1];
  const cmpModel = fm?.confirm_comparator_model ?? last?.model ?? "";
  const cmpGain = fm?.confirm_comparator_gain ?? last?.quality_gain ?? 0;
  const flat = h2["token_saving_is_structural_flat(<0.05)"]; // gate the H2b "firm" claim on the computed boolean

  // per-model confidence (brightness=confidence, NOT magnitude): the amber quality marker is FILLED only if EVERY
  // one of that model's cells has CI>0; else hollow — so a noisy point-estimate can't masquerade as a firm win
  const qualFilled = (m: string) => {
    const cells = view.matrix.filter((c) => c.model === m);
    return cells.length > 0 && cells.every((c) => c.quality_delta_excludes_0);
  };

  // chart geometry — reproducible points fill the bright left/center; the muted frontier sits at x≈0.95
  const W = 620, H = 300, L = 52, R = 18, T = 18, B = 42;
  const pw = W - L - R, ph = H - T - B;
  const XLO = 0.55, XHI = 1.0, YHI = 0.7;
  const x = (c: number) => L + ((c - XLO) / (XHI - XLO)) * pw;
  const y = (v: number) => T + (1 - v / YHI) * ph;
  const refY = y(view.headline.mean_input_token_saving); // flat blue reference, welded to the ~61% headline
  const tokPts = rows.map((r) => `${x(r.capability_naive_f1)},${y(r.token_saving)}`).join(" ");
  const qualPts = rows.map((r) => `${x(r.capability_naive_f1)},${y(r.quality_gain)}`).join(" ");
  const ghostX0 = x(0.84); // subtle "non-API / browser-captured" zone marker
  const QSCALE = Math.max(0.3, ...rows.map((r) => r.quality_gain)); // never silently clips a real gain

  return (
    <section className="pr-ag-card">
      <h3>③ 能力越强,“答对”红利越薄、“省 token”红利<b>结构性存活</b>(H2 · 能力×增益剪刀叉)</h3>
      <div className="pr-ag-chips">
        <span className="pr-ag-chip is-soft">质量 ΔF1 随能力↓ · Spearman <b>{h2.spearman_capability_gain ?? "—"}</b>{h2.quality_gain_monotone_decreasing ? "" : "(非严格单调)"}</span>
        <span className={flat ? "pr-ag-chip is-firm" : "pr-ag-chip is-soft"}>token 省{flat ? "结构性·近 flat" : "spread 偏大·非 flat"} · spread <b>{h2.token_saving_spread.toFixed(3)}</b> {flat ? "&lt;0.05 ✓" : "≥0.05 ✗"}</span>
        <span className="pr-ag-chip is-soft">H2a 前沿(Tier-2·浏览器抓取·不可复现):ΔF1 <b>≈0</b> ≤ {shortModel(cmpModel)} {cmpGain.toFixed(3)} {fm?.confirm_rule_met ? "✓ 满足" : "✗"}</span>
      </div>

      <svg className="pr-ag-h2-chart" viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label="能力(naive F1)对质量增益与 token 省的剪刀图:质量增益随能力下降趋近 0,token 省结构性近 flat;前沿点为浏览器手测、不可复现">
        <line x1={L} y1={T} x2={L} y2={T + ph} className="pr-ag-h2-axis" />
        <line x1={L} y1={T + ph} x2={L + pw} y2={T + ph} className="pr-ag-h2-axis" />
        {[0, 0.2, 0.4, 0.6].map((v) => (
          <g key={v}>
            <line x1={L - 3} y1={y(v)} x2={L} y2={y(v)} className="pr-ag-h2-axis" />
            <text x={L - 6} y={y(v) + 3} className="pr-ag-h2-tick" textAnchor="end">{v.toFixed(1)}</text>
          </g>
        ))}
        {[0.6, 0.7, 0.8, 0.9, 1.0].map((c) => (
          <g key={c}>
            <line x1={x(c)} y1={T + ph} x2={x(c)} y2={T + ph + 3} className="pr-ag-h2-axis" />
            <text x={x(c)} y={T + ph + 14} className="pr-ag-h2-tick" textAnchor="middle">{c.toFixed(1)}</text>
          </g>
        ))}
        {/* subtle non-API zone (browser-captured frontier) — muted, NOT a climax */}
        <rect x={ghostX0} y={T} width={L + pw - ghostX0} height={ph} className="pr-ag-h2-ghostzone" />
        <text x={(ghostX0 + L + pw) / 2} y={T + 11} className="pr-ag-h2-ghosttext" textAnchor="middle">非 API·手测</text>
        {/* flat token reference (welded to the headline saving) */}
        <line x1={L} y1={refY} x2={L + pw} y2={refY} className="pr-ag-h2-ref" />
        {/* token line + points (the FIRM half — full contrast) */}
        <polyline points={tokPts} className="pr-ag-h2-tok" />
        {rows.map((r) => (
          <circle key={`t${r.model}`} cx={x(r.capability_naive_f1)} cy={y(r.token_saving)} r={3.6} className="pr-ag-h2-tokdot" />
        ))}
        {/* quality line + confidence-coded points (the CONTESTED half) */}
        <polyline points={qualPts} className="pr-ag-h2-qual" />
        {rows.map((r) => (
          <circle key={`q${r.model}`} cx={x(r.capability_naive_f1)} cy={y(r.quality_gain)} r={3.8}
            className={qualFilled(r.model) ? "pr-ag-h2-qualdot is-firm" : "pr-ag-h2-qualdot is-weak"} />
        ))}
        {/* Tier-2 frontier — MUTED hollow diamond + dashed projection; token UNMEASURED ⇒ a dashed "未测" tick */}
        {fm && fm.reproducible === false && last && (
          <g className="pr-ag-h2-frontier-g">
            <line x1={x(last.capability_naive_f1)} y1={y(last.quality_gain)} x2={x(fm.capability_naive_f1)} y2={y(fm.quality_gain)} className="pr-ag-h2-proj" />
            <path d={diamond(x(fm.capability_naive_f1), y(fm.quality_gain), 5)} className="pr-ag-h2-frontier" />
            <text x={x(fm.capability_naive_f1)} y={y(fm.quality_gain) - 8} className="pr-ag-h2-frontxt" textAnchor="middle">GPT-5.5 ≈0</text>
            <line x1={x(last.capability_naive_f1)} y1={refY} x2={x(fm.capability_naive_f1)} y2={refY} className="pr-ag-h2-proj is-tok" />
            <text x={x(fm.capability_naive_f1)} y={refY - 6} className="pr-ag-h2-frontxt" textAnchor="middle">未测 token</text>
          </g>
        )}
        <text x={L + pw / 2} y={H - 4} className="pr-ag-h2-axlabel" textAnchor="middle">能力 = 每模型 naive-RAG 平均 F1(不含 axiom 层 · 任务局部)</text>
        <text x={12} y={T + ph / 2} className="pr-ag-h2-axlabel" textAnchor="middle" transform={`rotate(-90 12 ${T + ph / 2})`}>质量增益 ΔF1 / token 省比</text>
      </svg>

      <div className="pr-ag-h2-legend">
        <span><i className="sw tok" /> token 省(H2b 结构性·~flat)</span>
        <span><i className="sw qual" /> 质量 ΔF1(H2a 随能力↓ · 实心=该模型全格 CI&gt;0)</span>
        <span><i className="sw front" /> ◇ GPT-5.5 前沿(Tier-2·浏览器抓取·不可复现·token 未测)</span>
      </div>

      {/* H2b flat-line caveat — adjacent to the very claim it qualifies (the solid flat blue line) */}
      <p className="pr-ag-h2-bnote">▸ “省 token 近 flat”由上下文体量决定(axiom 上下文 ≈ naive 的 40%),但仅在 <b>3–4 个本地同族模型 + 单一合成 logistics 基底</b>上验证,非通用「模型无关」证明;前沿点 token <b>未测</b>,其 flat 延续为<b>推断</b>(画作虚线)。</p>

      {/* data backstop table — the exact numbers + rank order, zero implied regression line */}
      <div className="pr-ag-matrix pr-ag-h2-matrix">
        <div className="pr-ag-matrix-head"><span>模型(按能力升序)</span><span>能力 naive-F1</span><span>质量增益 ΔF1(/{QSCALE.toFixed(2)};CI&gt;0?)</span><span>token 省</span></div>
        {rows.map((r) => (
          <div className="pr-ag-row" key={r.model}>
            <span className="pr-ag-cellname">{shortModel(r.model)}</span>
            <span className="pr-ag-cellnum">{r.capability_naive_f1.toFixed(3)}</span>
            <div className="pr-ag-cellbar">
              <Bar frac={r.quality_gain / QSCALE} kind={qualFilled(r.model) ? "qual" : "qual-weak"} label={`+${r.quality_gain.toFixed(3)}`} />
              <span className={qualFilled(r.model) ? "pr-ag-sig is-yes" : "pr-ag-sig is-no"} title={qualFilled(r.model) ? "该模型每格 95% CI 均 >0" : "至少一格 CI 跨 0 ⇒ 判不定(条形已弱化)"}>
                {qualFilled(r.model) ? "●" : "○"}
              </span>
            </div>
            <div className="pr-ag-cellbar"><Bar frac={r.token_saving} kind="save" label={pct(r.token_saving)} /></div>
          </div>
        ))}
        {/* Tier-2 ghost row — quarantined below a dashed amber rule, NEVER concatenated into `rows` */}
        {fm && (
          <>
            <hr className="pr-ag-tier2-rule" />
            <div className="pr-ag-row is-tier2">
              <span className="pr-ag-cellname">⚠ GPT-5.5 · 前沿(浏览器手测·不可复现)</span>
              <span className="pr-ag-cellnum">{fm.capability_naive_f1.toFixed(2)}</span>
              <div className="pr-ag-cellbar"><span className="pr-ag-h2-ph">≈0(4 naive+1 axiom,非 mean±CI)</span></div>
              <div className="pr-ag-cellbar"><span className="pr-ag-h2-ph">未测 token</span></div>
            </div>
          </>
        )}
      </div>

      <p className="pr-ag-verdict">
        {fm?.caveat} 读 <b>Spearman</b>(方向性),勿读脆弱的严格单调 bool:加入第 4 本地模型 qwen3.6-35b-a3b 会打破单调
        (其增益反高于 gemma-12b)但 Spearman 仍 &lt; −0.5;它 naive F1 &lt; gemma-31b ⇒ 是<b>内点、非更强模型</b>,如实保留<b>不剪</b>。
        承重披露:右端最承重的前沿点是<b>浏览器抓取、不可复现</b>的 Tier-2 单点,趋势仅 3–4 个本地点支撑,勿当平滑定律。
      </p>
    </section>
  );
}

// Decision/architecture summary — the SAME honest results at an AI-architect / PM register: precise terms
// (token, F1, CI, coreference, resolver, break-even, external validity) with crisp glosses, framed around
// cost / capability / risk. Not dumbed down, not buried in charts. Every number is pulled LIVE so the prose
// can never drift from the result.
function ExecSummary({ proto, split }: { proto: AxiomProtocol; split: SplitAblation }) {
  const save = pct(proto.headline.mean_input_token_saving);
  const tokSig = parseFrac(proto.headline.token_saving_significant_cells); // 12/12 — the hard claim
  const qsig = parseFrac(proto.headline.quality_gain_significant_cells); // 8/12 — "better" is only partly significant
  const minDelta = proto.headline.min_quality_delta;
  const q = splitPair(split, "qwen-3-8b-instruct"); // faithful model — its read-off ≈ the resolver ceiling
  const naiveF1 = (q.naive?.quality_f1 ?? 0).toFixed(2);
  const axiomF1 = (q.axiom?.quality_f1 ?? 0).toFixed(2);
  const ceil = split.resolver_accuracy.answer_f1_mean.toFixed(2);
  const gemmaAx = (splitPair(split, "google/gemma-4-12b-qat").axiom?.quality_f1 ?? 0).toFixed(2);
  const nStar = proto.build_amortization.breakeven_N_dictionary;
  return (
    <div className="pr-ag-plain">
      <p className="pr-ag-plain-lead">
        命题:在 LLM 前置一层<b>确定性语义地基</b>(跨源实体解析 + 预联结,规则式、build 成本 ≈ 0),用同等或更优答对率
        换更低 token 成本,并解锁裸 RAG 接不住的跨源任务。三条结论 + 可信度边界如下;图表与每格置信区间见右侧技术子标签。
      </p>
      <div className="pr-ag-plain-card">
        <h4>① 成本 · 同质量下输入 token 降 ~{save}</h4>
        <p>
          logistics 跨源任务,axiom 层 vs 裸 RAG,跨 3 模型 × 4 脏度 × 8 seed、每格 bootstrap 95% CI:<b>输入 token 均降 ~{save}</b>,
          且 <b>{tokSig.num}/{tokSig.den} 格显著</b>(CI 整段 &gt;0)——这是硬结论。质量 F1 <b>不降</b>(min ΔF1 {minDelta >= 0 ? "+" : ""}{minDelta.toFixed(3)}),
          其中 <b>{qsig.num}/{qsig.den} 格</b>统计显著更高,即「更准」在多数而非全部条件成立。增益<b>随数据脏度上升</b>(别名/单位漂移/乱码越多,裸 RAG 越崩、axiom 越稳)。
        </p>
        <p className="pr-ag-plain-analogy">
          ▸ 架构含义:增益主要来自<b>免 build 的结构</b>(互斥匹配 + 异常锚定 + 上下文压缩);学习式别名词典 +0.000 held-out F1
          ⇒ <b>摊销永不回本(N*{nStar == null ? "=∞" : `=${nStar}`})</b>——别为「学词典」单独投训练预算。本质是把 entity-resolution / join 从<b>推理时下推到确定性预处理层</b>。
        </p>
      </div>
      <div className="pr-ag-plain-card">
        <h4>② 能力 · 从「裸 RAG 不可解」到可解(enablement)</h4>
        <p>
          更强的一类:跨域共指——同一实体在两系统经变体改写、<b>无共享键</b>。裸 RAG 直接喂两域原始记录,faithful 模型(qwen-8b)
          <b>F1 ≈ {naiveF1}</b>:表面不可桥、LLM 自己接不上。先用确定性 resolver(域内 z-score 互斥匹配)做跨域对齐再喂,
          <b>F1 → {axiomF1}</b>,且 token 省 ~85%。这是<b>使能(enable)而非增量优化</b>。
        </p>
        <p className="pr-ag-plain-analogy">
          ▸ 上限:axiom-RAG 质量 = <b>resolver 精度(≈{ceil} answer-F1)× 模型转录忠实度</b>——qwen 顶到上界,gemma-12b 因过量生成只到 ~{gemmaAx}。
          结构地基决定「能不能做」,模型决定「读得忠不忠实」,两者都是瓶颈。耦合关系为<b>构造、答案已知</b>(单 latent 切分),非野外采集。
        </p>
      </div>
      <div className="pr-ag-plain-card is-caveat">
        <h4>③ 外部效度 · 一个决定性的诚实负结果</h4>
        <p>
          承重披露:上述 substrate 为<b>合成、答案已知</b>。当把 substrate 的可观测边缘<b>校准到真实数据</b>
          (sklearn breast_cancer 的噪声 / 变异系数 ~14× 高于手设值)后,此前漂亮的 nexus 三渠道收敛<b>塌回判不定</b>——
          说明该结果部分依赖「手设的不真实低噪声」。如实报告,确定性、可经 <code>/api/nexus_xdom/calibrate</code> 复现。
        </p>
        <p className="pr-ag-plain-analogy">
          ▸ 选型含义:<b>token-saving 与 enablement 在合成 cross-source 上稳健</b>,可作为「结构地基降本 + 解锁能力」的方向性证据;
          但任何「野外跨域发现」须自带真实校准,<b>别拿 demo 数据当生产证据</b>。本地模型 $=0 ⇒ 成本轴仅 token,未折真实美元。
        </p>
      </div>
    </div>
  );
}

type SubTab = "plain" | "tok" | "enable" | "cap";

export default function AxiomGainView() {
  const [proto, setProto] = useState<AxiomProtocol | null>(null);
  const [split, setSplit] = useState<SplitAblation | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<SubTab>("plain"); // default to plain-language for non-technical readers

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchAxiomProtocol("logistics_demo"), fetchSplitAblation()])
      .then(([p, s]) => { if (!cancelled) { setProto(p); setSplit(s); } })
      .catch((e) => !cancelled && setError(String(e)));
    return () => { cancelled = true; };
  }, []);

  const ready = proto && split;
  const SUBTABS: { id: SubTab; label: string }[] = [
    { id: "plain", label: "📋 摘要 · 架构/PM 视角" },
    { id: "tok", label: "① 成本：省 token（技术）" },
    { id: "enable", label: "② 能力：enablement（技术）" },
    { id: "cap", label: "③ 能力前沿：剪刀叉（H2）" },
  ];

  return (
    <div className="pr-ag">
      <div className="pr-ag-bar-top">
        <span className="pr-ag-title">结构化语义地基 · 成效（活下来、可引用的那条线）</span>
        <span className="pr-ag-note">本地模型 $=0 ⇒ 成本轴=真实 token · 确定性 / 冻结 fixture · 数字随结论挂诚实 caveat</span>
      </div>
      {error && <p className="pr-error">加载失败:{error}（先启动后端 :8200）</p>}
      {!error && !ready && <p className="pr-muted">加载中…（跑跨模型聚合 + bootstrap CI）</p>}
      {ready && (
        <>
          <nav className="pr-ag-subtabs" role="tablist" aria-label="分析子标签">
            {SUBTABS.map((t) => (
              <button key={t.id} role="tab" aria-selected={tab === t.id}
                className={tab === t.id ? "pr-ag-subtab is-active" : "pr-ag-subtab"} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </nav>
          {tab === "plain" && <ExecSummary proto={proto} split={split} />}
          {tab === "tok" && <Protocol p={proto} />}
          {tab === "enable" && <Split ab={split} />}
          {tab === "cap" && <CapGain p={proto} />}
          {tab !== "plain" && (
            <p className="pr-ag-foot">
              诚实边界:小规模 + <b>合成</b>数据(未接真实校准——nexus 的 Track 1 已演示「校准到真实可能塌」);
              本地 $=0 故只报 token;split 的耦合是<b>已知真值但构造的</b>(从一个 latent 切两半)⇒ 外部效度上移未闭合。
            </p>
          )}
        </>
      )}
    </div>
  );
}
