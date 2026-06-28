# Prism — 语义地基驱动的驾驶舱

> **一句话**:整个驾驶舱的界面(tab、面板、控件)是一份**语义地基 spec** 的**纯函数**。换一份 spec,
> 零代码就换一套完整的领域驾驶舱。Prism 后端与前端都**领域无关**——领域知识只活在 spec 里。

这是一个全新的、独立的原创项目(与任何既有项目无代码关系)。代号 **Prism**:一份 spec 经"棱镜"折射成一整套 UI。

## 核心理念

传统驾驶舱把"有哪些 tab、每个面板长什么样、用什么控件"**硬编码**在代码里,换领域=重写前端。
Prism 把这些**全部上移到声明式的语义地基**:

```
spec(语义地基)          运行时(领域无关)              结果
─────────────────       ─────────────────────        ──────────────────
entities + attributes →  后端按 semantic_type 合成数据  →  /spec + /data
  (每个属性带            前端按 view 生成 tab/面板          ↓
   semantic_type)       widget resolver 按 semantic_type   一整套驾驶舱
views + relations        选控件(仪表/趋势/徽章/…)        (UI = f(spec))
```

仓库自带**两个对比鲜明的领域**,跑的是**同一套引擎**,只差一份 spec:
- `backend/specs/infra_monitoring.json` — 工业管网监控(站点/传感器、压力仪表、H₂S 趋势)。
- `backend/specs/library_catalog.json` — 图书馆藏(藏书/分馆、评分、借阅趋势、上座率)。

在 UI 右上角「领域」下拉切换,即可看到**零代码**换出完全不同的驾驶舱——这就是"领域无关"的证明。

## 全景 · 给架构师 / PM 的诚实框定

**定位(诚实在先):Prism 是一个 for-fun / 学习沙盒**——成功判据是「还在玩、还在学吗?」,**不是** PMF / 简历 / 产品指标。但它**拒绝撒谎**:每个数字随结论挂诚实 caveat,负结果和胜利一样大声报。下面是架构师 / PM 30 秒能读完的账本。

**它由两半组成:**
1. **领域无关语义驾驶舱** —— 整个 UI(tab / 面板 / 控件)是一份**语义 spec 的纯函数**;换 spec 零代码换一套驾驶舱(见上)。数据**确定性合成**(哈希种子、无随机 / 无时钟、逐帧可复现)。
2. **一条诚实的研究线** —— 命题:在 LLM 前置一层**确定性语义地基**(跨源实体解析 + 预联结,规则式、build 成本 ≈ 0),能否同质量省 token、并解锁裸 RAG 做不了的跨源任务?驾驶舱里两个 lab tab(**⚖ axiom-gain** / **✦ 跨域 nexus**)各带「📋 架构 / PM 摘要」子标签,把下面的账本**活在界面里**(数字从 API 实时取,不会和后端漂移)。

**研究结果账本(稳 / 负 / 修 / 开):**

| 类别 | 结论 | 复现 |
| --- | --- | --- |
| **稳(CI 牢)** | 结构地基对裸 RAG:**输入 token 省 ~61%**(跨 3 模型 × 4 脏度 × 8 seed、每格 bootstrap 95% CI **12/12 显著**);质量不降(min ΔF1 +0.07,8/12 格显著更高);成本 × 质量 Pareto 前沿**由 axiom 独占** | `GET /api/axiomgain/logistics_demo/protocol` · [RESEARCH §11c](docs/RESEARCH_axiom_gain.md) |
| **稳(使能)** | 跨域共指:同一实体在两系统经变体改写、无共享键 ⇒ 裸 RAG 得分 **≈0**(认不出),确定性 resolver 预解析后 **→0.66**、token 省 ~85% —— **从 0 到能做** | `GET /api/split/ablation` · [DESIGN §11b](docs/DESIGN_data_package.md) |
| **诚实负** | 学习式别名词典 **+0.000** held-out F1 ⇒ 摊销**永不回本(N\*=∞)**——增益全在「免 build 的结构」,**别为学词典单独投训练** | [RESEARCH §11b](docs/RESEARCH_axiom_gain.md) |
| **决定性诚实负** | 把合成 substrate 的可观测边缘**校准到真实数据**(变异系数 ~14× 高于手设)后,nexus 三渠道收敛**塌回判不定**——之前的胜利部分靠「数据太干净」 | `GET /api/nexus_xdom/calibrate` · [METRIC §8g](docs/METRIC_nexus_reality.md) |
| **已修诚实漏洞** | 星系「发光 = 已验证」原用相对 top-decile,**无关域对**也强行点亮 ~7;换成**绝对显著阈 + FDR(CACE)**后(同构造)**熄灭 7.17→0.03**、真桥精度 0.66→0.96。rewire 控制(同观测乱标签)新规则下不熄=AUC 失效(§8e),非 extinction——两控制测两失效 | `GET /api/nexus_xdom/fdr_check` · [METRIC §8h](docs/METRIC_nexus_reality.md) |
| **开放(不声称已补)** | substrate 的**外部效度**未闭合(跨域耦合是构造的设计潜变量);任何「野外跨域发现」须自带真实校准 | [OBSERVER §11/§12](docs/OBSERVER_NOTES.md) |

