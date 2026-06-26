# 设计笔记 · 异构数据包(spec 驱动生成器 + clean-room 解析器)

> **状态:方向锚(design note),非已建成、非指令。** 旁观会话整理,供在建会话取舍。
> 关联:[`RESEARCH_axiom_gain.md`](RESEARCH_axiom_gain.md)(本数据包是其基准基底)· [`SPEC_FORMAT.md`](SPEC_FORMAT.md) · [`OBSERVER_NOTES.md`](OBSERVER_NOTES.md)。

## 0. 命题
要一份**异构、跨源**的数据包(时序 / SQL / NoSQL / 文档 / 新闻),让 axiom-net / 语义地基有地方**赢裸 RAG**(跨源任务才照得出它的价值),同时当 [`RESEARCH_axiom_gain`](RESEARCH_axiom_gain.md) 的基准基底。做法:**别去爬一摊,把数据包本身做成 spec 驱动的生成器**——加场景 = 加一份 spec,廉价、可复现、零法律风险,与 Prism 一脉相承。

## 1. 两条焊死的纪律(不可协商)
1. **Clean-room:Prism 只含自有代码。** 不引入 SPI(前东家 IP)的代码/资产——含其 agentic parser。需要同类能力就**重写**(技能可带走,代码不带)。引一行外部 IP 进来 = 毁掉 Prism 的 clean-room 身份。
2. **数据合规:合成为主 + 开放许可真数据。** 不工程化绕过 ToS / 版权 / 反爬;爬取仅限**明确开放许可**的源,且尊重 `robots.txt` / 速率限制 / 署名要求。对**研究基准**而言这不是妥协——合成可复现、答案已知、零尾巴,本就更优(见 §4)。

## 2. spec 驱动的异构生成器(核心)
一份 `data_source` spec 声明实体 / 关系 / 各模态源 / **预埋跨源链** / 配套任务,生成器吐出多存储的一致数据集 + ground-truth:

```jsonc
{
  "id": "logistics_demo",
  "stores": {
    "sql":   { "tables": ["shipment", "carrier", "warehouse"] },       // → SQLite
    "nosql": { "collections": ["inventory_doc"] },                      // → JSON 文档
    "timeseries": { "streams": ["gps_temp", "throughput"], "frames": 240 },
    "docs":  { "kinds": ["bill_of_lading_pdf", "inspection_report"] },  // → 合成 PDF/表/图
    "news":  { "feed": "port_weather", "events": 60 }                   // → 文本+时间戳
  },
  "ground_truth": [                                                     // 预埋的跨源因果/关联(=已知答案)
    { "news_event": "台风封港 #12", "causes": { "stream": "throughput", "anomaly_at": 132 },
      "linked_sql": { "table": "shipment", "where": "status='delayed'" } }
  ],
  "tasks": [ { "q": "哪批延误能由哪条新闻事件解释?", "answer_ref": 0, "needs": ["news","sql","timeseries"] } ]
}
```
- 加一个场景 = 加一份 `data_source` spec。确定性生成(沿用 `_wiggle` 等),逐字节可复现。

## 3. 模态 → 存储映射
| 模态 | 落成 | 复用 |
|---|---|---|
| 时序 | SQLite 表 / parquet | 现有确定性 `_wiggle` 引擎 |
| 关系 SQL | SQLite(可移植) | — |
| NoSQL / 文档 | JSON 文档集 | — |
| 多模态文档 | 合成 PDF / 表 / 图(SVG→PDF) | 给解析器练手的"脏"输入 |
| 新闻 / 文本 | 文本语料 + 时间戳 | **预埋**与时序/SQL 的关联事件 |

## 4. 为什么"预埋 ground-truth"让合成**更适合**基准
- 你**知道**新闻↔时序↔SQL 的真实关联 → 任务有**已知答案** → 能干净打分;
- 你**知道** axiom 该不该帮上忙 → 能验证增益归因;
- 全程可复现、零许可纠纷。**真爬数据的 ground-truth 是未知/含糊的,基准噪声大。** 真数据留给"真实感 demo",不进精度基准。

## 5. agentic 解析器(clean-room **重写**,不 lift SPI)
建一个**属于 Prism 的** agentic 解析器,把异构原始(PDF / HTML / CSV / JSON)解析成结构化行/实体。指向:**(a) §2 合成的多模态文档**(主)+ **(b) §6 开放许可真数据**(少量,练真实脏数据)。
- 职责:抽取 + 归一 + **provenance** + 置信 + **失败可观测**(照搬 SPI 的**诚实纪律**——纪律是 skill,可带;代码不带)。
- 它也是 axiom-net 的天然上游:解析出的实体/关系喂本体/公理层。

## 6. 开放许可真数据来源(若掺真数据,只走这些)
| 源 | 许可 | 用途 |
|---|---|---|
| Wikidata / Wikipedia | CC-BY-SA | 本体 / 实体 / 关系(绝配) |
| CC-News(Common Crawl, HF) | CC | 新闻文本语料 |
| GDELT | 开放 | 新闻**事件**(元数据/链接,非正文) |
| Wikinews | CC-BY | 新闻正文(可用) |
| 各国 open-data 门户 | 公共 | 时序 / 统计 |
| arXiv | 标注许可 | 文档 / PDF 解析 |
> 用前逐一核 license + 满足署名;**不碰版权正文的 ad-hoc 爬取**。

## 7. 场景清单(2–3 个起步,各跨全模态、领域互异以证泛化)
1. **供应链/物流**:运单(SQL)+ 承运商单据(PDF)+ GPS/温控时序 + 港口/天气新闻 + 库存(NoSQL)。
2. **能源/公用**(通用、非 SPI):表计时序 + 资产台账(SQL)+ 检修报告(文档)+ 监管/市场新闻。
3. **零售/电商**:订单(SQL)+ 商品目录(NoSQL)+ 流量/销售时序 + 评论(文本)+ 趋势新闻。

## 8. 跨源任务集(= 基准的"题")
每题**必须跨源才能答**,且有**已知答案**(来自 §2 预埋)、且**held-out**(不在 axiom 训练上调过)。直接喂 [`RESEARCH_axiom_gain`](RESEARCH_axiom_gain.md) 的 with/without ablation。**这种题才照得出 axiom-net 对裸 RAG 的增益。**

## 9. 该停的纪律(防无底洞)
**一个场景全模态端到端先打通**(生成器 → 多存储 → 解析器 → 跨源任务 → axiom-gain 能跑),**再**铺第 2、3 个。生成式让复制廉价——但先证一条链能转,别先把五个场景铺满。

---
*—— 设计笔记。这是给在建会话的方向锚,不是指令;建造的人说了算。*
