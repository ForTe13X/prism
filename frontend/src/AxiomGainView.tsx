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

// 说人话 — the SAME honest results in plain language for a non-technical reader: analogies, no jargon, and
// the caveats translated (not dropped). Numbers are pulled LIVE from the fetched data so the plain words can
// never drift from the real result.
function PlainLanguage({ proto, split }: { proto: AxiomProtocol; split: SplitAblation }) {
  const save = pct(proto.headline.mean_input_token_saving);
  const qsig = parseFrac(proto.headline.quality_gain_significant_cells); // e.g. 8/12 — "better" is only PARTLY certain
  const q = splitPair(split, "qwen-3-8b-instruct"); // the faithful model — its read-off ≈ the resolver ceiling
  const naiveF1 = (q.naive?.quality_f1 ?? 0).toFixed(2);
  const axiomF1 = (q.axiom?.quality_f1 ?? 0).toFixed(2);
  return (
    <div className="pr-ag-plain">
      <p className="pr-ag-plain-lead">
        我们在验证一个想法:<b>先用一套确定性的「整理规则」把杂乱数据理顺,再交给 AI</b>——它能不能<b>又省又准</b>,
        甚至做到原本做不到的事?下面用大白话讲结论(想看图表和置信区间,点右边两个子标签)。
      </p>
      <div className="pr-ag-plain-card">
        <h4>① 同样答对,少读约 {save} 的内容(更省钱、更快)</h4>
        <p>
          让 AI 回答跨系统的问题,平常要把一大堆原始记录一股脑塞给它。我们先帮它把数据理好——把同一个东西的
          不同叫法认成一个、把相关的记录连起来——再给它一份整理好的摘要。结果:它要读的内容少了约 <b>{save}</b>(这点很确定),
          而且<b>至少一样好——从没更差</b>;多数情况下更好,但严格说「更好」只在约 <b>{qsig.num}/{qsig.den}</b> 的测试里统计上站得住(其余持平,说不准)。
        </p>
        <p className="pr-ag-plain-analogy">
          💡 类比:给员工<b>一页已经核对、连好关系的摘要</b>,而不是一摞原始单据。而且<b>数据越乱</b>(错别字、
          不同单位、不同叫法),这套整理<b>省下的越多</b>。
        </p>
      </div>
      <div className="pr-ag-plain-card">
        <h4>② 让 AI「从不会到会」</h4>
        <p>
          还有更难的题:同一个东西在两个系统里<b>长得完全不一样</b>,还没有共同编号。直接把两边原始记录给 AI,
          它根本认不出谁是谁——得分约 <b>{naiveF1}</b>(基本等于 0)。我们先用确定性的「对账」把它们一一认出来,
          它就答得出来了——得分升到约 <b>{axiomF1}</b>。
        </p>
        <p className="pr-ag-plain-analogy">
          💡 关键:这不是「省一点」,是<b>「从 0 到能做」</b>——这套结构地基<b>使能</b>了原本不可能的任务。
          (诚实说明:这里两个系统里「同一个东西」的对应关系是我们<b>构造出来、答案已知</b>的;真实场景里要认这种对应可能更难,且「对账」本身也不是 100% 准。)
        </p>
      </div>
      <div className="pr-ag-plain-card is-caveat">
        <h4>③ 我们也如实报告了不好看的地方(这正是它可信的原因)</h4>
        <p>
          <b>一次「翻车」:</b>之前在合成数据上有个漂亮的「跨域发现」。后来我们把合成数据的<b>噪声水平校准到一份
          真实数据</b>,那个发现就<b>塌了</b>——说明它有一部分是「数据太干净」撑出来的。我们如实写下这次翻车,
          因为诚实的负结果比假装成功更有价值。(确定性、可经 <code>/api/nexus_xdom/calibrate</code> 复现)
        </p>
        <p className="pr-ag-plain-analogy">
          ⚠ 适用边界:以上都在我们<b>自己造的、答案已知的小规模合成数据</b>上测;真实世界更复杂,数字不保证照搬。
          本地模型不花钱,所以只比「读了多少内容」,没比真实美元。
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
    { id: "plain", label: "📖 说人话" },
    { id: "tok", label: "① 省 token（技术）" },
    { id: "enable", label: "② 让 AI 从不会到会（技术）" },
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
          {tab === "plain" && <PlainLanguage proto={proto} split={split} />}
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
