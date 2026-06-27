"""Deterministic heuristic/regex extractor — the agentic-STYLE heterogeneous parser (§5).

Inverse of :mod:`backend.app.raw_render`: it takes the messy, heterogeneous RAW text blobs (mixed
delimiters/quoting, unit suffixes, blank cells, time-stamped free-text news, noisy throughput dumps)
and reconstructs structured rows/entities — shipments, warehouses, carriers, news, throughput points —
each carrying PROVENANCE (``source`` + ``line`` index) and a CONFIDENCE score, plus an OBSERVABLE
failure report (parsed vs failed counts + reasons).

WELDED DISCIPLINES
  * DETERMINISTIC: pure regex/heuristics over the input text. No ``random``, no clock, NO LIVE LLM CALL.
    Same package → byte-identical parse.
  * CLEAN-ROOM: only Prism's own code; the honesty discipline (provenance + confidence + observable
    failure, never silently drop a row) is a skill carried over, not lifted code.
  * HONEST FAILURE: every input line is accounted for — a line is either parsed (into a typed row) or
    counted as a failure WITH A REASON. Rows are never silently dropped; ambiguous fields lower a row's
    confidence rather than vanishing.

FUTURE EXTENSION (not done here, by design): an LLM-augmented extraction layer for the genuinely
SEMANTIC dirtiness (mojibake recovery, alias→canonical entity resolution from prose, schema inference)
would slot in as a *fixture-backed* stage — the LLM pass pre-baked into a frozen, versioned fixture and
replayed deterministically at parse time (never a live call), preserving byte-reproducibility. This
module is the deterministic heuristic core that such a layer would sit on top of.
"""
from __future__ import annotations

import re

# Delimiters the renderer may have used. We split on whichever yields the expected column count,
# preferring the most structured — a deterministic disambiguation, not a guess.
_DELIM_CANDIDATES = ["\t", " | ", ";", ",", "|"]

# Unit suffix spellings the renderer appends to a weight. Stripping the suffix recovers the stored
# number; the suffix itself tells us the stored UNIT (kg vs lb) so a downstream layer can normalize.
_KG_TOKENS = ("kg", "千克", "kgs")
_LB_TOKENS = ("lbs", "lb")

_WEIGHT_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z一-鿿]*)\s*$")
# news frame stamp variants emitted by raw_render.render_news
_FRAME_RE = re.compile(r"(?:\[frame\s+(\d+)\]|@F=(\d+)|<t:(\d+)>|FRAME\s+(\d+)\s*::)")
_NEWS_ID_RE = re.compile(r"(NEWS-\d+)")
# throughput point: "t12: 510.9" / "t12=510.9" / "t12 -> 510.9" or a "frame:value" csv cell
_TP_KV_RE = re.compile(r"^t(\d+)\s*(?::|=|->)\s*([0-9]+(?:\.[0-9]+)?)\s*$")
_TP_PAIR_RE = re.compile(r"^(\d+):([0-9]+(?:\.[0-9]+)?)$")

_ID_PREFIXES = {"shipment": "SHP-", "warehouse": "WH-", "carrier": "CR-"}


def _unquote(cell: str) -> str:
    """Strip a CSV-style quote wrapper (and unescape doubled quotes). Surface form only."""
    c = cell.strip()
    if len(c) >= 2 and c[0] == '"' and c[-1] == '"':
        return c[1:-1].replace('""', '"')
    return c


def _split_row(line: str, ncols: int) -> list[str] | None:
    """Split a CSV-ish line into exactly ``ncols`` cells, trying each candidate delimiter and keeping
    the first that yields the right count. Returns None if no delimiter produces ``ncols`` cells —
    that line then becomes an OBSERVABLE failure, never a silent drop."""
    for d in _DELIM_CANDIDATES:
        if d in line:
            parts = [p for p in line.split(d)]
            if len(parts) == ncols:
                return [_unquote(p) for p in parts]
    return None


def _parse_weight(cell: str) -> tuple[float | None, str | None, float]:
    """Parse a weight cell → (value, unit, confidence). Recognizes a trailing unit suffix; an empty or
    unparseable cell yields (None, None, low-confidence)."""
    cell = cell.strip()
    if not cell:
        return None, None, 0.0
    m = _WEIGHT_RE.match(cell)
    if not m:
        return None, None, 0.0
    val = float(m.group(1))
    suffix = m.group(2).strip().lower()
    if not suffix:
        return val, None, 0.7  # number with no unit — recovered, but unit unknown
    if any(suffix.endswith(t) or suffix == t for t in _LB_TOKENS):
        return val, "lb", 1.0
    if any(suffix.endswith(t) or suffix == t for t in _KG_TOKENS):
        return val, "kg", 1.0
    return val, None, 0.6  # number present but unrecognized unit token


