"""Read API for the §5 agentic parser: generate a package → render it messy → parse it back, and report
the round-trip recovery + the observable failure report. See backend/app/parser.py + raw_render.py."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .data_package import generate
from .parser import parse_package
from .raw_render import render_package

parse_router = APIRouter(prefix="/api/parse", tags=["parse"])


@parse_router.get("/{source_id}")
def parse(source_id: str, dirtiness: float = Query(0.0, ge=0.0, le=1.0), link: int = Query(2, ge=1, le=5)) -> dict:
    pkg = generate(source_id, dirtiness=dirtiness, link_explicitness=link)
    if pkg is None:
        raise HTTPException(status_code=404, detail=f"data source not found: {source_id}")
    rendered = render_package(pkg)
    parsed = parse_package(rendered)

    def recov(truth_ids: set, got_ids: set) -> float:
        return round(len(truth_ids & got_ids) / max(1, len(truth_ids)), 3)

    sql = pkg["stores"]["sql"]
    recovery = {
        "warehouse_id": recov({w["id"] for w in sql["warehouses"]},
                              {w["id"] for w in parsed["entities"]["warehouses"]}),
        "shipment_id": recov({s["id"] for s in sql["shipments"]},
                             {s["id"] for s in parsed["entities"]["shipments"]}),
        "news_id": recov({n["id"] for n in pkg["stores"]["news"]},
                         {n.get("id") for n in parsed["entities"]["news"]}),
    }
    return {
        "source_id": source_id, "dirtiness": dirtiness, "link_explicitness": link,
        "summary": parsed["summary"], "reports": parsed["reports"], "id_recovery": recovery,
        "raw_preview": {k: v[:280] for k, v in rendered["raw"].items()},
        "sample": {"shipments": parsed["entities"]["shipments"][:3], "news": parsed["entities"]["news"][:2]},
        "note": "render→parse 往返:确定性启发式解析器把脏的异构原文还原成结构化行(带 provenance + 置信 + 可观测失败)。"
                "LLM-aug 语义抽取(乱码恢复 / 别名归一)是后续 fixture 化扩展。",
    }
