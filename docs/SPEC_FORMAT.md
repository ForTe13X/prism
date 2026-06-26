# 语义地基 Spec 格式 (v0)

一份 spec 就是一个领域的"语义地基",也是整个驾驶舱的唯一来源。位于 `backend/specs/<id>.json`。

## 顶层结构

```jsonc
{
  "id": "infra_monitoring",          // 唯一 id,须等于文件名(无扩展名);仅 [a-z0-9_]
  "title": "管网监控驾驶舱",          // 领域标题(中文)
  "title_en": "Pipeline Monitoring", // 可选英文
  "version": "0.1.0",
  "accent": "#2f7d9a",               // 该领域的主题色(前端整体 accent)
  "description": "…",                // 一句话说明(显示在 banner)
  "temporal": { "frames": 48, "now": 36, "step": "hour" },  // 可选;时间帧轴(P1,下文)
  "entities": [ … ],                 // 实体(下文)
  "relations": [ … ],                // 实体间关系(v0 仅声明,下钻为 TODO)
  "views":    [ … ]                  // 视图 → 顶部 tab
}
```

## temporal —— 时间帧轴(P1,可选)

声明这份 spec 的**回放时间轴**。前端据此画顶部的 replay slider;后端 `GET /api/data/...?frame=N`
按帧确定性合成,`GET /api/timeline/{id}` 回这三个字段。

```jsonc
{ "frames": 48, "now": 36, "step": "hour" }
```
- `frames`:总帧数(slider 范围 `0 … frames-1`)。
- `now`:默认停靠帧(不带 `?frame=` 时返回这一帧;slider 上标一个「现在」刻度)。
- `step`:每帧的时间粒度(`hour`/`day`/`minute`/`week`/…),只用于**通用**时间标签格式化,不含领域语义。

**不写 `temporal`** ⇒ 该领域只有单帧(`frames:1`),前端不显示 slider。演化由属性的 `evolves` 决定(下文)。

## entities[]

```jsonc
{
  "type": "station",        // 实体类型 id(唯一)
  "label": "站点",
  "label_en": "Station",
  "icon": "🏭",             // 卡片图标
  "count": 8,                // 合成多少行(确定性)
  "attributes": [ … ]        // 属性(下文)
}
```

## attributes[] —— 核心:每个属性带一个 `semantic_type`

`semantic_type` 决定**后端怎么合成值** + **前端用什么控件渲染**。这是整套系统的枢纽。

| semantic_type | 含义 | 额外字段 | 后端合成 | 前端控件 |
| --- | --- | --- | --- | --- |
| `identifier` | 实体显示名/编号 | `prefix` | `<prefix>-001` 递增 | 加粗标题 |
| `category` | 离散分类 | `values[]` | 从 values 哈希取一个 | 圆角 pill |
| `status` | 状态(有好坏语义) | `values[]` | 从 values 哈希取一个 | 彩色徽章(good/warn/bad 按值名约定上色) |
| `metric` | 数值指标 | `unit`, `range[min,max]` | range 内确定性取值 | 数字 + 单位 |
| `gauge` | 带阈值的量 | `unit`, `range`, `threshold{warn,limit}` | range 内取值 | 进度条 + 阈值刻度(**阈值为上界**,达到=更差) |
| `timeseries` | 时间序列 | `unit`, `range`, `points`(默认24), `threshold{limit}` | 确定性正弦+抖动序列 | 内联 SVG 折线(超 limit 标红 + 虚线) |
| `text` | 自由文本 | — | 从内置短语取一个 | 灰字 |

### evolves / drift —— 属性怎样随帧演化(P1,领域无关)

任何属性都可加这两个字段,声明它在时间轴上**怎么变**:

| 字段 | 含义 | 默认 |
| --- | --- | --- |
| `evolves` | `true` ⇒ 该属性随 `frame` 演化;**不写 ⇒ 逐帧不变**(身份/分类常这样) | `false` |
| `drift` | 漂移幅度 ∈ [0,1],占该值"跨度"的比例(数值=range 跨度;离散=值表长度)。越大摆动越猛 | 数值类 `0.3`;`status`/`category` `0.8`;`text` `1.0` |

