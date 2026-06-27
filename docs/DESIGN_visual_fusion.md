# 设计笔记 · 多域融合视觉奇观(stunning 且诚实)

> **状态:方向锚(design note)。v1 的 SVG 形态已落地**(见下「v1 已落地」),three.js 银河碰撞是后续升级。
> 关联:[`METRIC_nexus_reality.md`](METRIC_nexus_reality.md)(奇观渲染的就是它的输出)· [`OBSERVER_NOTES.md`](OBSERVER_NOTES.md) §10(超图远期)· 现有 `OntologyGraph.tsx`/`graph.ts`/P1 `ReplaySlider`(不动)。

> **v1 已落地(SVG)+ v2 已落地(three.js 银河碰撞)**:后端 `GET /api/nexus_xdom/view?seed=` 给**每桥 nexus_confidence**(三独立渠道 ≥2/3 入各自 top-10% → 点亮;否则 medium/巧合,**标签无关分层**)。前端 Cockpit `跨域 nexus` tab,**3D/2D 切换**:
> - **v2 `NexusGalaxy.tsx`(R3F,懒加载独立 chunk 890kB——不进主包)**:两螺旋星团(INFRA 冷青 × LIBRARY 暖琥珀)+ 白热合并核(scale=真桥数)+ 候选桥三态;**luminance-threshold Bloom 只让白热高桥 + 核过曝**(`luminanceThreshold=0.7`;仅 HDR HOT 高桥/核 toneMapped=false 超阈,**代码层虚影/单渠道不可能发亮**,普通混合不叠加),OrbitControls 自转(`prefers-reduced-motion` 关),drei `Stars` 极淡星场(唯一非数据元素)。无 WebGL → 自动回退 SVG。
> - **v1 `NexusView.tsx`(SVG,回退/无障碍)**:同数据,候选桥三态 + feGaussianBlur 辉光。
> - 共享:**诚实计分板 HUD**(候选/真桥/单渠道/巧合/精度)+ 不可摘 caveat。落实 §0/§6 铁律:**光多少=过 ≥2 渠道的桥多少**,**诚实稀疏**(实测每包仅 ~6 桥发光、其余 100+ 虚影),前端零发明置信(只读后端)。实测:R3F canvas WebGL2 正常、prod build 懒 chunk 分离、3D/2D 切换 + SVG 回退均通。GW/Sinkhorn 对齐动画(§2 v2 引擎)仍是后续。

## 0. 命题
把"多个领域本体的 net space **碰撞 → 融合**为一个新空间"做成 **stunning 的视觉奇观**。
**铁律——美必须编码真,不是装饰**:每个视觉通道映射一个**真实量**;边的实/虚/明暗 = [`METRIC`](METRIC_nexus_reality.md) 的 `nexus_confidence`(3 透镜 ≥2/3 收敛);**两个无关域融合必须诚实地稀疏**(允许"诚实的丑",不许假满屏)。**没有这条,它就是它要反对的那种"看着权威实则没证"的谎。**

## 1. 主脊:银河碰撞 / Nexus 引力铰合(Galaxy Collision)
两个域 = 两个旋臂星云(实体=恒星,域内 relations=暗引力丝)。在新 **Confluence** lens 里从两侧漂近——但**不是脚本拖着撞,而是被真实对齐过程拽近**:位移每帧来自后端的 GW/Sinkhorn 对齐迭代,**整个画面的核心动势直接是度量收敛本身**(忠实"动画=真实对齐回放"铁律)。被三透镜判真的少数引力井才真正把两边恒星拉合、点亮成实桥;判巧合的井引力衰减、星系擦肩而过、留下诚实的虚影残迹。
> 选它因为:近黑底 + 加性 bloom 的"咬合"拐点最 wow;**bloom 高阈天然成诚实闸**——只有 `confidence=high` 过阈才溢光,代码层虚影不可能发亮 →「**光多少 = 真桥多少**」物理成立;旋臂星云最经得起"诚实的稀疏"(两团冷盘擦肩本身就美,不靠连接撑场)。

