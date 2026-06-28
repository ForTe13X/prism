# 研究设计 · 公理逻辑网的增益测量 (axiom-net gain)

> **状态:研究设计锚(methodology note),非已建成、非指令。** 旁观会话据作者好奇整理,供取舍。
> 关联:[`OBSERVER_NOTES.md`](OBSERVER_NOTES.md) · [`DEMANDS.md`](DEMANDS.md)(learning metrics / 调用 cost 监控)· [`DESIGN_what_if_sequential.md`](DESIGN_what_if_sequential.md) · 待写的 `DESIGN_data_package.md`(§9)。

## 0. 一句话
量"公理逻辑网值不值":同等质量下省了多少 token / $ / 调用次数,每轮 learning 的边际成本与收益,以及不同 LLM 上增益的差异。**只有诚实地把分母(对照、held-out、质量、建造成本)算进去,数字才是研究,不是营销。**

## 1. 假设(要被证伪的,不是"它很有用")
- **H1**:axiom-net ON 在**同等答案质量**下,降低 (输入+输出 token / 调用次数 / $)。
- **H2(更有意思)**:**增益与模型能力反相关**——弱/小模型(qwen3-8b/gemma)增益 > 强模型(它本就会推理)。

## 2. 反事实:没对照就没 gain
- **Ablation**:同模型 / 同任务 / 同 prompt,**只切 axiom-net 一个开关**(ON/OFF)。
- baseline 必须**公平且具名**,至少两档:
  - `naive` —— 无 axiom,直接 prompt;
  - `rag` —— 无 axiom 但对原始多源数据做检索注入(**这才是真正要赢的对照**:证明结构化 axiom 优于裸 RAG)。
- 永远报 **"gain over〈baseline 名〉"**,不裸说 gain。

## 3. 四轴分开测 + 合并成本模型
| 轴 | 量的是 |
|---|---|
| 输入 token | 提示(含注入的 axiom / 检索片段) |
| 输出 token | 生成 + 推理 |
| 调用次数 | LLM calls + tool calls |
| 质量 | 任务正确性 / 评分 |

注入 axiom 常**加**输入 token 却**减**输出/调用——别只盯一轴。合并成本 `= Σ(in·$in + out·$out) + calls·固定开销`,`$/token` 来自一张**显式 pricing 表**(每模型一行,本地模型按电/算力折算或记为 0 但**单列**)。

## 4. headline = 成本×质量**前沿**,不是单数
"便宜但答错"不是 gain。固定质量比成本,或画 cost–accuracy 前沿。单指标首选 **cost per correct(每正确答案成本)**。

## 5. 建造成本 + 摊销曲线(核心,最有研究味) · 已落地 → §11b
axiom-net = **一次性 BUILD 成本**(learning loop 自己烧 token/calls)+ **每查询 SAVING**。
- 真 gain(N 次查询)`= saving·N − build`。
- 画**累计成本 with vs without ~ N** 两条线 → **break-even N\***(回本点)。
- **"每轮 learning iteration"**:逐轮记 `(该轮建造增量成本, 该轮带来的推理收益增量)`;边际收益跌破边际成本即**该停**。这条边际曲线本身就是结果。

## 6. 跨 LLM:矩阵 + 抓交互
- 拆成两个独立实验:(a) 谁**用** axiom-net 更省(inference 端);(b) 谁**建**得更省/更好(learning 端)。
- 测 `模型 × {ON,OFF} × 任务集`,**死盯交互项**(H2)。小模型增益显著更大 ⇒ "小模型 + axiom = 便宜够用"的硬证据。

## 6b. 脏度轴 + robustness(接 [`DESIGN_data_package`](DESIGN_data_package.md) §4c)
把数据**脏度**做成旋钮(0=干净 → 高,可分维度:身份脏率 / 缺失率 / 冲突率 …)⇒ gain 多一根轴 **`gain × dirtiness`**。
- **假设**:axiom-net 对 RAG 的**优势随脏度增长**(canonical 解析 + 约束本就是鲁棒机器)。这条曲线若成立 = "体现 robustness"最硬的结果;不成立也极重要(说明 axiom 没那么扛脏)。
- **robustness 的可测定义**:准确率随脏度的**退化曲线**,with vs without axiom-net——**退化越平 = 越鲁棒**。
- 纪律:污浊须**保留干净 ground-truth**(考"从脏捞真");LLM 生成的脏**预烤成冻结 fixture** 保证可复现(见 §7)。

