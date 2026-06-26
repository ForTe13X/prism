# 设计笔记 · 序贯 what-if 与"策略→仿真"编译

> **状态:方向锚(design note),非已建成、非指令。** 由旁观会话据作者两轮口述整理,供在建会话取舍。
> 关联:[`ROADMAP.md`](ROADMAP.md) P3/P6 · [`SPEC_FORMAT.md`](SPEC_FORMAT.md)(`dynamics`) · [`OBSERVER_NOTES.md`](OBSERVER_NOTES.md) · [`DEMANDS.md`](DEMANDS.md)。

## 0. 框定:长程推演,不是博弈
作者用"sequential game"只是 **analogy**,本意是 **long-horizon rumination —— 帮人想得比脑子能盘的更远**(把前瞻外包给工具)。严格说这是**序贯决策过程(MDP / 决策树)**,不是双人博弈——要的是 rollout 与 policy,不是 minimax/纳什。
唯一让"game"诚实成立的方式:把不确定性/扰动塑造成**对抗性的"自然"**(最坏情况 / 鲁棒规划,"你 vs 最坏的天意")——对运营求稳健有用。**要么走 MDP,要么走 robust-game,别两边糊着。**

## 1. 核心架构判断(分界线):LLM=编译器,引擎=确定性执行器
> 这一刀切对了,就是"可审计的决策参考"与"很会说的预测机"的分界。

LLM **不编未来**(幻觉之源),只把"人话 policy"**编译成引擎能转的旋钮**;真正跑数的是透明、确定、可复现的引擎。**numbers 永远来自引擎,不来自 LLM。**

```
人话 policy → [LLM 编译] → policy IR →(给人 看/改/确认)→ [确定性引擎执行]
              → 结构化结果(轨迹/越限/verdict/敏感性)→ [LLM 解释结果 + 标承重假设]
```
LLM 在两头(译进来、讲出去)夹一个确定性内核,中间一道**人确认闸**,引擎是数字的唯一真相源。

## 2. 结构件:有类型的 policy IR(keystone)
别 NL 直接→"仿真";中间夹一层 **schema 校验的 policy IR**。LLM 的活是 `NL → IR`,引擎执行 IR。草图:

```jsonc
{
  "horizon": 24,
  "target": { "entity": "station", "attr": "pressure" },        // 推演要盯/要稳的量
  "rules": [                                                     // 决策规则:条件 → 动作(可复用的"打法")
    { "when": { "attr": "pressure", "op": ">=", "value": 9 },
      "do":   { "action": "shift", "attr": "throughput", "by": -0.15 },  // 旋钮=setpoint 下移 15% 跨度
      "note": "压力进警戒 → 渐进减流" }
  ],
  "events": [ { "at_frame": 6, "action": "pulse", "attr": "pressure", "by": -0.2 } ], // 一次性冲击(可选)
  "assumptions": { "model": "mean_revert", "rate": 0.25, "volatility": 0.08 } // 推演所凭动力学——必须随结论披露
}
```
- IR 是**契约**:让翻译可校验、让仿真确定。`assumptions` 块是诚实的承重件(见 §5)。
- 动作词(`shift`/`pulse`/…)对齐既有仿真引擎([`simulation.py`](../backend/app/simulation.py))的干预原语,**领域无关**。

## 3. 人确认闸(= P6 模式套到 policy 上)
LLM 把编译出的 IR **明着摆出来、可编辑、要用户确认,再执行**。这样 LLM 译错了,是一个**看得见、改得动**的步骤,而不是藏在结果里的雷。
这正是 roadmap P6"生成式 workflow + 用户确认"的同一模式 —— 架构自洽,值得共用一套确认 UI。

## 4. v1 做"策略对比",不是"策略优化"
- 让用户**自己写 2–3 条候选操作规则**(他的 playbook),引擎把每条在不确定性下各 roll 一遍,**比谁更扛**(越限率 / 终值 / 最坏情况)。
- 这就是作者要的 **"for reference / guideline"——参考,不是机器替他拍板**;也正是运营最想要的:**压测我自己的打法**。
- 机器**搜索/推荐"最优 policy"**是信任雷区(会很自信地推一个"玩具模型下最优"方案)→ **往后放**;真做也得套"在所述假设下最优 + 敏感性"。
- **UX 别让决策树爆炸**:比较几条**具名 policy**,不铺开所有分支。决策有用的产物是"哪条规则扛得住",不是一棵指数树。