- 演化是**确定性**的:值绕它的 frame-0 基线,被一条 `(seed, frame)` 哈希出来的平滑信号 `_wiggle` 拉动 —— 无随机、无时钟,同 `frame` 同值,可逐字节复现。
- `identifier` **永不演化**(行的名字跨帧恒定),即使写了 `evolves` 也忽略。
- `timeseries` 把 `evolves` 当作"**窗口随帧滑动**"(展示截至当前帧的 `points` 点窗口);不演化则停在 v0 的 `[0…points-1]` 窗口。
- **未声明 `evolves` 的属性 = v0 的值,逐帧字节一致** —— 这是回放一致性的命门。

> 演化规则只活在 spec(`evolves`/`drift`)+ `data_synth.py`,**绝不针对任何领域**。

### dynamics —— 仿真动力学(P3,可选)

数值属性(`metric`/`gauge`/`timeseries`)可声明 `dynamics`,供轨迹仿真 `POST /api/sim/{id}` 外推未来帧:

```jsonc
"dynamics": { "model": "mean_revert", "rate": 0.25, "trend": 0.015, "volatility": 0.08 }
```
| 字段 | 含义 | 默认 |
| --- | --- | --- |
| `model` | 动力学模型,目前仅 `mean_revert`(均值回复) | `mean_revert` |
| `rate` | 回复强度 ∈ [0,1](越大越快拉回设定点) | `0.15` |
| `trend` | 每帧漂移,占 `range` 跨度的比例 | `0` |
| `volatility` | 每帧冲击幅度,占跨度比例(**确定性 hash,非真随机**) | `0.12` |

- 全部可缺省(引擎有默认值);未声明 `dynamics` 的数值属性照样能仿真。
- 仿真**永远带不确定带**(min/中位/max,多次确定性 roll)且**诚实标注**为合成示意(非实测)。
- 领域无关:动力学只活在 spec + 仿真引擎(`backend/app/simulation.py`),不针对任何领域。详见 [`docs/ROADMAP.md`](ROADMAP.md) P3。

### status 上色约定(领域无关)
值名(小写)落入约定集合即上色,否则中性:
- **good**(绿):`normal/ok/available/open/healthy/online/good`
- **warn**(琥珀):`warning/degraded/busy/on_loan/pending/elevated`
- **bad**(红):`critical/fault/overdue/closed/error/offline/down`

> 想支持新状态词?加进 `frontend/src/widgets.tsx` 的 `GOOD/WARN/BAD` 集合即可。

## relations[]

```jsonc
{ "from": "sensor", "predicate": "installed_at", "to": "station" }
```
**P2 起,relations 驱动本体图谱**:每条关系生成确定性的**实例边** —— 每个 `from` 实例按 `hash(spec, predicate, from_id)` 连到一个 `to` 实例。节点=实体实例(按该帧 `status` 上色),边=这些实例映射。拓扑跨帧稳定(`installed_at` 属身份),拖 slider 只重上色。见 `GET /api/graph/{id}?frame=N` 与 [`docs/ROADMAP.md`](ROADMAP.md) P2。

## views[] —— 决定顶部有哪些 tab

```jsonc
{ "id": "stations", "title": "站点总览", "entity": "station", "layout": "cards" }
```
- `entity`:这个 tab 展示哪个实体类型的数据。
- `layout`:`cards`(卡片网格)或 `table`(表格)。两种布局都用同一个 widget resolver 渲染单元格。

## 加一个新领域 = 加一份 spec

1. 复制一份 `backend/specs/<新id>.json`,改 `id`/实体/属性/视图。
2. 后端**无须改动**(自动出现在 `/api/specs`)。
3. 前端**无须改动**——若用到了**新的 semantic_type**,才需在 `widgets.tsx` + `data_synth.py` 各加一处。

这就是"界面是 spec 的纯函数"的实操含义。