## 6c. 判别区间 + 防"对着自己方法配题"(接 [`DESIGN_data_package`](DESIGN_data_package.md) §4d)
基准要落在**判别区间**:with / without 分数**拉得开**。都 ~100%(题太易)或都 ~0%(题太难)= floor/ceiling 废题,**无判别力**。
- **脏度 / link 显眼度这些旋钮强到能"造出任何想要的结果"** ⇒ 甜区**必须**由**与被测方法无关的独立判据**、且在**测 axiom-net 之前预注册**定:**「裸 RAG 吃力」∧「oracle(满上下文强模型 / 知真值的检验器)能复原」**。事后照着你的方法调难度 = **teaching to the test = 自欺**。
- 每条弱化的 link / 脏化须经 **oracle 验"可复原"**,确保"**难而非不可能**"(否则只是噪声,惩罚所有人,无信号)。

## 7. 研究卫生(否则只是 demo,不是研究)
- **held-out 任务集**:axiom 不得在被测任务上调过(否则测的是过拟合,不是泛化)。把 SPI 的 in-sample-bias / walk-forward 纪律原样搬来。
- **多 seed、报 mean ± CI**:gain 必须 **> 噪声**(LLM 本就抖;温度固定 + 多跑)。
- pin 模型版本 / prompt / 任务集版本;留**原始 per-call log**。可复现 = 研究门槛。

## 8. 插桩点(= 实时监控的离线版)
LLM 调用口(`backend/app/llm_client.py`)每次记 `{model, in_tok, out_tok, calls, $, latency, correct?}`。
- **离线**:批量跑 held-out → 本研究的表/曲线;
- **实时**:同一份记录喂 `DEMANDS.md` 的"learning metrics / cost 监控看板"。**一件事的两个时态。**

## 9. 数据基底(硬依赖)
本基准要一份**异构、够扎实**的多源数据包(时序 / SQL / NoSQL / 文档 / 新闻),且任务要**跨源**——**跨源正是 axiom-net 该赢裸 RAG 的地方**。见 [`DESIGN_data_package.md`](DESIGN_data_package.md)。
> **held-out 的诚实性,取决于数据基底的诚实性**(来源合规 + 不泄漏 + 可复现)。
>
> **状态:数据基底的确定性 substrate 已落地(DP1)** —— `logistics_demo` 一场景(SQL+时序+新闻)、预埋跨源真值、脏度/link 旋钮、以及**确定性的判别力骨架**(naive vs linked vs oracle,见 `DESIGN_data_package` §10)。本节的 with/without **LLM-ablation**(naive-RAG vs axiom-RAG + §3–§8 的成本/质量/摊销/跨模型)即建在其上,是下一块。

## 10. 不要做(废数陷阱)
- ❌ 稻草人 baseline(没人真用的"全塞 context");❌ 在 axiom 训练过的任务上测;❌ 忽略 build 成本只报每查询节省;❌ 降质量换成本却当 gain;❌ 单次跑、gain 落在噪声里;❌ 只报 token 不报 $/calls/quality。

## 11. 实现状态(DP2,ablation 端到端首跑已落地)
`backend/app/axiom_layer.py`(clean-room canonical 解析:异常锚定 + 别名归一,**不读 corruption_map**)+ `benchmark.py`(naive-RAG vs axiom-RAG,同模型同 prompt 只换上下文;token 插桩 + **冻结 fixture** 保证可复现)+ `GET /api/axiomgain/{id}`。LLM 调用走 `llm_client.structured_complete` 的 fixture 缓存。

**首跑结果**(`logistics_demo`,4 held-out seeds × {qwen3-8b, gemma-12b-qat} × {dirt 0, 0.6};本地 $=0,故用 **tokens-per-correct**):

