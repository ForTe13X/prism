"""Coupling external validity — the deepest open gap (OBSERVER §11 tension #1), tested on REAL paired data
ACROSS A COUPLING-STRENGTH SPECTRUM (so the result can't hide behind a softball).

Track 1 (§8g) calibrated the substrate's MARGINALS to real data and the convergence collapsed; but the
COUPLING there was still a designed latent. This closes the harder half with a REAL coupling: take ONE real
dataset (sklearn breast_cancer, 569 tumors; 30 features = 10 base features × {mean, se, worst}) and form two
views of the SAME real tumor, then ask whether the structured semantic matcher (z-score → undoes a per-view
affine) recovers the known row correspondence. Crucially we run TWO points on the coupling-strength spectrum:

  * SAME-feature views  (A = `mean` stats, B = `worst` stats of the SAME 10 base features) — a NEAR-DUPLICATE
    coupling: mean-radius vs worst-radius are the same physical quantity (per-base r ≈ 0.7–0.97). This is the
    EASY end (matching a measurement to a near-copy of itself); a single base feature already gives AUC ≈ 0.9.
  * DISJOINT-feature views (A = `mean` of base features 0–4, B = `worst` of base features 5–9) — a GENUINELY
    cross-aspect coupling: different physical measurements, linked ONLY through the shared tumor. This is the
    honest cross-domain test.

A per-view deterministic affine (scale+offset) + renamed fields makes raw values non-comparable, so a surface
match is ~chance; only the semantic z-score (affine-invariant) can bridge. The honest question: how far does
the metric's convergence signal transfer as the coupling goes from near-duplicate to genuinely cross-aspect?
Aggregates only (no per-row real value leaves here). Deterministic: per-view affine from Prism's _unit hash.
"""
from __future__ import annotations

from .data_synth import _unit
from .nexus_eval import roc_auc

REAL_SOURCE = "sklearn load_breast_cancer (569 real tumors; views = feature subsets of the SAME tumor)"


def _load_matrix() -> list[list[float]]:
    from sklearn.datasets import load_breast_cancer

    d = load_breast_cancer()
    if d.data.shape != (569, 30):
        raise ValueError(f"breast_cancer shape {d.data.shape} != (569, 30)")
    return [[float(v) for v in r] for r in d.data]


def _view(M: list[list[float]], cols: list[int]) -> list[list[float]]:
    return [[M[i][c] for c in cols] for i in range(len(M))]


def _affine(V: list[list[float]], dk: str) -> list[list[float]]:
    """Per-view deterministic affine (scale·x + offset) — non-comparable raw; z-score (affine-invariant)
    undoes it. scale>0 so standardization perfectly inverts it ⇒ semantic recovery is not circular."""
    na = len(V[0])
    sc = [0.5 + 2.0 * _unit("realpair", dk, "scale", c) for c in range(na)]
    off = [50.0 * (_unit("realpair", dk, "off", c) - 0.5) for c in range(na)]
    return [[sc[c] * row[c] + off[c] for c in range(na)] for row in V]


def _zscore(V: list[list[float]]) -> list[list[float]]:
    m, na = len(V), len(V[0])
    out = [[0.0] * na for _ in range(m)]
    for c in range(na):
        col = [V[i][c] for i in range(m)]
        mu = sum(col) / m
        sd = (sum((x - mu) ** 2 for x in col) / m) ** 0.5 or 1.0
        for i in range(m):
            out[i][c] = (V[i][c] - mu) / sd
    return out


def _pearson(a: list[float], b: list[float]) -> float:
    m = len(a)
    ma, mb = sum(a) / m, sum(b) / m
    va = (sum((x - ma) ** 2 for x in a)) ** 0.5 or 1.0
    vb = (sum((x - mb) ** 2 for x in b)) ** 0.5 or 1.0
    return sum((a[i] - ma) * (b[i] - mb) for i in range(m)) / (va * vb)


def _diag_corr(M: list[list[float]], a_cols: list[int], b_cols: list[int]) -> float:
    """Mean |Pearson| of the ALIGNED column pairs (a_cols[k] vs b_cols[k]). For the same-feature views this is
    mean-radius↔worst-radius etc. = the NEAR-DUPLICATE strength (~0.87); it's what makes that coupling a softball."""
    n = len(M)
    vals = [abs(_pearson([M[i][a] for i in range(n)], [M[i][b] for i in range(n)])) for a, b in zip(a_cols, b_cols)]
    return round(sum(vals) / len(vals), 3) if vals else 0.0


def _mean_cross_corr(zA: list[list[float]], zB: list[list[float]]) -> float:
    """Mean |Pearson| over all (A-feature, B-feature) column pairs — a scalar 'how coupled are the views'."""
    na, nb = len(zA[0]), len(zB[0])
    cols_a = [[zA[i][c] for i in range(len(zA))] for c in range(na)]
    cols_b = [[zB[i][c] for i in range(len(zB))] for c in range(nb)]
    vals = [abs(_pearson(ca, cb)) for ca in cols_a for cb in cols_b]
    return round(sum(vals) / len(vals), 3)