**嫁接其余三套里真正服务诚实的点子**(拒纯炫技):
- **三透镜裁决弧(取自 crystalline)**:hover 候选桥 → 绕桥中点亮三道弧(ΔL=青 / CBBS=绿 / CACE=洋红),≥2 弧同亮才点火;三弧齐=白(3/3),缺一弧=偏色 + 显式「单透镜异议」。**把统计检验变成手可触的光学事实。**
- **Sinkhorn 脉冲泵动(取自 synaptic)**:引力井深度逐迭代变化 = 传输质量 `Tᵢⱼ` 的脉冲,**字面看见熵正则在对齐矩阵**(v2 高潮引擎)。
- **n-元超边 = 半透膜瓣(取自 fluid-membrane)**:3+ 跨域恒星围成的超边渲成半透发光膜瓣,不透明度=收敛度,只在真收敛时成形(v3,接 §10 超图)。
- 明确**拒绝**:全屏玻璃折射(性能黑洞)、高分辨 marching-cubes isosurface(易变 lava lamp)、film grain/vignette(纯装饰、零真实量)。

## 2. 通道 → 真实量 映射表(铁律落地,逐通道有出处)
| 视觉通道 | 真实量 | 来源 |
|---|---|---|
| 恒星 3D 位置 | 域布局/嵌入(`layoutGraph`→旋臂);跨域=当前 `T` 诱导重心 | `graph.ts` / nexus `T` |
| 两星系质心间距 | GW/Sinkhorn 当前迭代对齐距离 | `steps[k].residual` |
| 恒星辉光强度/尺寸 | nexus 锚强度(参与高质量 `T` 条目质量和) | METRIC 桥端点参与度 |
| **边 实/虚/暗淡褪去** | **`nexus_confidence`(3/2/≤1 透镜收敛)** | METRIC §1 命门 |
| 边色相(青/绿/洋红混) | ΔL / CBBS / CACE 三分量 | 三透镜各分 |
| 边粗细 | 校准置信 `p=1−2^{−ΔL}`(Kraft) | METRIC §3 |
| 引力井深度(下垂) | ΔL bits 净增益 | METRIC §2 |
| 脉冲质量/速度 | 传输质量 `Tᵢⱼ` | Sinkhorn 解(v2) |
| 合并核白热体积 | 已收敛真桥计数 | `confidence=high` 计数 |
| 三道裁决弧亮灭 | 各透镜过阈与否 | 三透镜 pass |
| 双盘缝隙/空旷面积 | 未收敛比例(诚实稀疏读数) | `1 − k/N` |
| slider 位置 | GW 迭代步 `k` / 时间帧(双模) | 复用 `ReplaySlider` |

配色全派生自现有 `spec.accent`(域 A infra `#2f7d9a` 冷青 / 域 B library `#8a5a2f` 暖琥珀——本就冷暖对,零硬编码即可分域;真桥点火=加性白热,稀有故珍贵)。后期:`SelectiveBloom` 高阈(只真桥+白热核过曝)+ 轻 `DoF`(焦平面钉在咬合铰链)+ 加性星场(唯一允许的非数据元素,极淡、不进 bloom)。**每层运动都编码真实量,零 idle 漂浮;收敛后静止——静止=收敛。**

