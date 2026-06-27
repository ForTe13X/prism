# 设计笔记 · 异构数据包(spec 驱动生成器 + clean-room 解析器)

> **状态:方向锚(design note),非已建成、非指令。** 旁观会话整理,供在建会话取舍。
> 关联:[`RESEARCH_axiom_gain.md`](RESEARCH_axiom_gain.md)(本数据包是其基准基底)· [`SPEC_FORMAT.md`](SPEC_FORMAT.md) · [`OBSERVER_NOTES.md`](OBSERVER_NOTES.md)。

## 0. 命题
要一份**异构、跨源**的数据包(时序 / SQL / NoSQL / 文档 / 新闻),让 axiom-net / 语义地基有地方**赢裸 RAG**(跨源任务才照得出它的价值),同时当 [`RESEARCH_axiom_gain`](RESEARCH_axiom_gain.md) 的基准基底。做法:**别去爬一摊,把数据包本身做成 spec 驱动的生成器**——加场景 = 加一份 spec,廉价、可复现、零法律风险,与 Prism 一脉相承。

## 1. 两条焊死的纪律(不可协商)
1. **Clean-room:Prism 只含自有代码。** 不引入 SPI(前东家 IP)的代码/资产——含其 agentic parser。需要同类能力就**重写**(技能可带走,代码不带)。引一行外部 IP 进来 = 毁掉 Prism 的 clean-room 身份。
2. **数据合规:真实校准的合成 + 开放许可参照。** 真实数据**只作参照**,用于**校准**生成器的分布/相关/机制(见 §4b),且**只取聚合量**(矩/相关/结构)、参照本身走**开放许可**;不工程化绕过 ToS / 版权 / 反爬,爬取仅限明确开放许可源并尊重 `robots.txt` / 速率 / 署名。对**研究基准**这不是妥协——校准后的合成既**真实**(符合业务数理)又**干净**(可复现、答案已知、零尾巴)。

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
- 全程可复现、零许可纠纷。**真爬数据的 ground-truth 是未知/含糊的,基准噪声大。**

## 4b. 真实数据作为参照:逆向学出生成机制(校准)
纯凭空合成的软肋:**可复现 ≠ 真实**——分布/相关/因果若离谱,基准测的是个不存在的世界(外部效度为零)。解法:**用真实数据当参照,逆向学出"生成机制",再正向采样合成**(system identification / 逆推 DGP——是 [P3](RESEARCH_axiom_gain.md) forward 仿真的**逆**:从真实学参数,再 forward 生成)。
- **边缘 + 依赖**:各源拟合边缘分布,**copula** 抓跨源相关(让预埋的"新闻↔时序↔SQL"同现是**真实强度**,非任意);
- **因果**:从真实学**结构因果模型 / 因果图**,让 §2 预埋因果是**学来的**而非拍的;
- **动力学**:`dynamics` 的 `rate/vol` **从真实序列标定**,不手设。

两头通吃:**真实性**来自拟合真实数理逻辑,**干净**来自机制握在你手 → ground-truth 已知、可复现、输出零版权。

**风险 → 对策(信息,非指控):**
- 参照 license:拿版权数据"只拟合参数"在法律上仍是活问题 → 参照**走开放许可 + 只取聚合量**(不喂原始微观行)。
- 隐私 / 记忆化:拟合微观数据会泄漏个体、也让"校准合成"退化成"洗过的真数据" → **只拟合聚合层**(分布/相关/结构)。
- 过拟合参照:贴死一份样本则失泛化、把"不可复现"请回来 → 拟合**简约机制**,生成仍参数化 + seeded。
- **"真实"要验证非声称**:拿**没拟合过的矩 / 相关**做 held-out 检验,合成对得上才算像。

> 真数据仍可留一薄层进"真实感 demo";但**精度基准**用的是**校准后的合成**(realistic + 干净 + 已知答案)。

## 4c. 污浊化层:从脏里把真值捞回来(robustness / 给 axiom 引擎上强度)
干净基准只测 easy case;**axiom 引擎的核心价值就是对脏数据的鲁棒**(消歧 / 对账 / 补缺 / 纠错 = 数据治理痛点)。故加第三层。
**不变量:污浊只动"观测",留住"真值"。** ① 逆机制 → ② 干净生成 + ground-truth → ③ **可调污浊层**;观测=脏、真值=干净,基准考"从脏捞真"。**污了真值 = 基准废。**