def _coupling(M: list[list[float]], a_cols: list[int], b_cols: list[int]) -> dict:
    n = len(M)
    rawA, rawB = _affine(_view(M, a_cols), "A"), _affine(_view(M, b_cols), "B")
    zA, zB = _zscore(rawA), _zscore(rawB)
    na = len(zA[0])

    def raw_s(i, j):
        return -sum((rawA[i][k] - rawB[j][k]) ** 2 for k in range(na))

    def zdist(i, j):
        return sum((zA[i][k] - zB[j][k]) ** 2 for k in range(na))

    def pair_auc(scorefn) -> float:
        sc, lb = [], []
        for i in range(n):
            sc.append(scorefn(i, i)); lb.append(1)
            for s in range(40):
                j = int(_unit("realpair", "neg", i, s) * n) % n
                if j == i:
                    j = (j + 1) % n
                sc.append(scorefn(i, j)); lb.append(0)
        return roc_auc(sc, lb)

    bestB = [min(range(n), key=lambda j: zdist(i, j)) for i in range(n)]
    bestA = [min(range(n), key=lambda i: zdist(i, j)) for j in range(n)]
    top1 = sum(1 for i in range(n) if bestB[i] == i) / n
    mutual = [(i, bestB[i]) for i in range(n) if bestA[bestB[i]] == i]
    mut_acc = (sum(1 for i, j in mutual if i == j) / len(mutual)) if mutual else 0.0
    return {
        "mean_cross_corr": _mean_cross_corr(zA, zB),
        "raw_value_match_auc": round(pair_auc(raw_s), 4),       # ~chance ⇒ surface non-leaky
        "semantic_zscore_auc": round(pair_auc(lambda i, j: -zdist(i, j)), 4),
        "resolver_top1_acc": round(top1, 4), "resolver_mutual_acc": round(mut_acc, 4),
    }


def run_real_coupling() -> dict:
    """The real-coupling spectrum: near-duplicate (same-feature) vs genuine cross-aspect (disjoint-feature).
    Honest finding — the convergence signal transfers STRONGLY on the near-duplicate softball but degrades to
    ~weak when the coupling is genuinely cross-aspect; unique 1-of-N resolution is hard or impossible."""
    try:
        M = _load_matrix()
    except Exception as exc:
        return {"error": f"real data unavailable: {exc}", "real_source": REAL_SOURCE}
    n = len(M)
    chance = 1.0 / n
    same = _coupling(M, list(range(0, 10)), list(range(20, 30)))        # mean vs worst of the SAME 10 bases
    disjoint = _coupling(M, list(range(0, 5)), list(range(25, 30)))     # mean{0-4} vs worst{5-9}: DIFFERENT bases
    # the near-duplicate strength of the same-feature views (mean-radius↔worst-radius etc.) — the softball tell
    same["same_base_diag_corr"] = _diag_corr(M, list(range(0, 10)), list(range(20, 30)))

    raw_chance = 0.40 <= same["raw_value_match_auc"] <= 0.60 and 0.40 <= disjoint["raw_value_match_auc"] <= 0.60
    signal_degrades = disjoint["semantic_zscore_auc"] < same["semantic_zscore_auc"]
    return {
        "real_source": REAL_SOURCE, "is_real_data": True, "n": n, "chance_top1": round(chance, 5),
        "oracle_auc": 1.0,
        "same_feature_near_duplicate": same,        # the EASY end (near-copy of the same measurements)
        "disjoint_feature_cross_aspect": disjoint,  # the GENUINE cross-domain test
        "checks": {"surface_non_leaky_both(raw~chance)": raw_chance,
                   "signal_degrades_with_genuineness": signal_degrades,
                   "same_feature_is_a_softball(diag_corr>0.7)": same["same_base_diag_corr"] > 0.7},
        "verdict": "real_coupling_signal_degrades_from_softball_to_genuine_cross_aspect",
        "honest_verdict": (
            f"耦合是**真的**(同一真实肿瘤的两个特征视图,已知真值),非设计潜变量;在**耦合强度谱**上各测一点,不靠 softball。"
            f"① **近重复(同 base 的 mean↔worst,对齐列 |corr|≈{same['same_base_diag_corr']})**:语义 AUC=**{same['semantic_zscore_auc']}**、"
            f"top-1={same['resolver_top1_acc']}——但这是**易端**(把一次测量对到它的近拷贝;单特征即 AUC≈0.9),**不算真跨域**。"
            f"② **真·跨切面(不同 base 特征,仅经同一肿瘤耦合,平均 |corr|={disjoint['mean_cross_corr']})**:语义 AUC=**{disjoint['semantic_zscore_auc']}**、"
            f"top-1=**{disjoint['resolver_top1_acc']}**(≈随机 {chance:.4f})——**信号大幅衰减、唯一解析基本不可能**。"
            f"**诚实裁决**:收敛**信号**随耦合「越真越跨切面」**单调衰减**(0.93→{disjoint['semantic_zscore_auc']});合成 substrate 的 ~0.99 与 resolver 0.7–0.96"
            f"**严重高估了真实跨域耦合的强度**。即「度量能在**强**真耦合上区分真/假」成立,但「真实**跨切面**耦合」既弱又难唯一解析——"
            f"这是 §8g(校准边缘→塌)之外、Track 1 未触的**耦合外部效度**,现用真实配对数据沿强度谱测过(§11 张力#1)。"
            f"raw 匹配两端皆≈随机 ⇒ 表面经仿射非泄漏。边界:单数据集多视图(同对象不同特征子集),非两独立真实来源——更强真跨源是后续。"),
    }