def _provenance(source: str, line: int) -> dict:
    return {"source": source, "line": line}


def parse_sql(text: str) -> dict:
    """Parse the messy SQL blob → warehouses / carriers / shipments rows with provenance + confidence.

    Section headers (``### ... ###``) switch the active table; blank lines and the in-blob column
    header are skipped (counted as ``skipped``, not failures). Any data line that won't split into the
    expected column count is a failure with a reason."""
    warehouses: list[dict] = []
    carriers: list[dict] = []
    shipments: list[dict] = []
    failures: list[dict] = []
    skipped = 0
    section = None

    for i, raw_line in enumerate(text.splitlines()):
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            skipped += 1
            continue
        if stripped.startswith("###"):
            low = stripped.lower()
            if "warehouse" in low:
                section = "warehouse"
            elif "carrier" in low:
                section = "carrier"
            elif "shipment" in low:
                section = "shipment"
            else:
                section = None
            skipped += 1
            continue
        # the shipments in-blob column header line (starts with an id-less header token)
        if section == "shipment" and _ID_PREFIXES["shipment"] not in stripped and "id" in stripped.lower():
            skipped += 1
            continue

        if section == "warehouse":
            cells = _split_row(line, 4)
            if cells is None or not cells[0].startswith(_ID_PREFIXES["warehouse"]):
                failures.append({**_provenance("sql", i), "reason": "warehouse row: bad column split or missing id", "raw": stripped})
                continue
            warehouses.append({
                "id": cells[0], "region": cells[1], "port": cells[2], "name": cells[3],
                "_provenance": _provenance("sql", i), "_confidence": 1.0,
            })
        elif section == "carrier":
            cells = _split_row(line, 2)
            if cells is None or not cells[0].startswith(_ID_PREFIXES["carrier"]):
                failures.append({**_provenance("sql", i), "reason": "carrier row: bad column split or missing id", "raw": stripped})
                continue
            carriers.append({
                "id": cells[0], "name": cells[1],
                "_provenance": _provenance("sql", i), "_confidence": 1.0,
            })
        elif section == "shipment":
            cells = _split_row(line, 6)
            if cells is None or not cells[0].startswith(_ID_PREFIXES["shipment"]):
                failures.append({**_provenance("sql", i), "reason": "shipment row: bad column split or missing id", "raw": stripped})
                continue
            conf = 1.0
            try:
                frame = int(cells[3])
            except ValueError:
                # frame unrecoverable but row otherwise fine → keep the row, lower confidence
                frame, conf = None, min(conf, 0.5)
            weight, unit, wconf = _parse_weight(cells[4])
            conf = min(conf, wconf if weight is not None else 0.5)
            status_cell = cells[5].strip()
            status = status_cell if status_cell else None  # blank cell → missing (observed honestly)
            if status is None:
                conf = min(conf, 0.6)  # missing field lowers confidence, doesn't drop the row
            shipments.append({
                "id": cells[0], "warehouse_id": cells[1], "carrier_id": cells[2],
                "dispatch_frame": frame, "weight": weight, "unit": unit, "status": status,
                "_provenance": _provenance("sql", i), "_confidence": round(conf, 3),
            })
        else:
            failures.append({**_provenance("sql", i), "reason": "data line outside any known table section", "raw": stripped})

    parsed = len(warehouses) + len(carriers) + len(shipments)
    return {
        "warehouses": warehouses, "carriers": carriers, "shipments": shipments,
        "report": {
            "source": "sql", "parsed": parsed, "failed": len(failures), "skipped": skipped,
            "by_kind": {"warehouses": len(warehouses), "carriers": len(carriers), "shipments": len(shipments)},
            "failures": failures,
        },
    }


