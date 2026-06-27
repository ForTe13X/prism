# 研究设计 · 真 nexus 度量(real-nexus-vs-coincidence)v1

> **状态:研究设计锚(methodology note),非已建成、非指令。** 旁观会话 + 一轮 5-透镜对抗式 workflow(发散→验真→综合)整理,供在建会话取舍。
> 关联:[`RESEARCH_axiom_gain.md`](RESEARCH_axiom_gain.md)(§6c 判别区间纪律)· [`DESIGN_data_package.md`](DESIGN_data_package.md)(预埋真值/distractor substrate)· [`OBSERVER_NOTES.md`](OBSERVER_NOTES.md) §10(停放的超图 vision)。

## 0. 它是什么 / 不是什么
为"多域本体融合"的核心难题——**区分真跨域 nexus 与硬对齐挤出的巧合**——设计一个**站得住脚、可复现、有参考价值**的度量。
- **能声称**:这条桥的统计联合性/结构惊异/显著性,**超出了〈度数机械 / 随机对齐 / 多重比较〉所能挤出的巧合量**;并给**校准的**置信。即:**量化/界定巧合**。
- **不能声称**:证真、证因果、证"语义有意义"。一个按构造系统性过耦合两域的生成器会骗高分——**压缩增益 / 度数惊异 ≠ meaning**。这是结构上限,不是 bug。度量永远只认"透镜/判据"身份,不冒充定理。

## 1. 核心设计:收敛效度(convergent validity)——这是灵魂
**绝不用单一花哨数做 headline。** 取 3 条**失效域不重叠**的独立透镜,各给一分;
> **`nexus_confidence` 仅当 ≥2/3 透镜各过其预注册阈、且符号一致时才非零**(3/3=high,2/3=medium 并显式标"单透镜异议",≤1/3=判巧合)。
每条透镜都有已知失效域,三者不重叠,**一致即互证**。诚实代价:收敛门**压低 recall**(任一透镜失效域内的真桥被压)——这是**用 precision/校准换 recall** 的明示取舍。

## 2. 三骨透镜(各管一类巧合,各自师出有名、自带 null + 自带定律自检)

| 透镜 | 借的框架 | 判据(真桥 ⇔) | 它管的失效模式 | 守自己的法(写成单测硬断言) |
|---|---|---|---|---|
| **ΔL-Nexus** | 两部分 MDL / 算法信息(Rissanen, Kolmogorov) | 经桥联合编码**严格短于**独立编码:`ΔL=L(B)−L(B\|A,n)−L(n)>0`。`L(n)`=桥本身的描述费=**"硬挤一条对齐"的明码标价** | 高基数伪相关 / 多重比较挤出的对齐 | 算法互信息非负(`L(B\|A,n)>L(B)`即拒桥)· Kraft→`p=1−2^{−ΔL}`校准从码长长出 · 换压缩器排序须不变(O(1)不变性) |
| **CBBS** | 度数保持 configuration-null(Newman modularity) | 跨域边质量**超过度序列机械强制**(`z/p` from Maslov–Sneppen 精确保度 swap) | hub 度数混杂(中心节点偶然多连)——ΔL 不直接除掉 | Q-分解闭合 · 逐 swap 度序列守恒 · `E[Δ]=0`(喂度匹配随机图→`p`≈Uniform) |
| **CACE** | 置换检验→BH-FDR→稳定性选择(Neyman-Pearson / Benjamini-Hochberg / Meinshausen-Bühlmann) | 发现尺度上控住**整族**假阳率 + 抗扰动可复现(置换 `p`→BH→bootstrap 选择概率 `Π`) | 发现尺度族膨胀 + 脆弱偶然桥——单条算不出 | 置换 `p` 在交换性下 ≤Uniform(KS 可验)· BH 的 `E[FDP]≤q*` · `Π*`提高单调收紧误选 |

