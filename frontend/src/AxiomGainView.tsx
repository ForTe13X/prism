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

export default function AxiomGainView() {
  const [proto, setProto] = useState<AxiomProtocol | null>(null);
  const [split, setSplit] = useState<SplitAblation | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchAxiomProtocol("logistics_demo"), fetchSplitAblation()])
      .then(([p, s]) => { if (!cancelled) { setProto(p); setSplit(s); } })
      .catch((e) => !cancelled && setError(String(e)));
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="pr-ag">
      <div className="pr-ag-bar-top">
        <span className="pr-ag-title">结构化语义地基 · axiom-gain（活下来、可引用的那条线）</span>
        <span className="pr-ag-note">本地模型 $=0 ⇒ 成本轴=真实 token · 确定性 / 冻结 fixture · 数字随结论挂诚实 caveat</span>
      </div>
      {error && <p className="pr-error">加载失败:{error}（先启动后端 :8200）</p>}
      {!error && (!proto || !split) && <p className="pr-muted">加载中…（跑跨模型聚合 + bootstrap CI）</p>}
      {proto && <Protocol p={proto} />}
      {split && <Split ab={split} />}
      {(proto || split) && (
        <p className="pr-ag-foot">
          诚实边界:小规模 + <b>合成</b>数据(未接真实校准——nexus 的 Track 1 已演示「校准到真实可能塌」);
          本地 $=0 故只报 token;split 的耦合是<b>已知真值但构造的</b>(从一个 latent 切两半)⇒ 外部效度上移未闭合。
        </p>
      )}
    </div>
  );
}
