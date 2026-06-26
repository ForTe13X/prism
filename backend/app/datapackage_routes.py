"""Read API for the cross-source data package (DP1). Lets you generate a scenario at given knobs and
inspect the multi-store sample + ground-truth + the deterministic discriminability figures (naive vs
linked vs oracle across link-explicitness and dirtiness). See docs/DESIGN_data_package.md."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .data_package import generate, list_sources
from .data_package_eval import evaluate

datapackage_router = APIRouter(prefix="/api/datapackage", tags=["datapackage"])


@datapackage_router.get("")
def sources() -> dict:
    return {"sources": list_sources()}


@datapackage_router.get("/{source_id}")
def inspect(
    source_id: str,
    dirtiness: float = Query(0.0, ge=0.0, le=1.0),
    link: int = Query(4, ge=1, le=5),
) -> dict:
    """Generate the package at the given knobs and return a inspectable view + the naive/linked/oracle
    scores at those knobs."""
    pkg = generate(source_id, dirtiness=dirtiness, link_explicitness=link)
    if pkg is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    sql = pkg["stores"]["sql"]
    ts = pkg["stores"]["timeseries"]
    return {
        "manifest": pkg["manifest"],
        "stores": {
            "sql": {"warehouses": sql["warehouses"], "carriers": sql["carriers"],
                    "shipments": sql["shipments"]},
            "news": pkg["stores"]["news"],
            "timeseries_sample": {w: s for w, s in list(ts["throughput"].items())},
        },
        "ground_truth": pkg["ground_truth"],
        "corruption_map": pkg["corruption_map"],
        "tasks": pkg["tasks"],
        "evaluate": evaluate(pkg, "explain_delays"),
    }


@datapackage_router.get("/{source_id}/discriminability")
def discriminability(source_id: str) -> dict:
    """The headline research figure: gap (linked − naive) across link-explicitness (clean), and the
    robustness curve (linked vs dirtiness at link=4). Deterministic proxy for the axiom-gain ablation."""
    if generate(source_id) is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    link_sweep = []
    for level in range(1, 6):
        r = evaluate(generate(source_id, dirtiness=0.0, link_explicitness=level))
        link_sweep.append({"link": level, "naive_f1": r["naive_f1"], "linked_f1": r["linked_f1"], "gap": r["gap"]})
    dirt_sweep = []
    for d in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        r = evaluate(generate(source_id, dirtiness=d, link_explicitness=4))
        dirt_sweep.append({"dirtiness": d, "naive_f1": r["naive_f1"], "linked_f1": r["linked_f1"]})
    return {
        "source_id": source_id,
        "link_sweep": link_sweep,
        "dirtiness_sweep": dirt_sweep,
        "note": "确定性判别力探针(naive=字面单源 / linked=跨源时空+实体联结 / oracle=知真值=1.0)。"
                "判别区间在 link≥2(naive 失效、linked 仍可复原);脏度上升 linked 退化=鲁棒性曲线。"
                "诚实边界:确定性骨架只区分 L1(显式键)与 L≥2(非显式)——L2–L5 同分 ~0.8;"
                "更细的 L2→L5 梯度(尤其纯语义 L5)留给后续 LLM/axiom 解题器。"
                "这是 axiom-gain 基准的确定性骨架,LLM-ablation(naive-RAG vs axiom-RAG)是后续。",
    }