| 模型 | 脏度 | naive-RAG F1 | axiom-RAG F1 | 输入 token 比 | tok/correct 比 |
|---|---|---|---|---|---|
| qwen3-8b | 0.0 | 0.92 | **1.00** | 0.41 | 0.45 |
| qwen3-8b | 0.6 | 0.84 | **0.95** | 0.37 | 0.40 |
| gemma-12b | 0.0 | 0.81 | **0.92** | 0.42 | 0.44 |
| gemma-12b | 0.6 | 0.53 | **0.87** | 0.39 | 0.29 |

- **H1 成立(首跑)**:axiom-RAG **质量≥naive 且输入 token ≈40%**(每正确答案省 55–71% token)。
- **§6b robustness 成立**:**增益随脏度增长**(gemma +0.11→**+0.34**;naive 0.81→0.53 崩,axiom 0.92→0.87 稳)。
- **H2 的诚实读法**:此处 gemma-12b 增益 > qwen-8b,但**因为 gemma 在 naive 上更差**(量化模型对原始跨源更吃力)——增益最大处=naive baseline 最弱处,与"参数量"不直接挂钩。
- **诚实边界**:**小规模首跑**(无多 seed CI、无 $ 定价、单场景);naive-RAG 给的是真原始多源(非稻草人)。完整研究(跨模型矩阵 + CI + cost frontier + agentic 解析器 + 真实校准)是后续。

### 11b. §5 建造成本 + 摊销已落地(确定性,含诚实负结果)
`backend/app/axiom_learn.py`(**学习式** canonical 解析:别名词典从『训练集』各包 `corruption_map['aliases']` 增量挖出,**有真 build 成本**;held-out 永不暴露自身 corruption_map,train/eval seed 不相交)+ `backend/app/amortization.py` + `GET /api/axiomgain/{id}/amortization`。全确定性/离线(学习与解析无 LLM;每查询实测 token 取自冻结 fixtures 作旁证)。把 §11 那条「算法式⇒build≈0、摊销平凡」**实测化**,结果是一个**价值分解**——也是**部分负结果**(§10 要的,胜过造假增益):

(数值取自 `run_amortization('logistics_demo')`,eval=manifest held-out seeds、dirt=0.6;energy 同形,见括注)

| 成分 | held-out F1 | build 成本 | 是否摊销 |
|---|---|---|---|
| basic linked(OR-of-cues,无互斥) | 0.625 | — | — |
| **+ 结构性公理**(互斥匹配 + 观测异常帧锚定 + 时间优先打分,三者合力) | 0.95(**+0.325**) | **免 build** | 真增益,即时 |
| **+ 压缩/预联结** | 同上 | **免 build**(空词典即生成正确紧凑上下文) | 真增益,即时 |
| **+ 学习式别名词典** | 0.95(**+0.000**) | ≈4.4k est-token(收敛第 4 轮,4414;energy 4264) | **永不**(N\*=∞) |

- **结论**:axiom 层的真实增益**全部来自免 build 的结构性联结**(互斥匹配 + 异常帧锚定 + 时间优先,合力 +0.325;及压缩)与下游 LLM 读取优势(§11);**唯一有 build 成本的成分(学习式别名词典)在本任务族零边际准确率增益**(两域、脏度 0/0.3/0.6/0.9 全为 0)——因为跨源联结**锚定在观测到的指标异常帧**,不靠实体归一,故词典从不改变归因。其 break-even N\*=∞。注:`+0.325` 是**三个结构改动合力**,非单靠互斥(单加互斥到 news-帧打分反而 ≈0.60,低于 basic)。
- **诚实**:学习器**确实学对了**(收敛时 held-out F1 == 算法式,parity 通过)⇒ 0 增益是**任务性质**而非学习器坏掉;build 成本为**估算 token**(非模型实测,真 LLM build 只会更贵 ⇒ 摊销差距下界);若把压缩收益错记到词典 build 上,名义 N\*≈16(=4414/285,energy≈15),但压缩本不需词典 ⇒ 真值=∞。