## 5. 诚实:叠甲是承重件,不是仪式
- 叠甲 ≠ 加更多免责话(会被无视、像 CYA)。是**具体且承重**那一句:**"这结论吊在假设 X 上;X 错了,推荐就翻"**。给**敏感性**:换一组假设/动力学,排名还稳吗?跨假设都稳的指南才可信。
- **"理由"必须长在确定性跑出来的结果上**:引擎出结构化结果,LLM 只**解释已经算出来的** + 解释自己的翻译选择,**绝不替 numbers 编**。把 LLM 摁在确定性真相的**下游**。
- 全程标注**"确定性合成示意 · 非实测"**;policy 输出额外标**"在 IR.assumptions 下推得"**。

## 6. 小本地模型可用性(qwen3-8b / gemma-12b-qat)
**正因为 IR 是窄 schema,小模型才扛得住**(填紧 schema 还行,开放推理就拉胯)。typed IR 不只为诚实,也是让小模型可用的前提:给 LLM 套 **structured-output / grammar 约束**输出 IR,失败则回退到"手填 IR"表单(NL 翻译只是加速器,不是必经路径)。

## 7. 不要做(anti-goals,防止变漂亮的空壳)
- ❌ 黑箱直接吐"最优操作建议"(没有可见 IR、没有确认闸)。
- ❌ LLM 生成 numbers / 轨迹 / "理由"脱离引擎实算。
- ❌ 指数级决策树铺给用户看。
- ❌ 通用叠甲糊一段(叠甲疲劳 = 等于没叠)。
- ❌ 把"玩具动力学下推出的 policy"呈现得像实测运营指南。

## 8. 与现状的接缝
- 建在已落地的 **P3 仿真 + spec `dynamics`** 之上:单发 what-if → 多规则序贯 rollout 是**扩展**,非重写;`verdict` 是 policy 评估的种子。

> **实现状态(P3.5,已落地确定性内核)**:`backend/app/policy.py`(闭环 rollout + 公共随机数对比 + 敏感性)+ `backend/app/policy_routes.py`(**有类型的 policy IR** = Pydantic `When/Do/Rule/Policy`,即本文 §2 的契约)+ `POST /api/policy/{id}`;前端 `frontend/src/PolicyView.tsx`「🧭 策略对比」tab(规则编辑器 + 对比图 + 鲁棒性表 + 敏感性横幅)。
>
> **实现状态(P6,§1 LLM 编译器 + §3 人确认闸已落地)**:`backend/app/llm_client.py`(本地 LLM,**结构化输出 json_schema** 把 NL 编译成 IR;严格校验:非法 op/动作丢弃、`by` 钳位、**非有限值/越界触发剔除**、剥 `<think>`/代码栅栏;失败可观测、不假装)+ `backend/app/compile_routes.py`(`POST /api/compile/{id}` 只**返回 IR 不执行** + `GET /api/llm/health`)。前端:策略编辑器顶部的「🗣️ 用人话写打法」框 → 编译出的 IR **落成一张可改、标了 🤖 LLM 译 provenance 的候选策略卡** → 人核对/改/删。
>
> **确认闸的语义(诚实说明)**:这里被"执行"的只是**可逆、无副作用的确定性对比**(跟手改任一规则一样即时重算),所以确认闸是"**可见 + 可编辑 + 标注来源**"的事后形态,而非阻断式的预执行闸——后者只在有**不可逆副作用**(如落盘改 spec、对外动作)时才必需(对应 P6 的 spec 构建/SPI browser-ops)。**§4「策略对比非优化」「numbers 只来自引擎」全程守住;LLM 译错是一张看得见、改得动的卡,不是藏在数字里的雷。** 已对 `qwen3-8b`/`gemma-12b-qat` live 跑通(印证 §6:窄 schema 让小模型可用)。
- 与 **P6** 共用"生成式 + 人确认"模式与 UI。
- 学习密度:DSL/IR 设计、structured-output、human-in-the-loop、序贯决策/rollout/鲁棒规划 —— 对 for-fun/学习目的汁水极足。

---
*—— 设计笔记。这是给在建会话的方向锚,不是指令;建造的人说了算。*