**焊死的纪律(贯穿全仓):**
- **确定性** —— sha256 种子,无 `random` / 无时钟,逐字节可复现;LLM 调用走**冻结 fixture**,跑分不碰 live 模型。
- **clean-room** —— 只用本仓自有代码;无任何既有项目 / 雇主 IP。
- **诚实是方向盘,不是叠甲** —— synthetic / 未实测的值永远标注;sim 永远带不确定带;判不定就报判不定(不四舍五入成显著);连可视化的**亮度都随置信度走**(零信号就熄灭,不只随点估大小)。

**边界(随结论挂):小规模 + 合成数据**(非生产证据);本地模型 $=0 ⇒ 成本轴仅真实 token、未折美元;研究线测的是「结构地基在**受控合成**跨源上的价值」,**不是**「野外能发现真 nexus」。研究方法学锚:[`METRIC_nexus_reality.md`](docs/METRIC_nexus_reality.md) · [`RESEARCH_axiom_gain.md`](docs/RESEARCH_axiom_gain.md) · 旁观诚实审计:[`OBSERVER_NOTES.md`](docs/OBSERVER_NOTES.md)。

## 架构

| 层 | 技术 | 职责 |
| --- | --- | --- |
| 后端 | **FastAPI (Python)** | 读 spec(`specs_loader`)+ 按 `semantic_type` **确定性合成**数据(`data_synth`,哈希种子、无随机);暴露 `/api/specs` `/api/spec/{id}` `/api/data/{id}/{entity}?frame=N` `/api/timeline/{id}` `/api/graph/{id}?frame=N` · `POST /api/sim/{id}`(轨迹仿真,`simulation`)· `POST /api/policy/{id}`(策略对比,`policy`)· `POST /api/compile/{id}` + `GET /api/llm/health`(LLM 编译,`llm_client`)· `GET /api/datapackage[/{id}[/discriminability]]`(跨源数据包,`data_package`)· `GET /api/axiomgain/{id}`(axiom-gain ablation,`benchmark`)· `GET /api/parse/{id}`(异构解析器,`parser`)· `GET /api/calibration`(逆向机制校准,`calibration`) |
| 前端 | **Vite + React + TypeScript** | 取 spec → 由 `views` 生成 tab、由实体 `attributes` 生成面板、由 **widget resolver**(`widgets.tsx`)按 `semantic_type` 选控件 |

> 后端不认识"管道"或"图书";`data_synth.py` 只认 `semantic_type`。把合成数据换成真实数据源,只需替换
> `synth_entity_rows` 一个函数,API 与前端**一行不改**。

## 跑起来

```bash
# 后端(任一可用端口,示例 8200)
cd prism
python -m venv .venv && .venv\Scripts\activate         # *nix: source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --port 8200

# 前端(另开一个终端)
cd prism/frontend
npm install
npm run dev            # http://127.0.0.1:5173
```

前端默认连后端 `http://127.0.0.1:8200`;改端口设 `VITE_API_BASE`。

## 语义类型(v0)

`identifier · category · status · metric · gauge · timeseries · text` —— 详见 [`docs/SPEC_FORMAT.md`](docs/SPEC_FORMAT.md)。
**加一个新 semantic_type** = 在 `widgets.tsx` 的 resolver 里加一个分支 + 在 `data_synth.py` 里加合成规则,**仅此两处**。

## 时间帧与回放(P1)

数据不再是单一快照:spec 顶层声明 `temporal: {frames, now, step}`,属性加 `evolves: true`(可选 `drift`)即随帧演化。
- 后端:`GET /api/data/{id}/{entity}?frame=N` 按帧**确定性**合成(哈希种子并入 `frame`,无随机/时钟,逐帧可复现);`GET /api/timeline/{id}` 回放轴。**未声明 `evolves` 的属性逐帧字节不变**(身份/分类不动)。
- 前端:驾驶舱顶部一条 **replay slider**(拖动选帧 + 播放/暂停),所有控件按当前帧取数,timeseries 显示"截至该帧"的滑动窗口。
- 领域无关:演化规则只在 spec(`evolves`/`drift`)+ `data_synth.py`,绝不针对任何领域。详见 [`docs/SPEC_FORMAT.md`](docs/SPEC_FORMAT.md) 的 `temporal` / `evolves` 两节与 [`docs/ROADMAP.md`](docs/ROADMAP.md) P1。

