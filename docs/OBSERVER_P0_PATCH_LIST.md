# OBSERVER · P0 诚实债 patch 清单(可直接照做)

> 这是**旁观者**给在建会话的一份**可照做的 patch 清单**,对应 [`OBSERVER_NOTES §15`](OBSERVER_NOTES.md) 的 P0 三连。
> **它是建议,不是指令**:你们决定采不采、怎么改。旁观者**不动你们的代码**,本清单只描述要改哪里、改成什么。
> 行号以建造会话 `30dc53b` / 旁观 `167bfa3` 为准,可能随后续提交漂移——按**字符串**定位最稳。
> 三条都是 **closes 已声明的诚实缺口**(§14 的开口 + caveat-软化的结构性根因),是 §15 里唯一"真该做"的一档。

---

## P0-1 · 在源头修 §13 construct-swap + 双控制回归测试(唯一 MEDIUM)

**问题**:招牌数字 **"8.27→0.03 熄灭"是 construct-swap**。"8.27"是 **rewire 控制**(观测逐字节不变、只打乱真值标签——OBSERVER §13 实测的那个),"0.03"是 **cross-pair 控制**(本 A × 无关 B)。同构造 before→after 其实是 **cross-pair 7.17→0.00**(依然是巨大真胜,根本不用拼)。更要紧:**新规则下 rewire 不熄(~4.27,precision 0),而且这是对的**——rewire 是"有耦合但乱标签",该用 **AUC(§8e,rewire AUC 0.46)**,不是 extinction。两个控制测两种失效,目前**零层披露**。

旁观者已亲验(30 seed,新 `_tier_bridges`):`real 4.267 / cross-pair零 0.000 / rewire零 4.267 (precision 0)`。

### 三处字符串都带这个数,逐一改

**(a) 后端真值源 — `backend/app/nexus_xdom_view.py::fdr_extinction_check`(现 L156–186)**
现在只测 real + cross-pair(`zero_pair`),verdict 末句(L184–185)写 *"the old relative top-decile gave ~8.27 for BOTH"* —— 这正是拼接点。建议让这个函数**同时测两个控制 + 同构造 before**,把"双控制 = 双失效"做成它的返回结构:

```python
def _old_relative_high(bridges) -> int:
    """OLD rule: ≥2/3 of the per-channel relative top-decile _fires (no FDR) — for same-construction 'before'."""
    sh, fp, rl = _scores(bridges)
    votes = [a + b + c for a, b, c in zip(_fires(sh), _fires(fp), _fires(rl))]
    return sum(1 for v in votes if v >= 2)

def fdr_extinction_check(seeds=None) -> dict:
    seeds = seeds or [f"xe-{i}" for i in range(30)]
    real_high, real_prec = [], []
    cross_new, cross_old = [], []          # SAME-construction before/after (unrelated A×B)
    rewire_new, rewire_prec = [], []       # the AUC control (identical obs, labels permuted)
    for sd in seeds:
        gA = generate_xdom(sd); null = _null_pools(sd)
        rb, _ = candidate_bridges_xdom(gA); _, rt = _tier_bridges(rb, null, FDR_Q)
        rhi = [i for i, t in enumerate(rt) if t == "high"]; real_high.append(len(rhi))
        if rhi: real_prec.append(sum(rb[i]["y"] for i in rhi) / len(rhi))
        # cross-pair zero: this A × an unrelated B — the no-nexus pair; NEW (FDR) vs OLD (relative)
        gB = generate_xdom(f"{sd}~zero"); zx = {"A": gA["A"], "B": gB["B"], "coupling": [], "seed": sd}
        zb, _ = candidate_bridges_xdom(zx); _, zt = _tier_bridges(zb, null, FDR_Q)
        cross_new.append(sum(1 for t in zt if t == "high")); cross_old.append(_old_relative_high(zb))
        # rewire zero: identical observations, only labels permuted — the AUC failure mode (§8e)
        wb, _ = candidate_bridges_xdom(gA, coupling=rewired_coupling(gA)); _, wt = _tier_bridges(wb, null, FDR_Q)
        whi = [i for i, t in enumerate(wt) if t == "high"]; rewire_new.append(len(whi))
        if whi: rewire_prec.append(sum(wb[i]["y"] for i in whi) / len(whi))
    n = len(seeds); avg = lambda xs: round(sum(xs) / len(xs), 3) if xs else None
    return {
        "seeds": n, "fdr_q": FDR_Q,
        "real_pair_mean_high": avg(real_high), "real_pair_high_precision": avg(real_prec),
        # extinction control (unrelated domains), measured SAME-construction:
        "cross_pair_old_mean_high": avg(cross_old), "cross_pair_new_mean_high": avg(cross_new),
        "extinguishes_on_cross_pair": (sum(cross_new) / n) < 1.0,
        # AUC control (rewire): SHOULD stay lit — extinction is the wrong tool here:
        "rewire_new_mean_high": avg(rewire_new), "rewire_high_precision": avg(rewire_prec),
        "verdict": (
            "Extinction is measured SAME-CONSTRUCTION on the cross-pair null (unrelated A×B): "
            f"old relative rule ≈{avg(cross_old)} high → new FDR ≈{avg(cross_new)} high ⇒ extinguishes. "
            f"The REWIRE control (identical observations, labels permuted) stays ≈{avg(rewire_new)} high at "
            f"precision ≈{avg(rewire_prec)} under the new rule — AND SHOULD: rewire keeps the coupling signal "
            "and only randomizes truth, so it is an AUC failure mode (§8e, rewire AUC ≈0.46), not a no-nexus "
            "pair; extinction is the wrong tool for it. Two controls, two failure modes."),
    }
```
> 关键:**"before"用同构造 cross-pair 的旧规则数(~7.17),不再借 rewire 的 8.27**;并把 rewire 作为**显式 AUC 控制**返回(~4.27 不熄,且诚实标注"这是对的")。

