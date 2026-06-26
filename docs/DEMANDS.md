# Prism — 作者需求捕获 + 旁观者映射 (2026-06-26)

> §1 是**作者的 demands**(原样捕获,是要求)。§2–§4 是**旁观者的映射/批注**(视角,非强制)。
> 总纲不变:领域无关(规则只在 spec + 引擎)、确定性、诚实(合成/外推/置信永远标注)。

---

## §1 作者 demands(原样)

1. **前端 DOM 级可用且符合预期**;LLM 相关特性暂用 **LM Studio 的 qwen3-8b 或 gemma-12b-qat 做 live test**。
2. **技术文档实时同步**:API / 后端 / 前端 / 产品 / 用户手册 / 测试用例 等。
3. **及时发现潜在 TODO 与整改项**,持续优化设计与实现。
4. **axiom learning / self-evolving**:做一个 **cockpit 看板** + **主动 run 机制(默认 scheduled job)**,供技术人员查看。
5. 看板上可含:**attribution trace、explanatory analysis、其他 metrics、visualization、change 变动、基模调用 cost** 等监控。
6. 内容太多时用 **nested tabs / sidebar** 组织。

---

## §2 旁观者映射:每条怎么干净落进 Prism

### 核心洞见:监控看板 = 一份 Prism spec(dogfooding)
demand 4–6 不要造新子系统。把"自演化循环"当一个运营域,用 spec 描述、用现有引擎渲染:
- 实体 `job`:run_id / status(status 语义→上色)/ started / duration / **cost**(metric)/ trigger(scheduled|manual)。
- 实体 `evolution_event` 或 `axiom`:changed_what / before→after / confidence(gauge)/ adopted(status)。
- 实体 `metric`:学习指标随帧变化(timeseries)。
- 实体 `model_call`:model / tokens_in/out / **cost** / latency。
- 关系:`job produces evolution_event`、`evolution_event supported_by model_call`……→ 本体图谱直接画出"哪个 run 改了什么、依据哪次模型调用"。
→ attribution / metrics / 可视化 / 变动 / cost / nested tabs **全部从已有 widget resolver + 时间帧回放 + 本体图谱白捡**,零 bespoke UI,且保持领域无关。
- **nested tabs / sidebar**:做成 spec 的 `views` 分组(小扩展:`view_group`),仍是 spec 驱动,不写死。

### demand 4 的诚实红线(防"自演化"变剧场)
"self-evolving"必须有**真实信号**,否则就是好看的空转。三选一,且必须标清:
- (a) **真学习**:从累积帧重拟动力学参数(drift/volatility)、或从数据挖关系/阈值(axiom mining)——是真的、可解释的。
- (b) **半真**:规则化的自调整(命中率反馈调权重),标注"启发式"。
- (c) **纯示意**:暂无真信号 → **明确标注 demonstration**,看板演示的是"监控"而非"学习器"。
**attribution / explanatory 必须展示真实计算出的贡献,不是编一个合理故事。** 这是整组 demand 里最容易滑向"工业垃圾"的一处。

### demand 5 的 cost 监控
`model_call.cost = tokens × 单价`。本地 LM Studio 单价记 0,但**scaffold 是真的**(tokens/latency 真实采集);接付费 API 时换单价即可。按 job 聚合、随帧出趋势。

### demand 1:DOM 级 + 本地 LLM 验证
- LLM client **env 驱动**:base_url→LM Studio(:1234)、model 名可配(qwen3-8b / gemma-12b-qat)。
- 验证 = **真实渲染的 DOM 断言 + 截图**,不是"编译过了"就算;LLM 特性(P6 生成 spec、explanatory)对着本地模型 live 跑。
- **坑(前车之鉴)**:LLM 调用失败时**别静默回退到 mock 模板**冒充真实输出——回退要可观测(计数 + 原因 + 一个 /health 暴露)。

### demand 2:文档实时同步(用 spec-as-source 把成本压到最低)
Prism 是 spec 驱动 → 很多"文档"可**生成**,不靠手抄:
- API 文档:FastAPI 自带 OpenAPI(`/docs`)。
- "有哪些实体/属性/semantic_type/视图":直接由 specs 渲染成参考页。
- 控件目录:由 widget resolver 的分支生成。
- 手写叙事(产品/用户手册)→ 配一个 `docs:check`(代码/spec 与文档漂移即失败),把"实时同步"变成可执行的闸,而非自律承诺。

### demand 3:潜在 TODO / 整改(持续旁观)
形成"周期性旁观 → 带日期评审 + 受跟踪 TODO"的回路;非平凡改动走 merge 前对抗评审。本轮已浮现的见 §3。

---

## §3 本轮巡检浮现的 TODO / 整改(具体)

- **[高] 把已建好的轨迹仿真接上**:`/api/sim`(`backend/app/sim_routes.py`)未进 `main.py`、前端未消费。最差异化、最出片、学习密度最高的那块**在仓库里睡着**。接线见 `OBSERVER_NOTES.md` §7。
- **[中] 回放语义**:当前 slider 是"过去/演化",还不是"未来/决策"。把右侧延成模拟未来(扇形带 + 情景对比 + verdict)——与 §2-dogfooding 之外的另一条主线。
- **[低] a11y**:`OntologyGraph` 节点 `<g>` 有 `role="button"`/`tabIndex` 但无 `onKeyDown`,键盘选不中;补 Enter/Space。
- **[低] 本体图谱的边是"确定性合成实例映射"**(哈希随机挑 `to` 行),非真实关系。当 viz 没问题(且已标注);但若将来"沿 relations 传播"驱动仿真,会沿随机边传播——届时需用真实关系或显式标注。
- **[贯穿] 未来侧/学习侧一旦出现,诚实标注三类来源(实测/示意/声明动力学)+ 置信带**。

---

## §4 范围与 for-fun 提醒

这组 demand 体量不小(等于一个可观测性 + 自演化子系统)。在"for fun / 学习"框架下这**很好**——调度、可观测、attribution、cost、dogfooding 全是学习汁水足的东西。两条提醒:
1. **当好奇心清单,别当义务 backlog**:哪块现在最挠你就先抓哪块;允许半成品、允许跑偏。
2. **dogfooding 优先**:监控看板用 Prism 自己的 spec/引擎实现,会让这组 demand 的大半"白捡",同时验证引擎的通用性——一举两得。

*—— 需求已捕获;旁观映射是视角,建造的人定夺。*
