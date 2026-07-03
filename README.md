# Prism — 语义地基驱动的驾驶舱

[English](README_EN.md)

Prism 把一份语义 spec 变成完整的领域驾驶舱。tab、面板、控件、数据合成、时间回放、图谱视图和决策实验都由 spec 驱动；后端与前端本身保持领域无关。

这个仓库有两个目标：

1. 展示领域驾驶舱可以写成 `UI = f(spec)`。
2. 在受控合成数据上探索：LLM 前面加一层确定性的语义地基，能否减少上下文、并让跨源任务变得可解。

除非另有说明，README 中提到的研究结果都只适用于本仓的确定性合成 substrate。

## 界面示例

spec 描述实体、属性、semantic type、视图、关系与时间行为。同一套 runtime 可以从不同 spec 渲染不同领域。

19 秒动图速览：时间帧回放 → 零代码切换领域（主题随 spec 变化）→ 星系对齐回放 → axiom-gain 趋势。

![19 秒速览:时间回放、零代码换域、星系对齐回放、axiom-gain 趋势](docs/media/demo-highlights.gif)

![Prism 主驾驶舱:界面由 spec 折射而来](docs/media/readme_cockpit.png)

Prism 也包含跨域 nexus 实验。两个数据域被画成两组记录星系；只有通过证据与显著性检查的链接才会点亮。

![星系相撞:两个数据域,只有过检验的桥才发光](docs/media/readme_nexus_galaxy.png)

axiom-gain 实验比较两种上下文：原始多源数据 vs 预联结后的语义地基。

![axiom-gain 剪刀叉:能力越强增益越小,token 省是结构性的](docs/media/readme_axiom_gain.png)

相关仓库：[prism-datagen](https://github.com/ForTe13X/prism-datagen)，从本项目抽出的独立确定性数据包生成器。

## 核心理念

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

## 研究实验

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

## 架构

| 层 | 技术 | 职责 |
|---|---|---|
| 后端 | FastAPI, Python | 加载 spec、确定性合成数据、暴露 spec/data/timeline/graph/simulation/policy/compile/data-package/axiom API |
| 前端 | Vite, React, TypeScript | 读取 spec，从 `views` 生成 tab 和面板，并按 `semantic_type` 选择 widget |

后端不认识「管道」或「图书」这类领域词。`data_synth.py` 只根据 semantic type 和 spec 字段工作。把合成数据换成真实数据源时，目标是在同一 API 后面替换数据 adapter，而不是重写前端。

## 本地运行

```bash
# 后端，示例端口 8200
cd prism
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --port 8200

# 前端，另开终端
cd prism/frontend
npm install
npm run dev
```

前端默认连接 `http://127.0.0.1:8200`。如需其他后端地址，设置 `VITE_API_BASE`。

## Spec 与扩展点

v0 semantic types：

```text
identifier · category · status · metric · gauge · timeseries · text
```

新增 semantic type 通常需要两处改动：

1. 在 `frontend/src/widgets.tsx` 增加 widget 分支。
2. 在 `backend/app/data_synth.py` 增加确定性合成规则。

spec 格式见 [docs/SPEC_FORMAT.md](docs/SPEC_FORMAT.md)。

## 已实现模块

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

## 复现与边界

- 确定性来自 sha256 派生 seed、无墙钟、以及 LLM benchmark 的冻结 fixture。
- 合成值会标注为 synthetic；仿真是决策支持示例，不是实测工况。
- 本地模型成本使用 token 数，不默认换算成金额；只有外部 API trace 明确引用时才使用费用数据。
- clean-room 范围：仓库只包含本项目代码，不导入私有或第三方产品代码库。
- 研究线关注受控合成跨源任务，不声称发现真实世界 nexus。

## 路线图

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
