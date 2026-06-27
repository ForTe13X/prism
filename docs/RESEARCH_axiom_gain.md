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

## 5. 建造成本 + 摊销曲线(核心,最有研究味)
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
- **诚实边界**:axiom 层**算法式(无训练)⇒ build 成本≈0、摊销平凡**(学习式 axiom-net 才有真 build 要摊);**小规模首跑**(无多 seed CI、无 $ 定价、单场景);naive-RAG 给的是真原始多源(非稻草人)。完整研究(跨模型矩阵 + CI + cost frontier + 真 build 摊销 + agentic 解析器 + 真实校准)是后续。

---
*—— 研究设计锚。这是给在建会话的方法学参照,不是指令;建造的人说了算。*