> **为何这三条**:MDL 的 `L(n)` 惩罚、CBBS 的闭式 null、CACE 的 FDR 是三套**成熟、自带 null/定律**的机制,承重诚实度最高。

## 3. 若只能保一条骨:ΔL-Nexus
1. **它直接量化"巧合"本身,不是间接代理**:`L(n)`(描述桥要付的 bits)就是"硬挤一条对齐的代价",付完净增益 `ΔL≤0` 即巧合——把"巧合"从事后阈值变成**框架自带的数学定义**("判据即定义",另两骨没有)。
2. **统一币种最强**:结构(度序列码)+属性(分布残差码)+语义(共现码)全折成 **bits 可加、跨模态可比**——最契合"领域无关融合"。
3. **校准免费**:Kraft → `p(real)=1−2^{−ΔL_bits}`,置信有信息论意义,不外配校准器。
- **必带 caveat**:① 是压缩器给 `K` 的**上界代理**(劣压缩器→真桥假阴)→必报换压缩器(zlib/算术码/PPM)排序消融;② **偏高带宽桥**——低带宽真 nexus `ΔL≈0` 被误判,**正因如此 v1 不能只靠它单条**;③ 对称量,不证方向/因果。

## 4. 可复现评测协议(锚在已落地的确定性 substrate)
**诚实前置**(决定协议形态):现 Prism substrate 是**单域多源包**(`data_package.py`:`generate(source_id,dirtiness,link_explicitness,seed)`、`_truth_event=None` distractor、`corruption_map`、L1–L5、`_unit` 哈希播种),**不是两个独立域的联合空间**(`OBSERVER_NOTES §10` 把真双域停为远期)。故分两期:

- **Phase A(现 substrate,立即可跑)**:真桥=预埋的跨源因果链(news→throughput 异常→延误);伪桥=`distractor` + 随机重连 + "两域复制"负控。对真桥∪伪桥每条算三透镜 → **precision/recall · ROC-AUC · reliability diagram/ECE**;每透镜各自的 null 全跑齐(缺一即把 vanity 数当真:ΔL 置换+压缩器消融 / CBBS swap+**混合诊断硬闸** / CACE 置换+**KS-against-Uniform** 不过则切保度置换并披露)。**此期验证的是"跨源 link 真伪原型",不得宣称"跨域 nexus 判据"。**
- **Phase B(v2 前提,须先建)**:新建抹掉跨域字符串/区域线索、只留语义可复原性的**双域 spec 对**(如 infra × library),埋跨域真 nexus + 随机伪桥 + 复制负控。**之后**才谈"跨域 nexus 判据"。

落地:`backend/app/nexus_*.py`(纯函数、确定性、`_unit` 播种、加法零回归)+ `GET /api/nexus/{a}/{b}` + frozen-fixture 进 benchmark + 框架不变量写成硬断言单测;多 seed 报 mean±CI(gain 须 > 噪声)。

## 5. 判别力 + 防"对着自己方法配题"(诚实命门)
- **甜区 (link, dirt) 由与三透镜无关的独立判据预注册**:「裸 baseline 吃力 ∧ oracle 可复原」(`RESEARCH_axiom_gain §6c`);**三透镜分数不得参与选难度**。每条弱化须过 oracle"可复原"验(难而非不可能)。
- **每透镜隐藏旋钮跑分前版本化冻结**:ΔL 的压缩器/量化网格/`L(n)` 编码 · CBBS 的 swap 数/2-block 划分 · **CACE 的 `T(e)` 签名核**(它的真杠杆、不在借来框架保护内,调它=三闸语义沦为对被调核背书)。
- **必打过的笨 baseline 阶梯**(打不过即该透镜退场):字符串 Jaccard · Pearson/Cramér's V · 单域 MI 取大 · raw cross-edge count · **⭐时间巧合 baseline**(只用 `|Δframe|≤tol` 同现,不付任何代价)。**最致命的一条**:substrate 里 L4–L5 字符串失效处,真正的分离信号就是**时间同现**;三透镜的卖点必须是在 L4–L5 **严格超过时序 baseline 的 AUC**,否则只是把时间戳同现换成 bits/z 重述,**无增量结构内容**。
- **判别赌注(能输)**:沿 link L4→L5、dirt 升,收敛(≥2/3)AUC ≥0.85 且严格 > 时序 baseline;裸 baseline 跌到 ≤0.6。跌到 ≈baseline 即判负,不打补丁。

