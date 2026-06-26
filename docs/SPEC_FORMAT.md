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
  "entities": [ … ],                 // 实体(下文)
  "relations": [ … ],                // 实体间关系(v0 仅声明,下钻为 TODO)
  "views":    [ … ]                  // 视图 → 顶部 tab
}
```

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
v0 仅声明(用于将来下钻/关系图,见 README 的 TODO)。

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