### 11c. 已落地:**完整协议**——跨模型矩阵 × 多 seed mean±CI + cost 前沿 + robustness 曲线(一个真 mini-result)
`backend/app/axiom_gain_protocol.py`(`run_protocol`,确定性聚合)+ `GET /api/axiomgain/{id}/protocol` + 8 测试。把 §11 的**点估**升成 §4/§6/§6b 要的**带不确定性的研究结果**:`run_ablation` 逐**单 seed**(全 cached ⇒ 快、确定)取回每格,再做**每格 deterministic bootstrap 95% CI**(复用 Prism 自有 `_unit` 哈希;同 nexus 的「报 mean±CI、CI 跨 0 即判不定」纪律)。前置 bugfix:`llm_client` 的 `response_format.json_schema` 缺 `name` ⇒ LM Studio 新版对**裸 schema** 一律 400(连带打挂 `/api/compile`);改为**规整**(预包裹的透传、裸 schema 补 `name`),fixture key 不变故旧 fixtures 全保。

**矩阵**:`logistics_demo`,**3 模型 × 8 held-out seed × 4 脏度(0/0.3/0.6/0.9)× {naive,axiom}-RAG**,96 格全 cached(0 失败,frozen fixtures)。本地 $=0 ⇒ 成本轴=**真实 token**。

| 模型 | 脏度 | naive F1 | axiom F1 | ΔF1(95% CI) | 输入 token 省 |
|---|---|---|---|---|---|
| qwen3-8b | 0.0 | 0.93 | 1.00 | +0.070 **[.014,.133]** | 59% |
| qwen3-8b | 0.6 | 0.75 | 0.91 | +0.156 **[.025,.363]** | 64% |
| gemma-12b | 0.3 | 0.66 | 0.85 | +0.190 **[.060,.347]** | 61% |
| gemma-12b | 0.6 | 0.53 | 0.80 | +0.271 **[.044,.526]** | 62% |
| gemma-31b | 0.0 | 0.92 | 1.00 | +0.081 **[.025,.163]** | 58% |
| gemma-31b | 0.6 | 0.78 | 0.91 | +0.130 **[.048,.230]** | 62% |

- **稳(CI 牢)**:**输入 token 平均省 ~61%,12/12 格 CI>0**;质量 ΔF1 **处处非负**(min=+0.070);**cost×quality Pareto 前沿由 axiom 点独占**(naive 一个都不在前沿——axiom 在**两轴**都更优);build 摊销 = **N\*=∞**(结构增益 +0.325 免 build、学习字典 +0.000,§11b)。
- **§6b robustness(端点 vs 趋势,诚实分开)**:端点 hi≥lo **3/3**,但**真单调只 1/3**——qwen 0.070→0.138→0.156→0.264(单增);gemma-12b 0.099→0.190→0.271→**0.103**、gemma-31b 0.081→0.124→0.130→**0.097** 都在 **dirt=0.6 见顶、最吵的 dirt=0.9 回落**(那两格 CI 跨 0=判不定)。故「increasing with dirt」真值=**1/3 单调**;naive 随脏崩、axiom 显著更稳,但**增益非全程单增**——不夸成 3/3。
- **§6 跨模型『抓交互』(同族 gemma 12b→31b,无族系混淆)**:方向上增益**随模型变大而缩小**(mean ΔF1 0.166 vs 0.108;31b 的 naive 本就更强 0.92 vs 0.80 ⇒ 结构脚手架对更弱模型帮助更大,§11「增益最大处=naive 最弱处」的受控方向)。**诚实限定:单对同族、两均值的点比、差值无 CI ⇒ 仅方向性,非 significance-tested**;per-dirt margin = [.018, .066, **.141**, .006],**除 dirt=0.6 外基本持平**(见 `model_scale_interaction.per_dirt_small_minus_large`)。
- **诚实边界(随结论挂)**:质量 ΔF1 仅 **8/12 格 CI>0**;4 格跨 0=判不定(3 格在 dirt=0.9 + 1 格 gemma-12b 干净 d0),不四舍五入成「全显著」;**小规模 + 合成数据**(未接真实校准——nexus 的 Track 1 已演示「校准到真实可能塌」,此处同样**未声称外部效度**);本地模型 **$=0 故只报 token 不报 \$**;未覆盖格(若有)在 `coverage` 字段,**绝不静默丢**。