## 6. Roadmap
- **v1(大致刻画 + 站得住脚 + 可复现)**:三骨透镜纯确定性实现于现 substrate;收敛效度规则;全套 null + 不变量硬断言;预注册甜区 + 冻结旋钮 + baseline 阶梯(含时序);出 PR/AUC/ECE + 判别/退化曲线 + 多 seed CI;诚实标"跨源 link 原型,非跨域 nexus";范围=单边桥级。
- **v2(扩展/确证)**:建**真双域 substrate**(Phase B);加 **CDSC(PID 交互信息)** 作第 4 确证透镜(需目标 T、并行 ≥2 算子仅排序一致才采信、只覆盖"协同型"桥);加 **GW-Distortion(最优传输)** 作第 5(先预注册 ε/λ + ε 敏感性 + 三角不等式/质量守恒运行时断言 + partial-GW 兜底非等距真桥召回);CBBS 升 dk-series/motif-null;CACE 加 PRDS 验证触发(违反退 Benjamini-Yekutieli)。
- **v3(polish / 真实域)**:检验单位从单边升到**子图/超边**(n-元 nexus);LLM-aug 造真正只留语义的 L5;校准外推研究(真实域无 ground-truth→只给相对排序+置换 p,不给绝对真值率,**永久挂出**);接 `§10` 超图遍历发现循环。

## 7. 承重诚实(随结论永久挂出,不可摘)
1. **不证真/不证因果/不证"有意义"**——只界定巧合 + 给校准置信;系统性过耦合的生成器会骗高分。
2. **代理性**:ΔL 是压缩器给 `K` 的上界 · CBBS 解析 `z` 在 simple-graph 下微误归一(只信 swap 经验 `p`)· GW(v2) 是局部极小;**换实现排序须稳**,否则在度量"我的实现恰好抓到的结构"。
3. **失效域(precision/recall 取舍明示)**:ΔL 偏高带宽桥 · CBBS 稀疏真桥功率地板 · CACE/CDSC 真但**冗余型** nexus 漏判(协同低≠非真);收敛门再压 recall。
4. **CACE 命门=交换性/独立性**:重尾度分布 → 标签置换 null 可能不正确、BH 在 p 强相关下失控;须实测触发受限置换/BY 并披露偏离裸保证。
5. **当前适用域**:单域多源 ≠ 双域联合空间;v1 是"跨源 link 原型"。
6. **合成外部效度**:合成高 AUC 不保真实域;真实域无 ground-truth → 只给相对排序 + 置换 p。
7. **vanity 防线是承诺非保证**:多个隐藏旋钮客观可调;缓解(预注册冻结 + 跨实现一致性 + 硬闸)把"可悄悄调"降到"调了会被 null/一致性抓到",但旋钮存在,风险须如实记。

## 8. 实现状态(M0 已落地:baseline 阶梯 + 一个决定性的诚实发现)
`backend/app/nexus_substrate.py`(候选桥枚举:hub 异常 ±tol 内的 (news, hub) 对,eval 标签 real/coincidence 取自 `_truth_event`+events、**打分器永不可见**;负控:rewire / distractor-only)+ `nexus_baselines.py`(笨 baseline 阶梯:⭐time-coincidence / string-Jaccard / entity-mention / anomaly-depth)+ `nexus_eval.py`(tie-correct ROC-AUC、average precision、ECE,及 link 扫描 / 负控 runner;**≥40 seed 池化**——每包仅 ~2 正例,AUC 量子化步长 1/22,单包不可读)+ `GET /api/nexus/{id}/{baselines|sweep|controls}`。全确定性、role-generic(两域可跑)。

