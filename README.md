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

## 架构

| 层 | 技术 | 职责 |
| --- | --- | --- |
| 后端 | **FastAPI (Python)** | 读 spec(`specs_loader`)+ 按 `semantic_type` **确定性合成**数据(`data_synth`,哈希种子、无随机);暴露 `/api/specs` `/api/spec/{id}` `/api/data/{id}/{entity}?frame=N` `/api/timeline/{id}` |
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