### 11d. H2 能力轴:**方向上增益随能力缩小(Spearman −0.80),但严格单调被第 4 个模型打破**(预注册→已跑)
`run_protocol().h2_capability_vs_gain` + [`docs/PREREG_axiom_gain_frontier.md`](PREREG_axiom_gain_frontier.md) + 测试。**唯一未测的泛化**(OBSERVER §15):活下来那条线的证据几乎全是小本地模型;**更强的模型还受益吗?** 先**预注册**(§6c:让「缩小」是被预测、非输),再跑。能力代理 = **每模型 naive-RAG F1**(无 axiom 层时的任务胜任度,task-local;params 是坏代理)。前沿点经 OBSERVER §15 P1 决定**真跑了一个更大模型**(`qwen/qwen3.6-35b-a3b` Q4,8 seed × 4 脏度)。

| 模型(按能力升序) | 能力(naive F1) | 质量增益 ΔF1 | token 省 |
|---|---|---|---|
| gemma-12b | 0.620 | 0.166 | 0.608 |
| **qwen3.6-35b-a3b(新)** | **0.741** | **0.175** | 0.634 |
| qwen3-8b | 0.759 | 0.157 | 0.627 |
| gemma-31b | 0.807 | **0.108** | 0.608 |

- **H2a:方向成立、严格单调被打破**。4 模型 **Spearman(能力,增益)= −0.80**(增益仍随能力降),但新模型**落在单调线上方**(能力 0.741 处增益 0.175 > gemma-12b 的 0.166)⇒ `quality_gain_monotone_decreasing=False`。**读 Spearman,别读脆的单调旗**。**这正是预注册的价值**:预测了单调,数据说「负相关但非单调」,就照报。
- **它其实不是「前沿点」**:naive F1 0.741 **居中、低于 gemma-31b 0.807**——35B 的 a3b MoE 在本任务上**并不比 31B dense 更胜任**。故预注册的 Confirm 规则(前沿点 ΔF1 ≤ 0.108)**没被触发**:我们加了个**内点**,不是更高能力点。**真正的前沿区(naive F1 > 0.81)仍待跑**(需在本任务上确实更强的模型)。
- **H2b:确认**。新模型 token 省 0.634,spread 仍 **0.025 < 0.05**(结构性持平);头条「省 ~61%」**与模型无关**,如预测。
- **不删格**:这个离线点**保留并报**(删了能保「单调 −1.0」更好看,但那违反 DON'T #4)。复跑:`run_protocol(models=PROTO_MODELS+['qwen/qwen3.6-35b-a3b'])`。前置 harness 修:qwen3.6 是推理模型、LM Studio 把 json_schema 答案塞进 `reasoning_content`(`content` 空)⇒ `llm_client` 加了 content-空时回退 `reasoning_content` + 慢模型 `timeout` 透传。

### 11e. **真前沿点(GPT-5.5,浏览器抓取)——H2a 在前沿被确认**
本地候选 naive F1 封顶 0.81(非真前沿)。无前沿 API,故用 Chrome MCP 驱动一个 **GPT-5.5**(ChatGPT web,「极速」= low thinking)会话取一个**确实更强**的点。切片 **脏度 0.6,4 seed(naive)+ 1 axiom 校验**(浏览器驱动慢,诚实小样本)。

| 模型(脏度 0.6) | 能力(naive F1) | 质量增益 ΔF1 |
|---|---|---|
| gemma-12b | 0.532 | 0.271 |
| qwen3.6-35b-a3b | 0.715 | 0.193 |
| qwen3-8b | 0.751 | 0.156 |
| gemma-31b | 0.777 | 0.130 |
| **GPT-5.5(前沿)** | **0.950** | **≈ 0.00** |

- **H2a 在前沿确认**。GPT-5.5 **naive F1 最高(0.950**——它自己就完成跨源解析:ho-0/1/3 = 1.0;ho-2 = 0.8 仅因一条真发货被脏度 NULL 掉、它**正确地拒绝幻觉**它**)且质量增益最小(≈ 0**——axiom 上下文只是把它已能产出的答案递给它)。预注册 Confirm 规则(前沿 ΔF1 ≤ gemma-31b 的 0.108)**满足**(≈0.00 ≤ 0.108)。**结构化语义底座的「质量」红利在前沿能力处消失**——正是 H2a,而且这次是真更强的点(不像 qwen3.6 那个内点)。
- **H2b 此处未测(诚实缺口)**。web UI 无 token 计数 ⇒ GPT-5.5 的 token 省**没测**。它是**结构性的**(axiom 上下文恒约 40% 大小),故 ~61% 仍应成立——但对 GPT-5.5 而言它买到的是**token 省 + 质量几乎不变**,这是整个 H2 结果最有用的诚实表述。
- **诚实警示(放大声)**:取自「ChatGPT GPT-5.5 极速 @ 2026-06-28」的**浏览器抓取**、**非 API**:一次性、**不能对固定模型复跑**(仅记录值,未冻为 fixture);**无 token 计数**;**小样本**(脏度 0.6、4 naive + 1 axiom);prompt 换行被压成空格、每格一个 mojibake **干扰项**被还原(干扰项不影响答案);**该行不进 protocol 矩阵/fixtures**(离线不可复现)——它作为**已披露的手测**留在文档里。本地 API 行仍是可复现记录。详见 [`docs/PREREG_axiom_gain_frontier.md`](PREREG_axiom_gain_frontier.md)。

### 11f. **API 佐证点(deepseek-v4-pro,Ark,已冻结)——H2b 实测、能力持平(非前沿)**
有真实 API 后(Volcengine Ark `deepseek-v4-pro-260425`),按注册网格(8 seed × 4 脏度)**真跑一次并冻结入 fixture**
(离线可复现、serve 时 $0)。原本期望「API 模型 = 更高能力点」**在全网格未成立**,该负结果照实放大报告:

| 模型(全网格) | 能力(naive F1) | 质量增益 ΔF1 | token 省 |
|---|---|---|---|
| gemma-4-31b-qat(本地) | 0.8075 | 0.1082 | 0.6084 |
| **deepseek-v4-pro(API)** | **0.8083** | **0.1074** | **0.6349** |

- **能力是持平,不是更高**。deepseek 全网格 naive F1(0.8083)与 gemma-31b(0.8075)差 **0.001**,是平局而非前沿。
  逐脏度看,deepseek 在重脏度(d0.9 = 0.762 vs 0.708)**更稳**、在中脏度(d0.3/0.6)略弱,净持平。**一个 4-seed
  的 dirt-0.6 试跑曾给 0.872、看着像前沿——完整 8-seed 网格(d0.6 = 0.758)纠正了它**。诚实教训:小的「好看切片」
  会高估优势,注册网格才算数。
- **它的真正价值:跨模型佐证 + 实测 H2b**。一个完全不同的模型(前沿 API、不同架构)在**同等任务胜任度**下给出
  **同样的增益**(0.1074 ≈ gemma-31b 0.1082)⇒ H2a 不是本地模型的假象;~63% 省 token 由**真实 API `prompt_tokens`
  实测**(非 LM-Studio 本地计数),结构性 H2b 在商用 API 上也成立。5 点轴 Spearman(能力,增益)= **−0.90**。
- **诚实警示(放大声)**:(1)生产**有成本**(一次性付费 Ark 跑),serve 是 **$0**(冻结 fixture)。(2)该模型
  **不支持 response_format**(json_schema/json_object 皆不支持),故用 **prompt-JSON** + `_extract_json` 构造——与
  本地 strict-schema 行的**已披露构造差异**(prompt 已含 JSON 形状,F1/能力同法测量、可比)。(3)它是**推理模型、
  温度 0 仍逐次非确定**(试跑与冻结的逐格 F1 不同)——**冻结的 fixture 钉死一次采样**以求可复现,与本仓所有模型同。
  (4)它按行打标(`provenance.source = ark-api`),**绝不静默混入** $0/strict-schema 本地序列。真正的**前沿**
  (极高能力)点仍是浏览器 GPT-5.5(naive 0.95、增益 ≈0);deepseek 佐证的是曲线**中段**。

---
*—— 研究设计锚。这是给在建会话的方法学参照,不是指令;建造的人说了算。*