**M0 的诚实发现(先量标杆,免得给自己配题 §5/§6c)**:在**现 substrate** 上,**time-coincidence baseline 在各 link(L1–L5)、各脏度(0–0.95)AUC 均近天花板(≈0.94–0.99)**。根因结构性:真桥**按构造即时间巧合**(news 帧 = 事件帧 = 异常帧,完美共线),而脏度只把 news 帧扰 ±1–2。⇒ **§5 字面要求的「L4–L5 严格超越 time-coincidence」在本 substrate 不可达**——时间戳即充分统计量。string baseline 如期:L1/L2≈1.0、**L3 仍靠 region 残留保持 ≈0.86**(`{kind}袭{region}` 仍泄漏 hub 名里的 region token)、**L4 才真崩(jaccard≈0.10)**、L5(端口字面)回升≈1.0;负控如期:rewire 时序信号跌破标杆、distractor-only 无真桥。

**设计面板(13 agent、多人实测)与 M0 独立同证,并指出唯一诚实的正面通道**:不是「击败时间」(L4 不可能),而是**免时间的语义通道**——*去别名*(dealias)后的 token→hub 共现(冻结 clean-vocab 表、**永不读帧**)。实测数见 §8b 表(L1/L2/L5 高、L3 中、**L4 低于随机**)。真正可证伪的赢点 = **抗脏度**:d=0.5 时去别名守住高 AUC,而*裸* 串匹配在区域别名链路(L2/L3)跌——**去别名 vs 裸串匹配的差距才是真结构内容**(冻结词表共现扛得住别名/乱码腐蚀,子串匹配扛不住)。面板建议把 ΔL/MDL 当**校准标尺**(Kraft `p=1−2^−ΔL`);**M1 实现取 ΔL_sem 为判别器**(faithful to §2/§3「ΔL-Nexus 是承重透镜」),并**并列报裸 overlap 作对照**(二者排序不同,见 §8b)。

**诚实边界(承重,随 M0 数挂出)**:① **属性/记录残差通道在本 substrate 为零**——carrier/weight 按全局记录序号播种、**与 hub 无耦合**,每 hub 仅 0–2 延误记录,纯噪声,不可据此立论。② **「≥2/3 独立透镜」收敛效度在本 substrate 是戏**——ΔL_sem/CBBS/CACE 都读同一张 token 表,实为「一信号三读」而非三票;须明说,架构留待 Phase-B 真双域才有真独立性。③ 候选枚举用了**时间 candidacy-prior(±tol)**仅取「时间上邻近的硬负例」;面板的全笛卡尔(无时间预筛)只会让 time AUC 更高(混入平凡远负例),故 tol 集是**对「时间已解」更保守、更难**的度量——二者结论一致。

**推论(指导 M1,绑死 §6c 反陷阱)**:要让透镜有意义,需引入**时间不可分的硬负例**(与真桥**同帧**却**无因果记录链**的 distractor 异常)。**但**(§6c 反陷阱警戒):该硬负例难度**必须由与三透镜无关的独立判据预注册**——co-timed 须经 oracle 验「确实时间不可分」**且**「record-link 缺失确可从观测复原」,**三透镜分数不得参与调难度**;否则「严格超越 time」将不可证伪(等于把任务配成只有所选透镜能分)。M1 路线(面板蓝图):先把 `I_sem` 语义透镜 + ΔL 校准 + **去别名 vs 裸串抗脏度**结果落地(这本身就是可发表的真赢点 + 诚实 L4 负结果),再谈硬负例与 CBBS/CACE 佐证。