## 3. 奇观叙事(分离→碰撞→对齐→逐条点亮→沉淀)
- **帧 0 分离**:两星云悬于两侧,中间空黑。HUD 诚实计分板:「候选井 N · 真桥 0 · 巧合 0」——诚实地、令人不安地空。
- **趋近相(碰撞)**:沿候选井缓缓拉近 + 旋转取向(角=对齐矩阵纯函数);间隙浮现密密麻麻**灰紫虚影候选井**(组合爆炸,绝大多数虚)——故意又乱又稀疏地丑;引力井脉冲泵动 = **字面看见矩阵在对齐**。
- **判决相(涌现桥逐条点亮)**:迭代收敛后亮三透镜裁决弧;**绝大多数虚影井褪成残渣消失**(Sinkhorn 把质量从巧合桥抽走的忠实回放);只有 ≥2/3 收敛的少数井骤然加深、恒星被猛拽到一起、「啪」点亮成实线(三色合成白热),bloom 第一次真正溢光。**逐条、按置信排序**点(高置信先),非一次性满屏。
- **money_moment「咬合 / lock-in」**:GW 残差跨收敛阈那一两帧,画面从两团冷盘**塌出一条发光铰链脊线**(spine of verified nexuses),合并核白热涨起。每条桥对应 `T` 一个被三透镜确认的高质量条目;**咬合时机=真实残差曲线拐点,非预录关键帧**。
- **沉淀相**:bloom 余晖落定,只剩已点火真桥缝出的第三层联合空间(v3 含膜瓣),虚影全暗灭。
- **三种观看**:自由 orbit(受限 OrbitControls)· 引导式 cinematic(`ReplaySlider` 自动步进当"播放对齐过程",每帧仍是真实 `T` 状态纯函数)· scrub(拖 slider 在迭代里穿梭,桥凝成实线或熔回,可逆、逐帧一致)。

## 4. 分期实施(每期最小但已惊艳,锚 METRIC roadmap)
- **v1 — 最小惊艳**(METRIC v1:单边桥级、Phase A 现 substrate):后端 `GET /api/nexus/{a}/{b}` 纯确定性三透镜,返回每候选桥 `{三透镜分, confidence, p, ΔL, dissent}`;**不需 GW 动画,先出静态咬合帧**。前端新 `NEXUS_TAB`(照搬 `GRAPH_TAB` synthetic-tab 模式,SVG 视图一字不动)+ `<NexusLens>` 懒加载 chunk:两星系 instancedMesh 旋臂 + 候选桥三态 + SelectiveBloom + HUD 诚实计分板 + 不可摘 caveat。**这一期已 stunning**:近黑底 + 白热脊线 + 三色边 + 诚实稀疏的空。slider 暂绑"按置信逐条点亮"的揭示进度。
- **v2 — GW 软对齐动画**(METRIC v2:GW 第 5 透镜):后端 `…/align` 返回**确定性 GW/Sinkhorn 迭代序列** `steps[k]={transport 稀疏条目, marginals, residual, 逐桥分}`;slider frame=迭代步 k;引力井脉冲(shader uniform=`Tᵢⱼ` DataTexture);质心间距=residual;咬合绑残差拐点。补"矩阵在我眼前对齐"的智性高潮 + orbit + cinematic。
- **v3 — n-元 nexus + 真双域**(METRIC v3 + Phase B):建抹掉跨域字符串线索的真双域 spec 对,检验单位升到子图/超边;膜瓣超边;接 §10 超图遍历。**此期才正式宣称"跨域 nexus",之前永久标"跨源原型"。**

