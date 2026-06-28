"""OBSERVER §15 P0-3 — honesty invariants: numbers are live-wired + test-locked, but the CAVEAT TEXT had no
guard, so it could be silently softened (it drifted twice — the stale /channels docstring, the §13 construct-
swap). These tests assert the load-bearing caveat TOKENS are PRESENT on each result surface (a tripwire that
guards presence, not correctness). Adding a new result endpoint forces you to declare its caveat token here."""
from __future__ import annotations

import pytest

sklearn = pytest.importorskip("sklearn")  # calibration + real-coupling need genuine real data

from backend.app.axiom_gain_protocol import run_protocol
from backend.app.nexus_real_pair import run_real_coupling
from backend.app.nexus_xdom_calibrate import run_calibration
from backend.app.nexus_xdom_view import fdr_extinction_check


def test_collapse_endpoint_keeps_its_caveat():
    v = run_calibration(gate_seeds=20, conv_seeds=20)
    assert "collapses" in v["verdict"]                                  # the Track-1 collapse verdict must stay


def test_real_coupling_keeps_single_view_boundary():
    s = str(run_real_coupling())
    assert "单数据集多视图" in s and "非两独立真实来源" in s              # the §8j boundary must not be dropped


def test_protocol_keeps_amortization_negative_and_synthetic_caveat():
    p = str(run_protocol("logistics_demo"))
    assert ("N*" in p or "∞" in p)                                      # learned-dict break-even N*=∞ (honest negative)
    assert "合成" in p                                                  # small-scale synthetic caveat present


def test_extinction_discloses_both_controls():
    r = fdr_extinction_check([f"xe-{i}" for i in range(12)])
    v = r["verdict"].lower()
    assert "rewire" in v and "auc" in v                                 # dual-control disclosure (no construct-swap)
    assert "cross_pair_new_mean_high" in r and "rewire_new_mean_high" in r
