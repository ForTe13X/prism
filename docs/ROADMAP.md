# Prism 路线图 — 从静态驾驶舱到时间轴 / 作业 / 自构建平台

> **怎么用这份文档**:在 `E:\Documents\Dev\prism` 起一个新会话,先读 `README.md` + `docs/SPEC_FORMAT.md` +
> 这份 `ROADMAP.md`,然后从 **P1** 开始按阶段推进。每阶段都是一个**可跑可看 + 有测试**的增量。

## 0. 不可动摇的命门(每个特性都必须守)

**Prism 的全部价值在于:UI 与后端逻辑都是 spec 的纯函数,领域无关。** 下面每一个特性都必须:
- **spec 驱动**:行为由声明式的语义地基决定,绝不为"管网/图书"等具体领域写 if-else。
- **确定性**:数据/演化/预测全部由 `(spec_id, entity, frame, attr, …)` 的 sha256 哈希种子合成 —— 无 `random`、无时钟、逐字节可复现(便于 replay 一致)。把合成换成真实源时,只替换 `synth_*` 一层,API/前端不动。
- **加新能力 = 收敛到少数枢纽**:新 `semantic_type` 只改 `widgets.tsx` + `data_synth.py`;新分析类型只加一个 job handler;新领域只加一份 spec。

> 任何让某领域"特殊"的硬编码都是在背叛这个项目的核心命题 —— 评审时第一个查这个。

## 1. 现状(v0,已提交 1694b46)

- 后端 FastAPI:`specs_loader`(读 `backend/specs/*.json`)+ `data_synth`(按 `semantic_type` 确定性合成**当前快照**)+ `/api/specs|spec/{id}|data/{id}/{entity}`。
- 前端 Vite+React+TS:`widgets.tsx`(semantic_type→控件 resolver)+ `Cockpit.tsx`(views→tab,cards/table)+ `App.tsx`(领域切换+accent)。
- 两个对比领域(`infra_monitoring` / `library_catalog`)跑同一引擎。
- **缺口**:数据是**单一快照**,没有时间维度 —— 这是所有后续特性的前提。

## 2. 四个架构支柱

| 支柱 | 解锁 | 领域无关的做法 |
|---|---|---|
| **① 时间帧模型** | 演化 · replay · 预测 · 仿真 | `data_synth` 加 `frame` 轴;`?frame=N` 确定性返回第 N 帧;spec 声明哪些属性随时演化 + 帧数 |
| **② 本体图谱 + 画布回放** | ontology net 可视化(版本帧 + slider) | 图由 spec `entities`+`relations`(+实例边)生成;Canvas 布局;slider 逐帧重放 |
| **③ 作业引擎** | job 监控 · 主动 run | 分析/预测/仿真 = job(入队→状态→面板);定时/触发=主动 run |
| **④ 分析模块 + 构建工作流** | 分析 · 归因 · learning metrics · 语义地基构建 | 都读帧模型;构建走"生成方案→用户逐步确认→应用"的人确认工作流 |

## 3. 分阶段路线(每阶段 = 一个可交付增量)

### P1 — 时间帧 + 回放 slider 【keystone,先做这个】
所有时间相关特性的地基。
- **后端**:`data_synth` 引入 `frame` 维度。`GET /api/data/{spec}/{entity}?frame=N` 返回第 N 帧状态(哈希种子加入 `frame`)。新增 `GET /api/timeline/{spec}` 返回帧范围/标签(如 `{frames: 48, now: 36, step: "hour"}`)。spec 顶层加 `temporal: {frames, now, step}`,属性可加 `evolves: true`(随帧演化)/`drift`(漂移幅度)。**未声明 evolves 的属性逐帧不变**(身份类不动)。
- **前端**:`Cockpit` 顶部一条 **replay slider**(拖动选 frame);所有 widget 按当前 frame 取数;timeseries 显示"截至该 frame"的窗口。播放/暂停按钮(逐帧自增)。
- **领域无关性**:演化规则在 spec(`evolves/drift`)+ `data_synth`,不针对任何领域。
- **验收**:拖动 slider,站点压力/状态/H₂S、藏书借阅都逐帧变化且**确定性**(同 frame 同值);切领域 slider 仍工作。
- **测试**:后端同 frame 字节一致 + 不同 frame 有别 + 非 evolves 属性跨帧不变;前端 resolver 快照。

### P2 — 本体图谱画布 + 版本帧回放
- **后端**:`GET /api/graph/{spec}?frame=N` —— 由 `entities`(节点)+`relations`(边)+ 实例级边(如 sensor→station 的 `installed_at`,实例由确定性映射生成)构成;节点带该 frame 的状态(用于上色)。
- **前端**:Canvas/SVG 力导向或分层布局画图谱;复用 P1 的 slider 逐帧/版本重放(节点状态/颜色变、边增减)。点节点 → 侧栏看该实体详情(复用 widget resolver)。
- **领域无关性**:图纯由 spec 的实体/关系生成;布局通用。
- **验收**:两个领域都能画出图;拖 slider 看网络演化;点节点出详情。