## 8b. M1 已落地:时间无关语义透镜(ΔL_sem + 裸 overlap 对照 + Kraft)
`backend/app/nexus_lens_sem.py`(`score_bridges`/`run_sem_lens`)+ `GET /api/nexus/{id}/sem` + 8 测试。`sem_overlap` = 去别名后 news body token 与 hub 身份 token 的共现数;判别器 `ΔL_sem = Σ_{matched} log2(nw/df(token))`(独特 id/name token 省 log2(nw) bit,人人共享 token 省 0),Kraft `p=1−2^−ΔL`;**全程不读帧**(时间无关,实测:篡改所有帧字段 + ctx 的 anomalies/depth + hub 行伪帧,ΔL 不变)。去别名用通用 resolver `axiom_layer.canon`(域字典,非本包真值),故非 truth-adjacent;ON/OFF 全消融。

**实测(40 seed 池化,两域同形)**:
| | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| **AUC(ΔL_sem, dirt0)** | **1.00** | **1.00** | 0.86 | **0.36** | 1.00 |
| AUC(裸 overlap, dirt0) | 1.00 | 1.00 | **0.93** | 0.23 | 1.00 |
| 去别名抗脏度 gap(ΔL, dirt0.5) | +0.03 | **+0.11** | **+0.09** | −0.03 | ~0 |

- **真赢点**:L1–L3/L5 有真判别力,且 **dirt0.5 时去别名 ΔL_sem 击败裸串(no-dealias)在区域别名链路 L2/L3**(gap +0.11/+0.09;L4/L5 别名不咬合处 gap≈0/略负,已列表)——冻结词表共现扛得住别名/乱码,子串匹配扛不住,这才是**超出时间**的真结构内容。
- **诚实负结果(即贡献)**:**L4 AUC=0.36 低于随机**——body 不名 hub 而 distractor 仍名其 region,lens 诚实地错排,证明它量的是非时间结构、不是洗时间戳;time-free gate 在 L4 如实判否。
- **ΔL ≠ 裸 overlap(不同排序,诚实并列)**:distinctiveness 加权改变排序,**非「只加校准」**;本 substrate 上裸 overlap 在 **L3 反优于 ΔL(0.93 vs 0.86)**,故两 AUC 并列报、不宣称等价。
- **校准诚实**:Kraft p 偏紧(ECE≈0.13–0.21),因 ΔL 是码长上界、偏自信;真校准器需拟合,留后续。属性通道未用(本 substrate 为零)。

## 8c. Phase B gate 已落地(写 channel 前的硬关:time-coincidence 必须「弱而在场」+ 窗须混类)
锚:`backend/app/nexus_phaseb.py`(纯函数、确定性、`_unit` 播种,复用 `generate()` spec 机制 + `nexus_eval.roc_auc` 平局校正 + `nexus_baselines.time_coincidence`)+ `data_sources/infra_demo.json`×`library_demo.json`(双域 spec,**区域/端口/实体词表零 token 重叠**;news 模板骨架跨域共用、非域标识词,后续读 news 须分离)+ `tests/test_nexus_phaseb.py`(11 断言)。**未写任何 channel**——这是 channel 前的关。

**为何先建 gate**:§8 已证 Phase A 上 time 是充分统计量(real≡时间巧合),lens 无诚实空间。Phase B 全部赌注=把 time 调成**弱而在场**的对手,留出空间。该「time-AUC 落 [0.60,0.75]」此前**未证**;若空,基底按 kill-criterion (i)/(iii) 自否,设计须先改。**这是先量对手强度、再投 channel 的预注册**(§6c 反陷阱:难度旋钮由与 lens 无关的独立判据=time 自己的 AUC + 窗混类 定,lens 分数不参与选难度)。

**机制(全确定性)**:K=4 潜类 · W=3 共享事件窗 · span=16 帧/窗 · 每侧 8 锚(取自 `generate()` 的 hub store)。候选 = **同窗(|Δwindow|=0)** 的 锚A×锚B 对;**real ⇔ 两锚同潜类**(跨域共因),潜类 hash 自 (seed,side,id)、**独立于窗**。同类锚在窗内同相位点火(real 对 |Δframe| 小),异类锚相位分离(coincidence 对 |Δframe| 大)——**把 time 从天平降为弱对手的唯一旋钮 = 窗内 frame jitter**;window_load(每窗每侧点火锚数)调每窗潜类混合度。