**脏清单(治理痛点,挑着上)**:
- **身份脏**(canonical 最该发威):别名/拼写/缩写/音译/大小写/空格变体、重复记录、实体裂并;
- **缺失**:null / 缺字段 / 缺行 / 半条记录;
- **时间脏**:迟到 / 乱序 / 时区时钟偏 / 回填 / 过期快照;
- **schema/格式漂移**:列改名 / **单位变**(kg↔lb、mg/m³↔ppm) / 日期格式 / **编码乱码(GBK↔UTF-8)** / 数字存成字符串;
- **跨源冲突**:SQL/文档/新闻 对同一事实给出不一致值;
- **数值故障**:冻结(卡死值) / 尖刺 / 漂移 / 不可能值;
- **参照完整性破**:悬空外键 / 孤儿记录;
- **文本噪声**:OCR 错 / 截断 / 混语言 / 术语不一致;
- **类别脏**:该枚举处自由文本 / 类目拼错 / 未见新类目。
> 这张清单 ≈ SPI 那些数据闸专治的妖(mg/m³↔ppm、GBK 乱码、冻结传感器、站名"站"归一)——经验/技能可带,**代码不带**。

**LLM-aug:用在语义脏,别杀鸡用牛刀。**
- **LLM 该上**(需语义可信度):逼真别名/拼写变体、文档 garble、**跨源叙事冲突**、OCR 式退化、该枚举处的脏自由文本。
- **代码该上**(结构/数值脏):null / 重复 / 外键破 / 时间偏 / 单位换 / 类型强转 / 离群注入——确定性变换,别烧 LLM。
- → **混合**:确定性污浊核(可调 + seeded)+ 可选 LLM-aug 层。

**LLM-aug 风险 → 对策(信息,非指控):**
- **非确定 → 基准不可复现** ⇒ LLM 脏**一次性预烤成冻结的 versioned fixture**,跑分时**绝不 live 调 LLM**(照搬"live→缓存 fixture"做确定性测试的纪律)。
- **污染 ground-truth** ⇒ LLM **只对已知值做表面污浊**(造 3 个"Acme Inc"变体则**记下 变体→canonical 映射**供打分),**绝不发明新事实**——约束为"corrupt surface,不 generate facts"。
- 聚合 / 隐私同 §4b。
- **脏度做成旋钮**(0=干净→高,可分维度)→ 接 [`RESEARCH_axiom_gain`](RESEARCH_axiom_gain.md) 的 `gain × dirtiness` 轴。

## 4d. 关联显眼度:link 不能太显眼(finesse)
link 太显眼(精确主外键、明摆父子/继承)→ 任务退化成"跟指针 JOIN",裸 RAG 也能做、axiom-net 优势归零(无可"发现");太弱(观测无痕)→ 不可复现噪声。**判别力全在中间。**
**把 link 显眼度做成旋钮**(与脏度并列),阶梯:
1. 显式共享键(`carrier_id==id`)— 太易;
2. **模糊键**(别名/拼写/格式遮住的同一标识)— 要实体消歧(**脏度在此汇合**);
3. **属性重叠/共指**(无键,名+地等描述重合)— 要 fuzzy match;
4. **时空同现**(新闻@帧132 ↔ 异常@帧132,**无键**)— 要对齐推断;
5. **纯语义/因果**(文章**描述**的事件**解释**了延误)— 要语义理解;
6. 观测无痕 — **不可复现,别用**。

把预埋的真 link 下压到 **2–5 级**(尤其 3–5),判别力就出来。**仍握 ground-truth,只调"暴露方式"——调观测、留真值**(与脏度同套路)。
**按关系类型:** 横向(FK 式 peer)→ 压到模糊键/共现;纵向(父子/继承/包含)→ 层级留一点结构可见,**叶子归属**调隐(成员靠推)。真实系统是**混合**:用显眼度**分布**,别一刀切;难任务专挑弱 link。
**可恢复不变量:** 弱化 ≠ 抹掉;每条压隐 link 须留**足够多源弱证据**让 oracle 能复原(否则=噪声,惩罚所有人)。隐式/模糊 link 本就**更真实**(治理难的根源)→ **难度与真实性同向**。
> 甜区怎么定、怎么防"对着自己方法配题",见 [`RESEARCH_axiom_gain`](RESEARCH_axiom_gain.md) §6c。

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