### P3 — 预测 + 仿真  ✅ 已交付(复用旁观者的 `simulation` 引擎并接线;轨迹仿真统一了 forecast+simulate,见 `OBSERVER_NOTES.md` §7)
- **后端(已交付,统一为一个端点)**:`POST /api/sim/{spec}` body=`{entity, attribute, horizon, row_index?, scenarios[]}` —— 对 `metric/gauge/timeseries` 外推未来帧。**基线轨迹 = forecast**(无干预的那条);**scenarios = simulation**(`shift` 设定点 / `pulse` 脉冲)。每条带不确定带(多次确定性 roll 的 min/中位/max)、越限帧、`verdict`。动力学(`mean_revert` `rate`/`trend`/`volatility`)取自 spec `dynamics`。引擎自包含、确定性,见 `backend/app/simulation.py`。
  > 原计划的 `/api/forecast` + `/api/simulate` 两个端点被这一个统一端点取代(forecast 即 baseline-only run)。
- **前端**:时间轴延伸到"未来"区(扇形带);what-if 面板设干预 → 基线 vs 情景多线对比 + verdict;诚实标注合成/不确定。
- **领域无关性**:预测/仿真作用于 `semantic_type`(数值类),不认领域语义。
- **验收**:任一数值属性可外推 + 出带;干预后情景线与基线分叉。✅

### P4 — 作业引擎 + 监控 + 主动 run
- **后端**:轻量 job 模型(入队/运行/完成,确定性 mock 执行)。`POST /api/jobs`(type=analysis|forecast|simulate|build)、`GET /api/jobs`(列表+状态)、`GET /api/jobs/{id}`。"主动 run"=按 spec 声明的触发器/间隔自动入队(default off)。
- **前端**:**job 监控面板**(队列/运行中/历史 + 状态徽章,复用 status widget);一键触发;主动 run 开关。
- **领域无关性**:job 只编排分析模块,不含领域逻辑。
- **验收**:发起一个 forecast job → 面板看它从 queued→running→done;结果可回看。

### P5 — 归因分析 + learning metrics 监控
- **后端**:`GET /api/attribution/{spec}/{entity}/{attr}?frame=N` —— 解释"该指标在第 N 帧为何变":沿 `relations` 把变化分解到关联实体/驱动属性的贡献(确定性分解,贡献和=总变化,诚实标注是合成归因)。`GET /api/learning-metrics/{spec}` —— 若有学习回路(如 spec 质量分/合成保真度/构建工作流的接受率),逐帧/逐版本给指标序列。
- **前端**:归因瀑布/贡献条;learning metrics 监控面板(指标随时间)。
- **领域无关性**:归因走通用关系图分解;learning 指标是平台级(非领域级)。
- **验收**:点一个异常帧 → 出贡献分解(和自洽);learning 面板出指标趋势。

### P6 — 语义地基构建工作流(生成 + 用户逐步确认)
把"建 spec"本身变成 Prism 的一等功能 —— 呼应 SPI 的 register→review→approve,但泛化、人在环。
- **后端**:`POST /api/build/plan` body=样本数据/自然语言描述 → **生成一份构建方案**(有序步骤:建实体 / 推断每列 `semantic_type` / 设 range&threshold / 加关系 / 配视图),每步带理由 + 置信。`POST /api/build/apply` 只应用**已确认**的步骤,产出/更新一份 spec。
- **前端**:工作流视图 —— 逐步展示生成的方案,每步**用户确认/改/拒**(human-in-the-loop),确认后即时预览该步对驾驶舱的影响;全确认 → 落一份新 spec,领域下拉立刻出现。
- **领域无关性**:这是**元层**——它生产 spec,本身对领域零假设;`semantic_type` 推断是通用启发式。
- **安全**:绝不自动应用未确认步骤;生成的方案是**建议**,落盘需显式确认(与 SPI browser-ops 的 plan→confirm→execute 同纪律)。
- **验收**:喂一份陌生领域的样本 → 生成方案 → 逐步确认 → 出一个能用的新驾驶舱。

## 4. 你的 11 项诉求 → 阶段追溯(一项不漏)

| 诉求 | 落点 |
|---|---|
| 演化 | P1(帧模型) |
| replay | P1(slider) + P2(图谱版本回放) |
| ontology net 可视化(画布/版本帧/slider) | P2 |
| 预测 | P3 |
| simulation | P3 |
| 分析 | P5 + 贯穿 |
| 归因分析 | P5 |
| learning metrics monitor | P5 |
| job 监控 | P4 |
| 主动 run | P4 |
| semantic foundation 构建(生成 workflow + 用户确认) | P6 |

## 5. 工程纪律(沿用,逐阶段守)

- **确定性**:所有合成/演化/预测/仿真用哈希种子,无随机/时钟;replay 必须可复现。
- **测试**:每阶段后端(确定性 + 边界 + 空安全)+ 前端(resolver/组件)+ 关键路径 e2e。
- **每阶段一提交**,提交信息说清"领域无关性怎么守住的"。
- **对抗式自审**:每个增量提交前过一遍"哪里偷偷硬编码了领域 / 哪里破了确定性 / 哪个声称是真实的其实是合成的(要诚实标注)"。
- **诚实**:合成数据/归因/learning 指标都明确标注是"确定性合成示意",不冒充真实采集。

## 6. 跑起来(给新会话)

```bash
# 后端
cd E:\Documents\Dev\prism
python -m uvicorn backend.app.main:app --port 8200
# 前端
cd frontend && npm install && npm run dev   # http://127.0.0.1:5173
```

`.claude/launch.json` 已有 `prism-backend` / `prism-frontend` 两个配置(新会话的 preview MCP 在 prism 根目录下即可用)。