## 5. 技术栈 + 数据契约 + 降级
栈(**全部懒加载、不进首屏主包、SVG 主体零受影响**):`react-three-fiber` + `three` + `@react-three/drei` + `@react-three/postprocessing`(EffectComposer: SelectiveBloom + DoF)。接入 `Cockpit.tsx` 加 `NEXUS_TAB`(需 ≥2 spec 可选),照搬 GRAPH/SIM synthetic-tab 模式;`OntologyGraph/graph.ts/time.ts` 一字不动;`ReplaySlider` 复用(`frame` 当迭代步传入)。
性能:每域单 instancedMesh(数千实例一 draw call,辉光走 instanced attribute);候选桥单 LineSegments 批量 α(低置信 LOD cull),只**已点火真桥**(稀少)走较贵可变宽 + bloom 选择层;脉冲/弧走 ShaderMaterial(GPU 端动画零 per-frame JS);目标 60fps。**诚实稀疏顺带保性能——真桥本就少。**
数据契约(扩展 `types.ts`/`api.ts`,沿现有 RESTful + frame):
```ts
interface NexusBridge { a:string; b:string; confidence:"high"|"medium"|"coincidence";
  lenses:{deltaL:number;cbbs:number;cace:number}; dl_bits:number; p_calibrated:number; dissent?:string }
interface NexusResult { pair:[string,string]; substrate_note:string; caveat:string;  // METRIC §7 不可摘
  bridges:NexusBridge[]; steps?:NexusAlignStep[];  // steps 仅 v2
  counts:{candidate:number; real:number; coincidence:number} }  // HUD 诚实计分板
```
后端 `backend/app/nexus_*.py`(METRIC §4 设计)、纯函数确定性 `_unit` 播种、加法零回归、frozen-fixture 进 benchmark、不变量写硬断言单测;**前端零发明置信**。
**非 WebGL 降级**:回退现有 SVG 图谱(2D 两列 + 逐条点亮桥),功能不丢、奇观降级,**绝不假数据补满**。

## 6. 诚实不变量(写成验收硬断言,CI 守门)
1. **无真量不画**:每束光必有映射表来源;`恒星辉光>0 ⟺ 参与 ≥1 条 confidence≥medium 桥`;`白热核体积 == confidence=high 计数`。
2. **无 nexus 则诚实稀疏(允许诚实的丑)**:bloom 阈由 confidence 驱动,**虚影代码层不可能过阈**;提供**负控开关**(两域复制/随机重连)——正确实现下应几乎全褪去;**CI 截图断言空域确实空、零 bloom**。禁:补满屏假桥、填充式装饰连线、给 ghost 加吸睛动效。
3. **不暗示未证因果/意义**:屏角常驻不可摘 caveat(METRIC §7);medium 桥永显「单透镜异议」;跨域真桥默认**无向**(对称量不证方向),不画因果箭头;Phase B 前永久标「跨源原型」。
4. **动画=真实对齐回放**:咬合绑真实残差拐点(非 CSS easing/关键帧);slider 每格索引后端预算的确定性迭代状态;来回 scrub 逐帧一致可复现。
5. **前端零发明置信**:桥状态/分数只来自后端;无数据则老实空。
6. **代理诚实**(随结论挂出):ΔL 是压缩器给 K 的上界、GW 是局部极小;**换实现排序须稳**,否则在度量"我实现恰好抓到的结构"。

## 7. 风险 + 缓解
1. **变 lava lamp(最致命)**:bloom/加性太爽,引诱调亮虚影、补桥、做预录炫动画。缓解:亮度严格由 confidence 驱动(代码层虚影不过阈)、咬合绑真实残差拐点、计分板不可关、映射写 CI 硬断言 + 负控自检、自转绑 frame 纯函数收敛即静止(禁 idle 漂浮)。
2. **性能**:M×N 桥 + 双 pass 后期在弱 GPU 偏重。缓解:收敛门天然限真桥数、LOD cull、instancing、shader 动画、quality 档降级(更稀疏=方向与诚实一致)。
3. **依赖重**:three 全家给轻量 SVG 应用加 bundle。缓解:严格隔离为**动态 import 懒加载 chunk**,不进主包、不碰现有视图;一个 lens 打磨透,别铺半成品(契合 for-fun 深度>广度)。
4. **3D 眩晕 / 可达性**:缓解:`prefers-reduced-motion`→收敛后即静止+关 bloom 呼吸;DoF 可关;**SVG 降级本身是无障碍兜底**(2D + 纯文本 HUD 计分板,屏幕阅读器可读"真桥几条")。
5. **后端依赖未建成**:三透镜是真活儿、GW 是 v2、Phase B 未建。缓解:视觉先接确定性 fixture/Phase A 跑 v1 静态咬合帧、标「原型数据」;**不假装已有跨域 nexus 判据**。

---
*—— 设计笔记。这是给在建会话的方向锚,不是指令;建造的人说了算。*
