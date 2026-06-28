"""Nexus metric read API (METRIC_nexus_reality Phase A). M0 serves the BASELINE LADDER — the bar a lens
must beat — plus the link sweep and negative controls. All deterministic/offline (no LLM). The full
3-lens metric + nexus_confidence lands at /api/nexus/{a}/{b} once the lenses (M1/M2) clear the bar."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .data_package import load_source
from .nexus_eval import discrimination_sweep, negative_controls, run_baseline_ladder
from .nexus_lens_sem import run_sem_lens
from .nexus_xdom_align import run_alignment, run_alignment_eval
from .nexus_xdom_calibrate import run_calibration, run_effect_sweep
from .nexus_xdom_eval import run_convergence
from .nexus_xdom_gate import run_gate
from .nexus_xdom_view import bridge_view, fdr_extinction_check

nexus_router = APIRouter(prefix="/api/nexus", tags=["nexus"])
# Phase-B cross-domain substrate lives under its own prefix (it is a different, two-domain experiment).
nexus_xdom_router = APIRouter(prefix="/api/nexus_xdom", tags=["nexus_xdom"])

_CAVEAT = ("Phase A = 跨源 link 原型(单域多源),非跨域 nexus。M0 只给『笨 baseline 阶梯』作标杆;"
           "诚实发现:time-coincidence 在本 substrate 各 link/脏度均近天花板(真桥按构造即时间巧合),"
           "故 lens 仅在引入『时间不可分的硬负例』后才有空间(见 METRIC §8)。")


def _require_source(source_id: str) -> None:
    if load_source(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")


@nexus_router.get("/{source_id}/baselines")
def baselines(source_id: str, link: int = 4, dirt: float = 0.0) -> dict:
    _require_source(source_id)
    return {**run_baseline_ladder(source_id, link=link, dirt=dirt), "caveat": _CAVEAT}


@nexus_router.get("/{source_id}/sweep")
def sweep(source_id: str, dirt: float = 0.0) -> dict:
    _require_source(source_id)
    return {**discrimination_sweep(source_id, dirt=dirt), "caveat": _CAVEAT}


@nexus_router.get("/{source_id}/controls")
def controls(source_id: str, link: int = 4, dirt: float = 0.0) -> dict:
    _require_source(source_id)
    return {**negative_controls(source_id, link=link, dirt=dirt), "caveat": _CAVEAT}


@nexus_router.get("/{source_id}/sem")
def sem_lens(source_id: str) -> dict:
    """M1: the time-free SEMANTIC lens (I_sem + ΔL/Kraft). The honest positive — wins L1–L3/L5, beats the
    naive-string baseline under dirtiness (dealias robustness), and concedes L4 (below chance)."""
    _require_source(source_id)
    return {**run_sem_lens(source_id), "caveat": _CAVEAT}


@nexus_xdom_router.get("/gate")
def xdom_gate() -> dict:
    """Phase-B §6c PRE-REGISTRATION gate (channel-blind): an oracle recovers the cross-domain coupling while
    time/depth/string baselines are ~chance — so the difficulty is real before any channel scorer exists."""
    return run_gate()


@nexus_xdom_router.get("/channels")
def xdom_channels() -> dict:
    """Phase-B.1: the two independent channels (shape = timeseries, fingerprint = SQL attrs) + the honest
    convergence verdict on HELD-OUT seeds. The headline is a faithful near-miss: both clear the power floor
    and are independent with a rewire-collapse, but convergence falls just short of the +0.05 clean-2/2 bar."""
    return run_convergence()


@nexus_xdom_router.get("/view")
def xdom_view(seed: str = "xe-0") -> dict:
    """Per-bridge nexus_confidence for ONE coupled package — the data the galaxy-collision visual renders.
    GLOW = Fisher-combined p over BH-FDR (absolute significance + multiple-comparison control, §13 fix);
    only FDR-significant bridges light (high), the rest are ghosts — a zero-coupling pair extinguishes."""
    return bridge_view(seed)


@nexus_xdom_router.get("/fdr_check")
def xdom_fdr_check(seeds: int = 30) -> dict:
    """OBSERVER §13 verification: the glow must EXTINGUISH on a zero-coupling pair. Tiers the real package
    vs a zero pair (this A × an unrelated B) over N seeds — the fix works iff zero-pair high ≈ 0 while real
    high > 0 (the old relative top-decile gave ~8.27 for BOTH)."""
    return fdr_extinction_check([f"xe-{i}" for i in range(max(1, min(seeds, 60)))])


@nexus_xdom_router.get("/align")
def xdom_align(seed: str = "xe-0") -> dict:
    """Sinkhorn alignment for ONE package — the iteration sequence (residual + transport snapshots) the
    animated 'money moment' scrubs: the galaxies pull together as the residual converges, true bridges
    ignite by transport mass. Animation == real alignment replay (DESIGN_visual_fusion §2)."""
    return run_alignment(seed)


@nexus_xdom_router.get("/align_eval")
def xdom_align_eval() -> dict:
    """Does the OT transport (global assignment + mutual exclusivity) recover the coupling better than the
    per-bridge channels? Measured AUC of transport vs each single channel."""
    return run_alignment_eval()


@nexus_xdom_router.get("/calibrate")
def xdom_calibrate(conv_seeds: int = 60) -> dict:
    """Track 1 (§4b): calibrate the substrate's OBSERVABLE marginals to REAL data (sklearn breast_cancer,
    aggregates only), verify on held-out moments, then re-run the gate + 3-way convergence. The honest
    external-validity test — `verdict` reports survive vs collapse. conv_seeds limits the held-out seed
    count for API latency (offline/tests use the full set)."""
    return run_calibration(conv_seeds=conv_seeds)


@nexus_xdom_router.get("/calibrate_sweep")
def xdom_calibrate_sweep(conv_seeds: int = 40) -> dict:
    """The honest robustness curve: 3-way convergence margin vs the coupling's relative effect size under
    real-calibrated marginal noise — locates the survive↔collapse boundary (and where the frozen design's
    clean SNR sits relative to it)."""
    return run_effect_sweep(conv_seeds=conv_seeds)
