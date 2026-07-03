"""Phase B nexus substrate GATE (METRIC_nexus_reality §4 Phase B) — pin the pre-channel acceptance test
as a regression-guarded fact, INCLUDING the statistical correction surfaced by adversarial review.

Headlines locked in:
1. On the two-domain (infra × library) co-timed candidate set, the time-coincidence baseline AUC decays
   smoothly from ceiling (jitter=0, time is a sufficient statistic — the Phase A killer) to chance as
   intra-window jitter grows; the band [0.60,0.75] is AUC-reachable at every load.
2. The class-mixing leg must NOT be gated on the worst window (min entropy): that is a worst-of-N order
   statistic that only drops as seeds are added — it PASSES at N=40 and FAILS at N≥80 for the same knob.
   The gate uses CONVERGENT stats (mean entropy + leak-rate). The leak-rate falls monotonically with load;
   the robust class-mixing floor is load≥5 (load=4's ~1.8% leak exceeds the 1% tolerance), and the
   recommended frozen knob is load=6 (leak≈0), NOT the load=4 a 40-seed pool would have suggested.
3. The reported AUC is de-biased: the old per-incident edge-clamp was removed (it crushed outer-class
   jitter tails and inflated AUC ~0.02)."""
from __future__ import annotations

from collections import Counter

from backend.app.data_synth import _unit
from backend.app.nexus_phaseb import (
    DOMAIN_A, DOMAIN_B, ENTROPY_FLOOR_BITS, K_CLASSES, LEAK_RATE_TOL, TIME_AUC_BAND,
    anchors, candidate_bridges, gate_point, gate_sweep,
)

A40 = [f"pb-{i}" for i in range(40)]
A80 = [f"pb-{i}" for i in range(80)]
POOL = [f"pb-{i}" for i in range(200)]  # enough windows (3·200) to estimate the ~1% leak-rate


# --- the joint substrate is well-formed and CHANNEL-BLIND ---
def test_anchors_are_eight_clean_ids_per_side():
    a, b = anchors(DOMAIN_A), anchors(DOMAIN_B)
    assert len(a) == 8 and len(b) == 8
    assert a[0].startswith("CL-") and b[0].startswith("COL-")           # token-disjoint id spaces


def test_bridges_are_channel_blind_and_labelled_by_class():
    a, b = anchors(DOMAIN_A), anchors(DOMAIN_B)
    bridges, per_window = candidate_bridges("pb-0", window_load=6, frame_jitter=14, anchors_a=a, anchors_b=b)
    assert bridges
    allowed = {"seed", "window", "a", "b", "class_a", "class_b", "dframe", "y", "label"}
    for br in bridges:
        assert set(br) == allowed                                       # no news/hub/semantic field leaks in
        assert br["y"] == (1 if br["class_a"] == br["class_b"] else 0)  # real ⇔ same latent class
        assert 0 <= br["window"] < 3
    assert len(per_window) == 3


def test_prevalence_is_one_over_K():
    pt = gate_point(POOL, window_load=6, frame_jitter=14)
    assert abs(pt["prevalence"] - 1.0 / K_CLASSES) < 0.02              # ≈0.25 honest imbalance


# --- THE BLOCKER, pinned: worst-window entropy is an N-unstable order statistic, NOT a valid gate ---
def test_min_entropy_is_an_unstable_order_statistic():
    lo = gate_point(A40, window_load=4, frame_jitter=14)
    hi = gate_point(A80, window_load=4, frame_jitter=14)
    assert lo["min_entropy"] >= ENTROPY_FLOOR_BITS                      # the old artifact: passes at N=40
    assert hi["min_entropy"] < ENTROPY_FLOOR_BITS                       # a class-pure window appears by N=80
    # ...while the CONVERGENT mean is essentially unchanged — that's why the gate uses mean + leak-rate
    assert abs(lo["mean_entropy"] - hi["mean_entropy"]) < 0.05


# --- the leak-rate is convergent & monotone in load; the robust floor is load≥5 ---
def test_leak_rate_monotone_in_load_and_floor_is_load_5():
    leak = {L: gate_point(POOL, window_load=L, frame_jitter=0)["leak_rate"] for L in (2, 3, 4, 5, 6)}
    assert leak[2] > leak[3] > leak[4] > leak[5] >= leak[6]            # falls monotonically with load
    assert leak[4] > LEAK_RATE_TOL                                     # load=4 leaks ~1.8% > 1% tol → reject
    assert leak[5] <= LEAK_RATE_TOL and leak[6] <= LEAK_RATE_TOL       # load≥5 holds the tolerance