**(b) 前端卡 ② — `frontend/src/NexusView.tsx` L309**
当前:
```
<b>零耦合对现在熄灭</b>(实测「高」桥 8.27→<b>0.03</b>,精度 0.66→<b>0.96</b>)…
```
改为(同构造 + 双控制一句):
```
<b>无关域对现在熄灭</b>(同构造实测:无关 A×B 的「高」桥 7.17→<b>0.00</b>,真桥精度 0.66→<b>0.96</b>);
rewire 控制(同观测、只乱标签)新规则下仍 ~4.27 <b>不熄且应当不熄</b>——那是 AUC 的活(§8e,rewire AUC 0.46),非 extinction 的活。两个控制测两种失效。
```

**(c) README — `README.md` L44**
把 "零对**熄灭**(8.27→0.03)" 改为 "无关域对**熄灭**(同构造 7.17→0.00;rewire 控制不熄=AUC 失效,非 extinction)"。

**(d) `docs/METRIC_nexus_reality.md §8h`** 同步:头条数字改同构造 cross-pair 7.17→0.00,加"双控制=双失效"一段。

### 加回归测试(锁死 construct + 双控制)
`backend/tests/test_nexus_xdom_view.py` 新增:
```python
def test_two_controls_measure_two_failures():
    r = fdr_extinction_check([f"xe-{i}" for i in range(20)])
    assert r["cross_pair_new_mean_high"] < 0.5                       # 无关域对熄灭
    assert r["cross_pair_old_mean_high"] > 3.0                       # 同构造 before 确实高(证明是真修复)
    assert r["rewire_new_mean_high"] > r["cross_pair_new_mean_high"] + 2.0   # rewire 仍亮(AUC 失效)
    assert (r["rewire_high_precision"] or 0.0) < 0.1                 # rewire 亮的几乎全是假
```

---

## P0-2 · 把丢掉的 caveat 还回用户面

**(a) 卡 ③ 补"单数据集多视图"边界 — `NexusView.tsx` L314 / L329**
后端 `nexus_real_pair.py` L160 已诚实写了边界,但前端卡 ③ 的标题"两面**都用真实数据测过**"和 L329"两面外部效度都用真实数据探过"**把这层省了**。复用后端原话补一句(不动数字,它们是 live-wired):
- L320 (b) 行尾或 L329 选型含义里插入:
  ```
  (真实配对数据=同一肿瘤的两特征视图——<b>单数据集多视图,非两独立真实来源</b>;更强真跨源是后续。)
  ```

**(b) 卡 ② 加天花板 + is-caveat — `NexusView.tsx` L292**
卡 ②(`<div className="pr-ag-plain-card">`,**唯一没 is-caveat 的卡**)扛着头条胜("3-way 稳过""熄灭""精度 0.66→0.96"),视觉占主导;停在卡 ② 没翻到卡 ③ 的人会过读。两选一(建议都做):
- 加 `is-caveat`:`<div className="pr-ag-plain-card is-caveat">`;
- 卡 ② 顶部加一行天花板横幅:
  ```
  ⚠ 受控合成 substrate;可恢复信号集中在<b>单一数值通道</b> ⇒ 共指基准、非收敛难度测试;真实校准下塌(见 ③)。
  ```
> 目的:**这张胜利卡永不脱离它的天花板单独渲染**。