## 10. 实现状态(DP1,已落地确定性substrate)
按 §9"先打通一条链"的纪律,先做 **logistics 一个场景**的确定性 substrate:
- `backend/data_sources/logistics_demo.json`(`data_source` spec)+ `backend/app/data_package.py`(确定性生成器,复用 Prism 自有 `_unit`/`_wiggle`;**先建 ground-truth『新闻→吞吐量异常→延误运单』,再让 SQL / 时序 / 新闻三源与真值一致**)。
- **两个旋钮都已落地且只动观测、留真值**:`link_explicitness`(1 字面 id → 5 纯语义)+ `dirtiness`(别名/单位/缺失/时移/数值/乱码,记 `corruption_map`)。
- `backend/app/data_package_eval.py`:`oracle / naive(字面单源) / linked(跨源时空+实体联结)` 三解题器 + 判别力探针。**结果**:link≥2 时 naive=0、linked≈0.8(任务确需跨源);脏度↑ linked 0.8→0.4(鲁棒性曲线)。这是 [`RESEARCH_axiom_gain`](RESEARCH_axiom_gain.md) ablation 的**确定性骨架**。
- `GET /api/datapackage[/{id}[/discriminability]]`;SQL 存可 `to_sqlite` 落成真 SQLite 查询。
- **诚实边界(§4d 梯度 vs 本骨架)**:确定性 `linked` 把多线索(名/区/港/异常时刻)OR 在一起,而 §4d 的 L2–L5 每级都留了至少一条可用线索,故**本确定性层只区分 L1(显式键)与 L≥2(非显式),L2–L5 同分 ~0.8**;§4d 那条精细的 L2→L5 梯度(尤其 **L5 纯语义**——此处 port 名仍写进文本、靠字面包含复原作 stand-in)是**未来 LLM/axiom 解题器**该跑出来的。`linked` 的 delay 容差是**领域先验常量**,不读 ground-truth;事件落在**互异仓库**上(去重用真正的空位搜索)。
- **DP2 已落地**:`backend/app/axiom_layer.py`(canonical 解析)+ `benchmark.py` 把骨架接上**真本地 LLM**(naive-RAG vs axiom-RAG,冻结 fixture);`GET /api/axiomgain/{id}`。首跑:axiom-RAG 质量≥naive 且输入 token≈40%,增益随脏度增长(见 [`RESEARCH_axiom_gain`](RESEARCH_axiom_gain.md) §11)。
- **§5 agentic 解析器已落地(确定性核)**:`backend/app/raw_render.py`(把包渲染成脏的异构原文,只呈现已有脏度、不动真值)+ `parser.py`(确定性启发式抽取,带 **provenance + 置信 + 可观测失败**,逐行交代不静默丢);`GET /api/parse/{id}`。往返恢复:干净 1.0、脏 backbone≈0.98。**LLM-aug 语义抽取**(乱码/别名)留作 fixture 化后续。
- **§4b 真实校准已落地(方法学)**:`backend/app/calibration.py` 逆向机制——从一个**合成替身 reference**(`IS_REAL_DATA=False`、与采样器不同过程)只拟合**聚合量**(矩/相关/AR(1)),再正向重采;**held-out 矩对得上**=按检验真实。`GET /api/calibration`。诚实边界:简约机制只抓二阶矩+线性耦合+AR(1)(skew 未复刻);接真实数据需开放许可 + 只取聚合量。
- **§7 生成器已泛化为 scenario-generic + 加第 2 个领域**:跨源**因果模式**(源事件→指标异常→受影响记录)是复用引擎,所有领域字符串(实体/字段名、id 前缀、新闻措辞、别名、量纲)进 spec 的 `vocab` + `roles` 块 ⇒ **加领域=加一份 data_source spec,零生成器代码**。`roles` 把模式槽位映射到各域 store/字段名,故判别力骨架(`data_package_eval`)保持领域无关。新增 `backend/data_sources/energy_demo.json`(通用**能源电网**域,非 SPI):变电站/读数/负荷 + 故障/检修新闻。**跨域判别力成立**(两域 L1 naive=1.0、L≥2 naive=0、linked 仍复原大部分)。**诚实下限**:energy 的纯时间型 L4(模板无区/港/枢纽线索,且两个真值异常落在 linked 的时间容差内、相距仅 3 帧)使**基础 linked 失去互斥性**、交叉误配,linked_f1≈0.33(对照 logistics 事件相距 10 帧、L4 仍 0.8)——这是**基础解题器**的下限(已由 `test_energy_l4_linked_is_honestly_weaker_no_time_exclusivity` 钉住),非真值缺陷,正是未来 LLM/axiom 解题器该补的。logistics 的**数据存储 / ground-truth / corruption_map / manifest / fixtures 逐字节不变**(全部 DP1/DP2 测试 + ablation fixtures 照旧);`generate()` 仅**新增一个 additive `roles` 元数据键**供通用解题器读取(非数据本体)。`to_sqlite` 亦已 role 化(按 store 键建表、列由各 store 自身 schema 推断),energy 包同样可落 SQLite。
- **未做(诚实):** §3 PDF/NoSQL 模态、§7 第 3 个场景、energy 域的 **axiom-gain LLM-ablation**(需新 fixtures;当前 ablation 只在 logistics 跑)、RESEARCH 的**完整研究**(跨模型矩阵 + 多 seed CI + $ 定价 cost-frontier + **学习式** axiom 层做真 build 摊销)。当前 axiom 层为算法式(build≈0)。

---
*—— 设计笔记。这是给在建会话的方向锚,不是指令;建造的人说了算。*