## 本体图谱画布(P2)

驾驶舱多了一个 **🕸 本体图谱** tab:把 spec 的实体/关系画成实例图谱。
- 后端 `GET /api/graph/{id}?frame=N`:节点=各实体在该帧的实例(行),边=由 `relations` 生成的**确定性实例映射**(每个 `from` 实例连到一个 `to` 实例)。
- 前端:SVG 分层布局(每个实体类型一列),节点按该帧 `status` 上色,**复用 P1 的 slider 逐帧重放**(拖动只重上色、不重排——拓扑跨帧稳定);点节点 → 右侧详情**复用同一套 widget resolver**。
- 领域无关:图纯由 spec 的 `entities`/`relations` 生成,布局通用,零领域假设。详见 [`docs/ROADMAP.md`](docs/ROADMAP.md) P2。

## 预测·仿真(P3)

驾驶舱再多一个 **🔮 预测·仿真** tab:把 slider 从"回放过去"延伸到"模拟未来"。
- 后端 `POST /api/sim/{id}`(`backend/app/simulation.py`):对一个数值属性外推 `horizon` 帧,给出**基线 + N 个 what-if 情景**轨迹,每条带**不确定带**(min/中位/max,多次确定性 roll)、越限帧、以及一个 `verdict`(优先避免越限,否则终值最低)。动力学(均值回复 `rate`/`trend`/`volatility`)与阈值取自 spec 的 [`dynamics`](docs/SPEC_FORMAT.md)。
- 前端:SVG 扇形带图(基线 + 情景对比、阈值线、越限标记)+ what-if 编辑器(设定点 `shift` / 脉冲 `pulse`)+ 判定横幅;**诚实标注**"确定性合成示意 · 非实测"。
- 引擎**自包含、确定性**(不 import `data_synth`,无随机/时钟);接 live 状态只需给 `simulate(baseline=…)`。详见 [`docs/ROADMAP.md`](docs/ROADMAP.md) P3 与 [`docs/OBSERVER_NOTES.md`](docs/OBSERVER_NOTES.md)。

## 策略对比 · 序贯 what-if(P3.5)

再多一个 **🧭 策略对比** tab:把"单发 what-if"升级成"**比几条候选打法**"——这是决策支持的核心(参考,不替你拍板)。
- 后端 `POST /api/policy/{id}`(`backend/app/policy.py`):每条**策略 = 一份有类型的 IR**(`当 目标量 op 阈值 → 调设定点 shift / 脉冲 pulse`)。引擎做**闭环序贯 rollout**(规则观察当前值、命中即 latch),各策略**共用同一扰动序列(公共随机数)**公平对比,按**鲁棒性**(越限率 / 最坏终值)排名;再跑一遍**敏感性**(更严苛假设下排名是否翻)。
- 前端:候选策略编辑器(规则:when→do)+ 对比图(基线 vs 各策略带)+ 鲁棒性表 + 判定 + **敏感性横幅**(承重诚实:结论吊在假设上)。
- **诚实纪律**:数字只来自确定性引擎(**LLM 不编数**);全程标"确定性合成示意 · 非实测"。typed IR 是为 P6 的"人话→IR 编译 + 人确认"预留的契约。详见 [`docs/DESIGN_what_if_sequential.md`](docs/DESIGN_what_if_sequential.md)。

## 人话→策略 · LLM 编译 + 人确认(P6 模式)

把"人话打法"用**本地 LLM**编译成上面的 typed IR —— 这是 roadmap P6"生成 + 用户确认"模式的落地。
- 后端 `POST /api/compile/{id}`(`backend/app/llm_client.py`):对 **OpenAI 兼容端点**(默认 LM Studio `127.0.0.1:1234`,`PRISM_LLM_BASE`/`PRISM_LLM_MODEL` 可配)发**结构化输出**(`json_schema`)请求,把自然语言编译成规则 IR。**LLM 只翻译,绝不产生数字**;返回的 IR 经严格校验(非法 op/动作丢弃、`by` 钳位)。
- **人确认闸**:编译出的 IR 落进策略编辑器成一张**可改的候选策略卡**——你审/改/删后,再交**确定性引擎**跑对比。**绝不自动执行**。
- **诚实**:失败**可观测**(`GET /api/llm/health` 出可达性 + 失败计数 + 原因),**绝不静默用模板假装真实输出**;LLM 不可达时退回手填规则。
- **小模型可用**正因为 IR 是**窄 schema**:`qwen3-8b` / `gemma-12b-qat` 配结构化输出即可稳定填表。详见 [`docs/DESIGN_what_if_sequential.md`](docs/DESIGN_what_if_sequential.md) §1/§3/§6。

## 跨源数据包 · axiom-gain 基底(DP1)