**(c) de-stale 路由 docstring — `backend/app/nexus_routes.py` L69–70**
当前自相矛盾(docstring 说"差一点过 2/2",live outcome 是"3-way 稳过"):
```
... but convergence falls just short of the +0.05 clean-2/2 bar.
```
改为:
```python
    """3 independent channels (shape⊥fingerprint⊥relational) on held-out seeds: 3-way convergence
    margin CI is entirely >0.05 ⇒ clears, with a rewire-collapse control. CEILING: this is the FROZEN
    SYNTHETIC substrate and all recoverable signal lives in ONE numeric channel ⇒ a coreference
    benchmark, NOT a difficulty-calibrated convergence test; real-data marginal calibration COLLAPSES
    it (§8g, /api/nexus_xdom/calibrate). A capped exploration result, not a validated discovery."""
```

---

## P0-3 · 用测试锁住 caveat 文字(根治"数字锁了、文字能软化")

**根因**:数字 live-wired + test-locked,但 **caveat 文字没有任何测试守**;`NexusView.tsx`/`AxiomGainView.tsx` 从不被 render 测 ⇒ 将来一次"精简文案"可删掉"判不定/非生产证据/N\*=∞/塌"而 CI 全绿。已实际漂移两处(P0-1/P0-2)即证。

**(a) 后端诚实不变量(零新依赖,先做这个)— `backend/tests/test_honesty_invariants.py`**
直接打各 summary 端点/纯函数,断言**必带的诚实词元在场**(守"在场",不证"正确"——是绊线不是证明):
```python
from app.nexus_xdom_calibrate import run_calibration
from app.nexus_real_pair import run_real_coupling
from app.axiom_gain_protocol import run_protocol
from app.nexus_xdom_view import fdr_extinction_check

def test_collapse_endpoint_keeps_its_caveat():
    v = run_calibration(conv_seeds=20)
    assert "collapses" in v["verdict"]                     # 塌缩判定在场

def test_real_coupling_keeps_single_view_boundary():
    s = str(run_real_coupling())
    assert "单数据集多视图" in s and "非两独立真实来源" in s    # 边界不许丢

def test_protocol_keeps_amortization_negative():
    p = str(run_protocol("logistics_demo"))
    assert "N*" in p or "∞" in p or "合成" in p              # N*=∞ / 合成 caveat 在场

def test_extinction_discloses_both_controls():
    r = fdr_extinction_check([f"xe-{i}" for i in range(12)])
    assert "rewire" in r["verdict"].lower() and "auc" in r["verdict"].lower()  # 双控制披露在场
```
> 新增一个结果端点时,这文件强制你顺手声明它的 caveat 词元。

**(b) 前端 render 级(需补 devDep)— `NexusView.test.tsx` + `AxiomGainView.test.tsx`**
现状:`frontend/package.json` 有 `vitest ^2.1.9`,**无 `@testing-library/react` / `jsdom`**(现仅 `widgets.test.tsx` 一个、多为纯函数)。两条路:
- **正路**:加 devDep `@testing-library/react` + `jsdom`,`vitest.config` 设 `environment: 'jsdom'`,mock `api.ts` 的 fetcher,断言 caveat **短语**在 DOM(非数字——数字归 API 锁):
  ```tsx
  // NexusView.test.tsx
  it("card ③ keeps the collapse + single-view + non-production caveats", async () => {
    render(<NexusView />);            // api mocked
    const el = await screen.findByText(/塌|判不定/);
    expect(el).toBeTruthy();
    expect(screen.getByText(/非生产证据/)).toBeTruthy();
    expect(screen.getByText(/单数据集多视图|非两独立真实来源/)).toBeTruthy();
  });
  it("the win card never renders without a ceiling (is-caveat count >= 3)", () => {
    const { container } = render(<NexusView />);
    expect(container.querySelectorAll(".is-caveat").length).toBeGreaterThanOrEqual(3); // 卡②也加了 is-caveat 后
  });
  ```
- **零依赖回退**(不想加 devDep 时):写一个 vitest 直接**读源文件文本**断言短语在场(`readFileSync('src/NexusView.tsx')` → `expect(src).toContain('非生产证据')`)。糙,但能挡掉"误删 caveat 文案",且零新依赖。

---

## Definition of done(照做完应满足)
- [ ] `fdr_check` 端点返回 `cross_pair_new_mean_high`(~0)、`rewire_new_mean_high`(~4.27)、`rewire_high_precision`(~0),verdict 含双控制说明;**全仓再无 "8.27→0.03" 串**(后端 verdict / NexusView L309 / README L44 / METRIC §8h 全改同构造)。
- [ ] 卡 ③ 含"单数据集多视图,非两独立真实来源";卡 ② 带天花板横幅且(建议)is-caveat;`/channels` docstring 与 live outcome 一致且带天花板。
- [ ] `test_two_controls_measure_two_failures` + `test_honesty_invariants.py` 通过;(选)前端 render 测通过。
- [ ] 验证命令:`cd backend && python -m pytest -q`(应仍全绿 + 新测);`cd frontend && npm test`。

---
*—— 旁观者 patch 清单。这是给在建会话的方向锚,不是指令;改不改、怎么改,建造的人说了算。*