**统计纠错(对抗式 review 抓到的 blocker,随结论挂出)**:gate (b) **不能**按「逐窗熵的最坏窗(`min`)≥1 bit」判——`min` 是 3·N 个窗上的**秩序统计量**,随种子只降不升、**无大样本极限**;本基底(K=4 / 每侧 8 锚)任何非退化 load 总有某种子产出欠混窗,故 `min≥1bit` 闸**只量池子大小、不量基底**:同一旋钮 N=40 过、N≥80 即出现 class-pure 窗而崩。**改用收敛统计**:窗均熵(≥1 bit)+ **leak-rate=P(窗熵<1 bit)≤ 1%**(预注册容差);二者随 N 收敛,leak-rate 随 load 单调降。AUC 同时**去偏**:删掉原 `_frame` 的边界 clamp(它把外侧类的 jitter 尾压到窗沿,class-不对称地**虚高 time-AUC ~0.02**);窗是**类别**分组,dframe 只在同窗内算,绝对帧位相消,故无需 clamp。

**实测(400 seed 池化——AUC ≥40 即稳,但 ~1% 的 leak-rate 需 N·W·τ≫1 窗故取 400;66 格点 load×jitter,~9s)**:
| 量 | 值 |
|---|---|
| time-AUC(jitter=0) | **1.0000**(time 完美分离 = Phase A 杀手如实复现) |
| time-AUC 随 jitter 单调衰减(去偏后) | 1.00 → ≈0.59(jitter=20);带内点遍布各 load |
| 窗均熵 | 各 load 均 ≥1 bit(1.34→1.85),随 N 稳 |
| leak-rate by load(收敛值) | L2≈19% · L3≈6% · **L4≈1.8%** · **L5≈0.5%** · **L6≈0%** · L7≈0% |
| 带 [0.60,0.75] **可达?** | **是**(20 接受点);但 (b) 把诚实下限钉在 **window_load ≥ 5**(load=4 的 ~1.8% leak 超 1% 容差被拒;**非** 旧报的 load≥4——那是 N=40 假象) |
| 冻结旋钮(最低 leak) | **load=6, jitter=14 → time-AUC=0.660**(去偏;旧 clamp 报 0.676/0.679),窗均熵=1.80 bit,leak=0.0%,prevalence=0.25(=1/K) |

⇒ **基底可行(GATE 意义上):time 弱而在场、窗稳混类,§4 Phase B 设计不自否,可投 CH1/CH2/CH3——但冻结 load=6,不是 load=4。**

**诚实命门(随结论永久挂出,最承重一条)**:gate **只证 time 弱到留出空间 + 窗混类,不证任何 lens 真能补上**。当前潜类是**纯 hash 抽象标签、无可观测语义**——此刻没有 lens 能复原它(time 也不能)。**必要非充分**:把「同潜类共享可观测词表/结构(CH1/CH2/CH3 读)」做进去、再验「time-free 通道确实能复原潜类且**严格 > time**」才是 channel 活儿,gate 不碰(故 harness 刻意 **channel-blind**:只读锚身份 + 注入的潜类/窗/jitter 层,不读 news/throughput/语义)。次要诚实:候选用 (a,b,w) 三元(同对跨多窗 = 多次时间观测,标签一致不偏);`window_load≥5` / load=6 是与 (K=4, 每侧8锚) 及 1% leak 容差绑定的结论,**非普适常数**;严格逐窗 ≥1 bit 在本基底对任何非退化 load 不可保证(故采分布式判据)。

---
*—— 研究设计锚。这是给在建会话的方法学参照,不是指令;建造的人说了算。*