一条新主线的地基:一份**确定性、clean-room、spec 驱动**的异构数据包生成器,为"语义/公理层是否真比裸 RAG 强"的基准([`docs/RESEARCH_axiom_gain.md`](docs/RESEARCH_axiom_gain.md))供题。
- 后端 `backend/app/data_package.py` + `GET /api/datapackage[/{id}[/discriminability]]`:读一份 `data_source` spec,**先建 ground-truth『源事件 → 指标异常 → 受影响记录』,再让 SQL + 时序 + 新闻三源与真值一致**;SQL 可落成真 SQLite。生成器**领域无关(spec 驱动)**:跨源因果模式是引擎,领域字符串全进 spec 的 `vocab`/`roles`——**加领域=加一份 spec,零生成器代码**。自带两个域:`logistics_demo`(运单/吞吐量)与 `energy_demo`(变电站/负荷,通用能源),**跨域判别力成立**(两域 L1 naive=1.0、L≥2 naive=0、linked 仍复原大部分;唯 energy 纯时间型 L4 因基础 linked 无互斥性而偏弱 ≈0.33——诚实下限,留给后续 LLM/axiom 层)。
- **两个旋钮(只动观测、留真值)**:`link_explicitness`(1 字面 id → 5 纯语义)与 `dirtiness`(别名/单位/缺失/时移/数值/乱码,记 `corruption_map`)。
- **判别力骨架**:`naive`(字面单源)/ `linked`(跨源时空+实体联结)/ `oracle`(知真值)三解题器——link≥2 时 naive 失效、linked 仍可复原(任务确需跨源);脏度↑ linked 退化(鲁棒性曲线)。这是 axiom-gain ablation 的**确定性骨架**。详见 [`docs/DESIGN_data_package.md`](docs/DESIGN_data_package.md)。

## axiom-gain ablation · 本地 LLM(DP2)

把上面的骨架接上真 LLM:**naive-RAG(原始多源)vs axiom-RAG(canonical 解析 + 预联结事实)**,同模型同 prompt 只换上下文。
- 后端 `backend/app/axiom_layer.py`(clean-room 异常锚定 canonical 解析)+ `benchmark.py`(token 插桩 + **冻结 fixture** 可复现)+ `GET /api/axiomgain/{id}`(从 fixture 出报告,无需 live 模型)。
- **首跑结果**(4 held-out seeds × {qwen3-8b, gemma-12b} × {dirt 0,0.6}):**axiom-RAG 质量≥naive 且输入 token≈40%**;**增益随脏度增长**(gemma 在 dirt0.6:naive 0.53 → axiom 0.87)。即 RESEARCH 的 H1 + §6b robustness 在首跑成立。
- **诚实**:axiom 层算法式(无训练 ⇒ build≈0、摊销平凡);小规模首跑(无多 seed CI / $ 定价 / 多场景);naive 给真原始多源(非稻草人)。完整研究见 [`docs/RESEARCH_axiom_gain.md`](docs/RESEARCH_axiom_gain.md) §11。
- **此后已升级为完整结果**(见顶部「研究结果账本」):**跨模型矩阵 + 每格 95% CI**(`/api/axiomgain/{id}/protocol`,token 省 ~61%、12/12 显著、Pareto 独占、学习字典 N\*=∞)· split-substrate **跨域共指使能**(`/api/split/ablation`,裸 RAG ≈0 → resolver 后 0.66)· real-data 校准的**决定性诚实塌缩**(Track 1,METRIC §8g)· §13 发光 **CACE/FDR** 修复(零耦合对熄灭,METRIC §8h)。全部活在驾驶舱 **⚖ axiom-gain** / **✦ 跨域 nexus** 两个 lab tab 的「📋 架构 / PM 摘要」子标签里(数字实时取自 API)。

## 预留 TODO(v0 之后)

- [ ] 更多控件/语义类型:`relation`(画实体关系图)、`geo`(地图)、`money`、`duration`、`enum-distribution`(饼图)。
- [ ] 真实数据源适配器(替换 `synth_entity_rows`):SQL / CSV / REST,按 spec 映射。
- [ ] spec 的 JSON Schema 校验 + 编辑器(可视化拼 spec → 即时预览)。
- [ ] 关系驱动的下钻(点一行 → 沿 `relations` 跳到关联实体)。
- [ ] 视图级聚合/指标卡(KPI header)与过滤/排序。
- [ ] 多语言(spec 里已留 `label_en`/`title_en`,接一个 locale 切换)。
- [ ] 主题:深色模式 + 每领域 accent 已通;再加密度/字号档。
- [x] 测试:后端合成的确定性/边界/空安全(`backend/tests/`)+ 前端 resolver 快照与时间标签(`vitest`)。 e2e 待补。
- [ ] 鉴权 + 多租户(每租户一组 spec)。