def parse_news(text: str) -> dict:
    """Parse raw timestamped news blocks → news rows with provenance + confidence.

    Each block is ``<stamp> <id> | <headline>`` then a body line. A missing frame stamp or missing id
    lowers confidence; a block with neither is an observable failure (can't be keyed)."""
    news: list[dict] = []
    failures: list[dict] = []
    skipped = 0
    blocks = text.split("\n\n")
    line_cursor = 0
    for b, block in enumerate(blocks):
        block_start = line_cursor
        line_cursor += block.count("\n") + 2  # account for the consumed "\n\n"
        block = block.strip("\n")
        if not block.strip():
            skipped += 1  # empty block: accounted as skipped (parity with sql/throughput), never dropped
            continue
        first, _, body = block.partition("\n")
        conf = 1.0
        fm = _FRAME_RE.search(first)
        frame = next((int(g) for g in (fm.groups() if fm else ()) if g is not None), None) if fm else None
        if frame is None:
            conf = min(conf, 0.4)
        im = _NEWS_ID_RE.search(first)
        nid = im.group(1) if im else None
        if nid is None:
            conf = min(conf, 0.3)
        if frame is None and nid is None:
            failures.append({**_provenance("news", block_start), "reason": "news block: no frame stamp and no id", "raw": first[:60]})
            continue
        # headline = remainder of the first line after the id and a separator
        headline = first
        if im:
            headline = first[im.end():].lstrip(" |:").strip()
        # a garbled (mojibake) body is preserved verbatim and flagged via confidence, not dropped
        garbled = bool(body) and ("Ã" in body or "å" in body or "æ" in body or "â" in body)
        if garbled:
            conf = min(conf, 0.5)
        news.append({
            "id": nid, "frame": frame, "headline": headline, "body": body.strip(),
            "garbled": garbled,
            "_provenance": _provenance("news", block_start), "_confidence": round(conf, 3),
        })
    return {
        "news": news,
        "report": {"source": "news", "parsed": len(news), "failed": len(failures), "skipped": skipped,
                   "failures": failures},
    }


def parse_throughput(text: str) -> dict:
    """Parse the noisy throughput dump → per-warehouse series of (frame,value) points with provenance.

    Handles both the ``t<frame>: <value>`` key:value lines and the ``frame:value`` CSV-pair rows.
    A ``=== throughput :: WID ===`` header switches the active warehouse."""
    series: dict[str, list[dict]] = {}
    failures: list[dict] = []
    skipped = 0
    points = 0
    current = None
    hdr_re = re.compile(r"throughput\s*::\s*(\S+)")
    for i, raw_line in enumerate(text.splitlines()):
        line = raw_line.strip()
        if not line:
            skipped += 1
            continue
        hm = hdr_re.search(line)
        if line.startswith("===") and hm:
            current = hm.group(1)
            series.setdefault(current, [])
            skipped += 1
            continue
        if line.lower().startswith("frame"):  # csv header line
            skipped += 1
            continue
        kv = _TP_KV_RE.match(line)
        if kv and current is not None:
            series[current].append({"frame": int(kv.group(1)), "value": float(kv.group(2)),
                                    "_provenance": _provenance("throughput", i), "_confidence": 1.0})
            points += 1
            continue
        # a CSV pair line: "0:655.3,1:623.3;..." — split on any non-pair delimiter
        pairs = re.split(r"[,; ]+", line)
        matched = [_TP_PAIR_RE.match(p) for p in pairs if p]
        if current is not None and matched and all(m for m in matched):
            for m in matched:
                series[current].append({"frame": int(m.group(1)), "value": float(m.group(2)),
                                        "_provenance": _provenance("throughput", i), "_confidence": 1.0})
                points += 1
            continue
        failures.append({**_provenance("throughput", i), "reason": "throughput line: unrecognized point format", "raw": line[:60]})

    return {
        "throughput": series,
        "report": {"source": "throughput", "parsed": points, "failed": len(failures),
                   "skipped": skipped, "warehouses": len(series), "failures": failures},
    }


def parse_package(rendered: dict) -> dict:
    """Parse a full :func:`backend.app.raw_render.render_package` output back into structured entities.

    Returns ``{entities, reports, summary}`` — entities carry provenance + confidence; ``reports`` is
    the per-source observable failure report; ``summary`` rolls up parsed/failed totals."""
    raw = rendered["raw"]
    sql = parse_sql(raw["sql"])
    news = parse_news(raw["news"])
    tp = parse_throughput(raw["throughput"])

    reports = {"sql": sql["report"], "news": news["report"], "throughput": tp["report"]}
    total_parsed = sql["report"]["parsed"] + news["report"]["parsed"] + tp["report"]["parsed"]
    total_failed = sql["report"]["failed"] + news["report"]["failed"] + tp["report"]["failed"]
    return {
        "entities": {
            "warehouses": sql["warehouses"], "carriers": sql["carriers"], "shipments": sql["shipments"],
            "news": news["news"], "throughput": tp["throughput"],
        },
        "reports": reports,
        "summary": {
            "parsed": total_parsed, "failed": total_failed,
            "failure_rate": round(total_failed / (total_parsed + total_failed), 4) if (total_parsed + total_failed) else 0.0,
        },
        "source_id": rendered.get("source_id"),
        "seed": rendered.get("seed"),
        "dirtiness": rendered.get("dirtiness"),
        "link_explicitness": rendered.get("link_explicitness"),
    }
