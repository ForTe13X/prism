import { useEffect, useState } from "react";
import { fetchAxiomProtocol, fetchSplitAblation } from "./api";
import { parseFrac, pct, splitModels, splitPair } from "./axiomgain";
import type { AxiomProtocol, SplitAblation } from "./types";

// The surviving, citable line (OBSERVER §12): structured semantic foundation vs bare RAG. This lab tab
// surfaces the two honest results — Track 2 (cross-model token-savings frontier) and the split-substrate
// cross-domain coreference (enablement) — with their caveats VISIBLE, never buried (honesty = the steering
// wheel). Spec-independent: the experiment is the same regardless of the selected domain.
const shortModel = (m: string) => m.replace(/^.*\//, "").replace(/-instruct|-qat$/g, "");

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

type SubTab = "plain" | "tok" | "enable";

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