def test_mean_entropy_stable_and_at_least_one_bit():
    for L in (2, 3, 4, 5, 6):
        assert gate_point(POOL, window_load=L, frame_jitter=14)["mean_entropy"] >= ENTROPY_FLOOR_BITS
    # convergent (unlike min): the N=40 estimate already matches the N=200 estimate
    assert abs(gate_point(A40, window_load=4, frame_jitter=0)["mean_entropy"]
               - gate_point(POOL, window_load=4, frame_jitter=0)["mean_entropy"]) < 0.05


# --- the MECHANISM: intra-window jitter converts time from sufficient statistic to weak adversary ---
def test_debiased_time_auc_decays_monotonically_with_jitter():
    aucs = [gate_point(A40, window_load=6, frame_jitter=j)["time_auc"] for j in (0, 4, 8, 12, 16, 20)]
    assert aucs[0] == 1.0                                              # jitter=0 ⇒ time perfectly separates
    assert all(x > y for x, y in zip(aucs, aucs[1:]))                  # strictly decreasing
    assert aucs[-1] < 0.65                                             # decays toward chance
    # de-biased: removing the class-asymmetric edge clamp lowered the frozen-knob AUC ~0.02 (was 0.6785)
    assert gate_point(A40, window_load=6, frame_jitter=14)["time_auc"] < 0.68


# --- the corrected GATE VERDICT: reachable, floor load≥5, robust knob load≥6 ---
def test_gate_reachable_with_robust_floor_at_load_ge_5():
    res = gate_sweep(POOL)
    assert res["reachable"] and res["n_accepting"] > 0
    lo, hi = TIME_AUC_BAND
    accepting_loads = sorted({g["window_load"] for g in res["accepting_points"]})
    assert min(accepting_loads) >= 5                                   # corrected; load=4 was a 40-seed artifact
    for g in res["accepting_points"]:
        assert lo <= g["time_auc"] <= hi
        assert g["mean_entropy"] >= ENTROPY_FLOOR_BITS and g["leak_rate"] <= LEAK_RATE_TOL
    # load=4 has AUC in band but is REJECTED for leak-rate (the class-mixing leg, not the time leg, binds it)
    l4 = next(g for g in res["grid"] if g["window_load"] == 4 and lo <= g["time_auc"] <= hi)
    assert not l4["accept"] and l4["leak_rate"] > LEAK_RATE_TOL
    assert res["accepting_points"][0]["window_load"] >= 6             # recommended (lowest-leak) knob is clean


# --- class ⟂ window: constant across windows AND the per-window class marginal stays flat ---
def test_class_assignment_is_independent_of_window():
    a = anchors(DOMAIN_A)
    br, _ = candidate_bridges("pb-3", window_load=6, frame_jitter=8, anchors_a=a, anchors_b=anchors(DOMAIN_B))
    seen: dict[str, int] = {}
    for x in br:
        for side, hub, cls in (("A", x["a"], x["class_a"]), ("B", x["b"], x["class_b"])):
            assert seen.setdefault(f"{side}:{hub}", cls) == cls         # class constant across windows
    assert seen["A:" + a[0]] == int(_unit("pb-3", "class", "A", a[0]) * K_CLASSES) % K_CLASSES  # documented hash


def test_per_window_class_marginal_is_near_uniform():
    # a roster that suppressed class k in window k would leak class↔window even while clearing the entropy
    # floor; the roster ranks by a class-INDEPENDENT hash, so each window's class marginal must stay ≈1/K.
    a, b = anchors(DOMAIN_A), anchors(DOMAIN_B)
    by_window = {w: Counter() for w in range(3)}
    for sd in POOL:
        seen: set = set()
        br, _ = candidate_bridges(sd, window_load=6, frame_jitter=0, anchors_a=a, anchors_b=b)
        for x in br:
            key = (x["window"], x["a"])
            if key not in seen:
                seen.add(key)
                by_window[x["window"]][x["class_a"]] += 1
    for w in range(3):
        tot = sum(by_window[w].values())
        for k in range(K_CLASSES):
            assert abs(by_window[w][k] / tot - 1.0 / K_CLASSES) < 0.05  # no window over/under-represents a class


def test_deterministic():
    assert gate_point(A40, window_load=5, frame_jitter=10) == gate_point(A40, window_load=5, frame_jitter=10)
    assert gate_sweep(A40) == gate_sweep(A40)
