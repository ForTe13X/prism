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

## 7. 研究卫生(否则只是 demo,不是研究)
- **held-out 任务集**:axiom 不得在被测任务上调过(否则测的是过拟合,不是泛化)。把 SPI 的 in-sample-bias / walk-forward 纪律原样搬来。
- **多 seed、报 mean ± CI**:gain 必须 **> 噪声**(LLM 本就抖;温度固定 + 多跑)。
- pin 模型版本 / prompt / 任务集版本;留**原始 per-call log**。可复现 = 研究门槛。

## 8. 插桩点(= 实时监控的离线版)
LLM 调用口(`backend/app/llm_client.py`)每次记 `{model, in_tok, out_tok, calls, $, latency, correct?}`。
- **离线**:批量跑 held-out → 本研究的表/曲线;
- **实时**:同一份记录喂 `DEMANDS.md` 的"learning metrics / cost 监控看板"。**一件事的两个时态。**

## 9. 数据基底(硬依赖)
本基准要一份**异构、够扎实**的多源数据包(时序 / SQL / NoSQL / 文档 / 新闻),且任务要**跨源**——**跨源正是 axiom-net 该赢裸 RAG 的地方**。见待写的 `DESIGN_data_package.md`。
> **held-out 的诚实性,取决于数据基底的诚实性**(来源合规 + 不泄漏 + 可复现)。

## 10. 不要做(废数陷阱)
- ❌ 稻草人 baseline(没人真用的"全塞 context");❌ 在 axiom 训练过的任务上测;❌ 忽略 build 成本只报每查询节省;❌ 降质量换成本却当 gain;❌ 单次跑、gain 落在噪声里;❌ 只报 token 不报 $/calls/quality。

---
*—— 研究设计锚。这是给在建会话的方法学参照,不是指令;建造的人说了算。*
