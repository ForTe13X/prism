# Prism — 语义地基驱动的驾驶舱

[中文](#中文) | [English](#english)

## 中文

Prism 把一份语义 spec 变成完整的领域驾驶舱。tab、面板、控件、数据合成、时间回放、图谱视图和决策实验都由 spec 驱动；后端与前端本身保持领域无关。

这个仓库有两个目标：

1. 展示领域驾驶舱可以写成 `UI = f(spec)`。
2. 在受控合成数据上探索：LLM 前面加一层确定性的语义地基，能否减少上下文、并让跨源任务变得可解。

除非另有说明，README 中提到的研究结果都只适用于本仓的确定性合成 substrate。

### 界面示例

spec 描述实体、属性、semantic type、视图、关系与时间行为。同一套 runtime 可以从不同 spec 渲染不同领域。

20 秒动图速览:拖动时间帧 → 零代码切换领域(主题也随 spec 变化)→ 星系对齐回放 → axiom-gain 趋势。

![20 秒速览:时间回放、零代码换域、星系对齐回放、axiom-gain 趋势](docs/media/demo-highlights.gif)

![Prism 主驾驶舱:界面由 spec 折射而来](docs/media/readme_cockpit.png)

Prism 也包含跨域 nexus 实验。两个数据域被画成两组记录星系；只有通过证据与显著性检查的链接才会点亮。

![星系相撞:两个数据域,只有过检验的桥才发光](docs/media/readme_nexus_galaxy.png)

axiom-gain 实验比较两种上下文：原始多源数据 vs 预联结后的语义地基。

![axiom-gain 剪刀叉:能力越强增益越小,token 省是结构性的](docs/media/readme_axiom_gain.png)

相关仓库：[prism-datagen](https://github.com/ForTe13X/prism-datagen)，从本项目抽出的独立确定性数据包生成器。

### 核心理念

传统 dashboard 往往把领域视图硬编码在应用代码里。Prism 把这些结构上移到声明式语义 spec：

```text
语义 spec                 领域无关 runtime                  结果
──────────────────        ─────────────────────             ─────────────────
entities + attributes ->  backend 读取 semantic_type   ->    /spec 与 /data
views + relations         frontend 渲染 views                生成驾驶舱
temporal behavior         widget resolver 选择控件            UI = f(spec)
```

仓库自带两个差异明显的领域：

- `backend/specs/infra_monitoring.json`：工业基础设施监控。
- `backend/specs/library_catalog.json`：图书馆馆藏与分馆活动。

在 UI 中切换领域，即可看到同一套引擎从不同 spec 渲染不同驾驶舱。

### 研究实验

研究 tab 是受控实验，不是生产结论。数字来自 API fixture 与已记录协议，保证 UI 与后端一致。

| 方向 | 当前发现 | 查看位置 |
|---|---|---|
| axiom layer vs raw RAG | 在注册矩阵里，语义地基让输入 token 约减少 61%，同时代理任务质量不下降 | `GET /api/axiomgain/logistics_demo/protocol`, [docs/RESEARCH_axiom_gain.md](docs/RESEARCH_axiom_gain.md) |
| 跨源共指 | 当两个系统没有共享键时，raw retrieval 接近 0；确定性 resolver 输出后，合成任务变得可解 | `GET /api/split/ablation`, [docs/DESIGN_data_package.md](docs/DESIGN_data_package.md) |
| 模型能力趋势 | 模型越强，质量增益越小；token 节省在测试设置中主要来自结构 | [docs/PREREG_axiom_gain_frontier.md](docs/PREREG_axiom_gain_frontier.md), [docs/RESEARCH_axiom_gain.md](docs/RESEARCH_axiom_gain.md) |
| 负结果 | 学习式 alias dictionary 在 held-out F1 上没有增益，因此 build cost 不摊销 | [docs/RESEARCH_axiom_gain.md](docs/RESEARCH_axiom_gain.md) |
| nexus 校准 | 将合成边缘校准到真实数据波动后，部分 nexus 结果从显著变为判不定 | [docs/METRIC_nexus_reality.md](docs/METRIC_nexus_reality.md) |
| 可视化修复 | galaxy link 改为绝对显著阈值 + FDR 校正，不再使用相对 top-decile 点亮 | `GET /api/nexus_xdom/fdr_check`, [docs/METRIC_nexus_reality.md](docs/METRIC_nexus_reality.md) |

开放边界：合成跨域耦合的外部效度尚未闭合。任何现实世界发现都需要真实校准数据与独立验证协议。见 [docs/OBSERVER_NOTES.md](docs/OBSERVER_NOTES.md)。

### 架构

| 层 | 技术 | 职责 |
|---|---|---|
| 后端 | FastAPI, Python | 加载 spec、确定性合成数据、暴露 spec/data/timeline/graph/simulation/policy/compile/data-package/axiom API |
| 前端 | Vite, React, TypeScript | 读取 spec，从 `views` 生成 tab 和面板，并按 `semantic_type` 选择 widget |

后端不认识「管道」或「图书」这类领域词。`data_synth.py` 只根据 semantic type 和 spec 字段工作。把合成数据换成真实数据源时，目标是在同一 API 后面替换数据 adapter，而不是重写前端。

### 本地运行

```bash
# 后端，示例端口 8200
cd prism
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --port 8200

# 前端，另开终端
cd prism/frontend
npm install
npm run dev
```

前端默认连接 `http://127.0.0.1:8200`。如需其他后端地址，设置 `VITE_API_BASE`。

### Spec 与扩展点

v0 semantic types：

```text
identifier · category · status · metric · gauge · timeseries · text
```

新增 semantic type 通常需要两处改动：

1. 在 `frontend/src/widgets.tsx` 增加 widget 分支。
2. 在 `backend/app/data_synth.py` 增加确定性合成规则。

spec 格式见 [docs/SPEC_FORMAT.md](docs/SPEC_FORMAT.md)。

### 已实现模块

| 模块 | 概要 |
|---|---|
| 时间回放 | `temporal` spec 生成逐帧确定性数据，前端 slider 控制所有面板 |
| 本体图谱 | 实体实例与关系渲染为稳定图谱，节点详情复用 widget resolver |
| 预测仿真 | `POST /api/sim/{id}` 运行确定性 what-if 轨迹，带不确定带与阈值检查 |
| 策略对比 | `POST /api/policy/{id}` 用共享扰动序列比较 typed sequential policy |
| 人话策略编译 | `POST /api/compile/{id}` 可通过本地 OpenAI 兼容端点把自然语言翻译成 typed IR，再等待人工确认 |
| 跨源数据包 | `GET /api/datapackage...` 生成带 ground truth 的确定性多源数据包 |
| axiom-gain benchmark | `GET /api/axiomgain/{id}` 报告 raw context 与预联结 semantic context 的 fixture 对比 |

设计说明见 [docs/ROADMAP.md](docs/ROADMAP.md)、[docs/DESIGN_what_if_sequential.md](docs/DESIGN_what_if_sequential.md)、[docs/DESIGN_data_package.md](docs/DESIGN_data_package.md) 与 [docs/RESEARCH_axiom_gain.md](docs/RESEARCH_axiom_gain.md)。

### 复现与边界

- 确定性来自 sha256 派生 seed、无墙钟、以及 LLM benchmark 的冻结 fixture。
- 合成值会标注为 synthetic；仿真是决策支持示例，不是实测工况。
- 本地模型成本使用 token 数，不默认换算成金额；只有外部 API trace 明确引用时才使用费用数据。
- clean-room 范围：仓库只包含本项目代码，不导入私有或第三方产品代码库。
- 研究线关注受控合成跨源任务，不声称发现真实世界 nexus。

### 路线图

- [ ] 更多 semantic type：relation、geo、money、duration、enum distribution。
- [ ] SQL、CSV、REST 的真实数据 adapter。
- [ ] JSON Schema 校验与可视化 spec editor。
- [ ] 实体之间的关系下钻。
- [ ] 视图级 KPI header、过滤与排序。
- [ ] 通过 spec label 做 locale 切换。
- [ ] 更多密度与主题控制。
- [x] 后端确定性/边界测试，以及前端 widget snapshot 测试。
- [ ] 端到端浏览器测试。
- [ ] 鉴权与多租户 spec set。

## English

Prism turns a semantic spec into a complete domain cockpit. Tabs, panels, widgets, data synthesis, timeline replay, graph views, and decision-support labs are generated from the spec; the backend and frontend stay domain-agnostic.

The repository has two goals:

1. Show that a domain cockpit can be treated as `UI = f(spec)`.
2. Explore whether a deterministic semantic layer in front of an LLM can reduce context size and enable cross-source tasks under controlled synthetic conditions.

Unless otherwise noted, research results in this README are scoped to this repository's deterministic synthetic substrate.

### What It Looks Like

A spec describes entities, attributes, semantic types, views, relations, and temporal behavior. The same runtime renders different domains from different specs.

A 20-second tour: timeline scrubbing → zero-code domain switch (the theme re-refracts with the spec) → nexus galaxy alignment replay → the axiom-gain trend.

![20-second tour: timeline replay, zero-code domain switch, galaxy alignment replay, axiom-gain trend](docs/media/demo-highlights.gif)

![Prism cockpit generated from a spec](docs/media/readme_cockpit.png)

Prism also includes a cross-domain nexus lab. Two datasets are drawn as two record galaxies; only links passing evidence and significance checks are highlighted.

![Nexus galaxy with statistically gated links](docs/media/readme_nexus_galaxy.png)

The axiom-gain lab compares raw multi-source context with a pre-linked semantic substrate before the prompt is sent to a model.

![Axiom-gain trend and token reduction](docs/media/readme_axiom_gain.png)

Related repository: [prism-datagen](https://github.com/ForTe13X/prism-datagen), the standalone deterministic data-package generator extracted from this project.

### Core Idea

Traditional dashboards usually hard-code domain views in application code. Prism moves that structure into a declarative semantic spec:

```text
Semantic spec                 Domain-agnostic runtime              Result
────────────────────          ─────────────────────────            ─────────────────
entities + attributes   ->    backend reads semantic_type    ->    /spec and /data
views + relations             frontend renders views               generated cockpit
temporal behavior             widget resolver selects controls      UI = f(spec)
```

The repository includes two intentionally different domains:

- `backend/specs/infra_monitoring.json`: industrial infrastructure monitoring.
- `backend/specs/library_catalog.json`: library collection and branch activity.

Switch the domain in the UI and the same engine renders a different cockpit from a different spec.

### Research Labs

The research tabs are controlled experiments, not production claims. Numbers are loaded from API fixtures and documented protocols so the UI and backend stay in sync.

| Area | Current finding | Where to inspect |
|---|---|---|
| Axiom layer vs raw RAG | In the registered matrix, the semantic substrate reduces input tokens by about 61% while keeping quality non-decreasing on the measured proxy tasks | `GET /api/axiomgain/logistics_demo/protocol`, [docs/RESEARCH_axiom_gain.md](docs/RESEARCH_axiom_gain.md) |
| Cross-source coreference | When two systems have no shared key, raw retrieval scores near zero; deterministic resolver output makes the synthetic task solvable | `GET /api/split/ablation`, [docs/DESIGN_data_package.md](docs/DESIGN_data_package.md) |
| Model-capability trend | Quality gain shrinks as model capability rises, while token reduction remains mostly structural in the tested setup | [docs/PREREG_axiom_gain_frontier.md](docs/PREREG_axiom_gain_frontier.md), [docs/RESEARCH_axiom_gain.md](docs/RESEARCH_axiom_gain.md) |
| Negative result | A learned alias dictionary adds no held-out F1 in this setup, so its build cost does not amortize | [docs/RESEARCH_axiom_gain.md](docs/RESEARCH_axiom_gain.md) |
| Nexus calibration | Calibrating synthetic edges toward real-data variability makes some nexus results indeterminate instead of significant | [docs/METRIC_nexus_reality.md](docs/METRIC_nexus_reality.md) |
| Visualization fix | Galaxy links now use absolute significance thresholds with FDR correction instead of relative top-decile highlighting | `GET /api/nexus_xdom/fdr_check`, [docs/METRIC_nexus_reality.md](docs/METRIC_nexus_reality.md) |

Open boundary: the external validity of synthetic cross-domain coupling is not closed. Any real-world discovery claim needs real calibration data and a separate validation protocol. See [docs/OBSERVER_NOTES.md](docs/OBSERVER_NOTES.md).

### Architecture

| Layer | Stack | Responsibility |
|---|---|---|
| Backend | FastAPI, Python | Load specs, synthesize deterministic data, expose spec/data/timeline/graph/simulation/policy/compile/data-package/axiom APIs |
| Frontend | Vite, React, TypeScript | Fetch specs, generate tabs and panels from `views`, and resolve widgets from `semantic_type` |

The backend does not know domain words such as "pipeline" or "book". `data_synth.py` works from semantic types and spec fields. Replacing synthetic rows with a real source is intended to require a data adapter behind the same API rather than a frontend rewrite.

### Run Locally

```bash
cd prism
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --port 8200

cd prism/frontend
npm install
npm run dev
```

The frontend defaults to `http://127.0.0.1:8200`. Set `VITE_API_BASE` to use another backend URL.

### Spec And Extension Points

Semantic types in v0:

```text
identifier · category · status · metric · gauge · timeseries · text
```

Adding a new semantic type usually requires two changes:

1. Add a widget branch in `frontend/src/widgets.tsx`.
2. Add deterministic synthesis behavior in `backend/app/data_synth.py`.

Spec details are in [docs/SPEC_FORMAT.md](docs/SPEC_FORMAT.md).

### Implemented Modules

| Module | Summary |
|---|---|
| Timeline replay | `temporal` specs generate deterministic frame-by-frame data; the frontend slider replays all panels from the selected frame |
| Ontology graph | Entity instances and relations render as a stable graph; node details reuse the same widget resolver |
| Prediction simulation | `POST /api/sim/{id}` runs deterministic what-if trajectories with uncertainty bands and threshold checks |
| Policy comparison | `POST /api/policy/{id}` evaluates typed sequential policies with shared disturbance sequences and sensitivity checks |
| Natural-language policy compile | `POST /api/compile/{id}` can translate a user phrase into typed IR through a local OpenAI-compatible endpoint, then waits for human review before simulation |
| Cross-source data package | `GET /api/datapackage...` builds deterministic multi-source packages with embedded ground truth and reference solvers |
| Axiom-gain benchmark | `GET /api/axiomgain/{id}` reports fixture-backed comparisons between raw context and pre-linked semantic context |

Design notes are linked from [docs/ROADMAP.md](docs/ROADMAP.md), [docs/DESIGN_what_if_sequential.md](docs/DESIGN_what_if_sequential.md), [docs/DESIGN_data_package.md](docs/DESIGN_data_package.md), and [docs/RESEARCH_axiom_gain.md](docs/RESEARCH_axiom_gain.md).

### Reproducibility And Scope

- Determinism comes from sha256-derived seeds, no wall-clock time, and frozen fixtures for LLM benchmark runs.
- Synthetic values are labeled as synthetic; simulations are decision-support examples, not measured plant behavior.
- Local-model cost uses token counts, not dollar estimates, unless an external API trace is explicitly cited.
- Clean-room scope: this repository contains its own code and does not import private or third-party product codebases.
- The research line studies controlled synthetic cross-source tasks. It does not claim real-world nexus discovery.

### Roadmap

- [ ] More semantic types: relation, geo, money, duration, enum distribution.
- [ ] Real data adapters for SQL, CSV, and REST behind the current API.
- [ ] JSON Schema validation and a visual spec editor.
- [ ] Relation-driven drilldown between entities.
- [ ] View-level KPI headers, filters, and sorting.
- [ ] Locale switching through spec labels.
- [ ] Additional density and theme controls.
- [x] Backend determinism and boundary tests, plus frontend widget snapshot tests.
- [ ] End-to-end browser tests.
- [ ] Authentication and multi-tenant spec sets.
