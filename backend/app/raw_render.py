"""Render a generated data-package into MESSY heterogeneous RAW text per source (§5 upstream).

This is the *upstream* of the axiom layer: it un-structures a clean cross-source package
(:func:`backend.app.data_package.generate`) back into the kind of raw, heterogeneous text an
agentic parser would actually be handed — a messy CSV-ish SQL dump, free-text timestamped news
blocks, and a noisy throughput key:value / CSV dump. :mod:`backend.app.parser` is the inverse:
it parses these blobs back into structured rows.

WELDED DISCIPLINES
  * DETERMINISTIC: no ``random``, no clock. All cosmetic variation (which delimiter, which quoting,
    which unit suffix spelling, where a stray blank cell lands) is derived by HASHING via Prism's own
    :func:`backend.app.data_synth._unit` — byte-reproducible across runs.
  * CLEAN-ROOM: only Prism's own code.
  * HONEST DIRTINESS: the messiness rendered here is ONLY the dirtiness already baked into the package
    by ``data_package._apply_dirtiness`` (lb unit drift, nulled statuses → blank cells, ±frame news
    time offsets, mojibake-garbled news bodies, region aliases). This renderer INVENTS NO NEW
    corruption of the truth — it only chooses *surface form* (delimiter/quote/whitespace/header
    casing). Surface-form scramble is a rendering concern, never a truth mutation: a blank weight cell
    is rendered iff the package already stored a value, a missing status cell iff the package already
    nulled it. The ground-truth answers are never read or rendered.

The output is a dict ``{source: text}`` plus a small manifest of how many rows went into each blob, so
the parser's recovery rate has an honest denominator.
"""
from __future__ import annotations

from .data_synth import _unit

# Surface-form vocabularies. The CHOICE among them is hash-driven per row, so a single blob mixes
# delimiters / quoting / unit spellings — heterogeneity without any new corruption of values.
_DELIMS = [",", ";", "\t", " | "]
_KG_SUFFIX = ["kg", " kg", "KG", "千克"]
_LB_SUFFIX = ["lb", " lb", "LB", "lbs"]
_BLANK = ""  # a missing/blank cell — only emitted where the package already nulled the value


def _u(*parts: object) -> float:
    """[0,1] hash — Prism's own deterministic unit, no clock/random."""
    return _unit(*parts)


def _pick(seq: list, *seed: object):
    return seq[int(_u(*seed) * len(seq)) % len(seq)]


def _maybe_quote(cell: str, *seed: object) -> str:
    """Sometimes wrap a cell in quotes, sometimes not — mixed quoting, value unchanged.

    Always quote when the cell itself contains the delimiter family characters, so the surface form
    never silently corrupts the value (a comma inside an unquoted CSV cell would split a field)."""
    if cell == _BLANK:
        return cell
    must = any(ch in cell for ch in ",;|\t")
    if must or _u("quote", *seed) < 0.35:
        return '"' + cell.replace('"', '""') + '"'
    return cell


def render_sql(package: dict) -> tuple[str, dict]:
    """SQL stores → a messy CSV-ish blob: mixed delimiters, mixed quoting, unit suffixes on weights
    (kg/lb — straight from the package's own unit drift), and BLANK cells where status was nulled.

    Returns ``(text, counts)`` where counts has the per-table row tally (the recovery denominator)."""
    sql = package["stores"]["sql"]
    seed = package["seed"]
    lines: list[str] = []
    counts = {"warehouses": 0, "carriers": 0, "shipments": 0}

    lines.append("### WAREHOUSES (id, region, port, name) ###")
    for i, w in enumerate(sql["warehouses"]):
        d = _pick(_DELIMS, seed, "whdelim", i)
        cells = [w["id"], w["region"], w["port"], w["name"]]
        row = d.join(_maybe_quote(str(c), seed, "whq", i, j) for j, c in enumerate(cells))
        lines.append(row)
        counts["warehouses"] += 1

    lines.append("")
    lines.append("### CARRIERS id|name ###")
    for i, c in enumerate(sql["carriers"]):
        d = _pick(_DELIMS, seed, "crdelim", i)
        row = d.join(_maybe_quote(str(x), seed, "crq", i, j) for j, x in enumerate([c["id"], c["name"]]))
        lines.append(row)
        counts["carriers"] += 1

    lines.append("")
    # header casing/spelling itself wobbles (schema-drift surface form) but column ORDER is fixed
    hdr = _pick(
        ["shipment_id,warehouse,carrier,frame,weight,status",
         "id ; wh ; carrier ; dispatch_frame ; wgt ; status",
         "SHP_ID | WAREHOUSE_ID | CARRIER_ID | FRAME | WEIGHT | STATUS"],
        seed, "shiphdr",
    )
    lines.append("### SHIPMENTS ###")
    lines.append(hdr)
    for i, s in enumerate(sql["shipments"]):
        d = _pick(_DELIMS, seed, "shdelim", i)
        # weight carries the unit suffix the package already chose (kg vs lb). NEVER converts the
        # number — just renders the stored value with a matching suffix spelling.
        if s.get("unit") == "lb":
            suff = _pick(_LB_SUFFIX, seed, "lbsuf", i)
        else:
            suff = _pick(_KG_SUFFIX, seed, "kgsuf", i)
        weight_cell = f"{s['weight_kg']}{suff}"
        # status: blank cell iff the package nulled it (missing-data dirtiness), else the literal value
        status = s.get("status")
        status_cell = _BLANK if status is None else str(status)
        cells = [s["id"], s["warehouse_id"], s["carrier_id"], str(s["dispatch_frame"]), weight_cell, status_cell]
        row = d.join(_maybe_quote(c, seed, "shq", i, j) for j, c in enumerate(cells))
        lines.append(row)
        counts["shipments"] += 1

    return "\n".join(lines), counts


def render_news(package: dict) -> tuple[str, dict]:
    """News store → raw timestamped text blocks. Each block is a free-text record with a frame stamp
    and headline/body — exactly the package's news rows (including ±frame time offsets and any mojibake
    garble already applied by the dirtiness layer). No truth labels (``_truth_event``) are rendered."""
    news = package["stores"]["news"]
    seed = package["seed"]
    blocks: list[str] = []
    count = 0
    for i, n in enumerate(news):
        # stamp format wobbles (a date-format-drift surface form) but the frame number is the package's
        stamp = _pick(
            [f"[frame {n['frame']}]", f"@F={n['frame']}", f"<t:{n['frame']}>", f"FRAME {n['frame']} ::"],
            seed, "newsstamp", i,
        )
        head = n.get("headline", "")
        body = n.get("body", "")
        blocks.append(f"{stamp} {n['id']} | {head}\n{body}")
        count += 1
    return "\n\n".join(blocks), {"news": count}


def render_throughput(package: dict) -> tuple[str, dict]:
    """Throughput timeseries → a noisy dump. Per warehouse, the series is emitted either as a
    ``key:value`` listing or a CSV row of (frame,value) pairs — the format choice is hash-driven, so
    one dump mixes both. Frozen points (sensor-glitch dirtiness) are already in the series; rendered
    verbatim. Returns the per-warehouse point counts (recovery denominator)."""
    ts = package["stores"]["timeseries"]["throughput"]
    seed = package["seed"]
    lines: list[str] = []
    counts: dict = {"warehouses": 0, "points": 0}
    for i, (wid, series) in enumerate(sorted(ts.items())):
        lines.append(f"=== throughput :: {wid} ===")
        if _u(seed, "tpfmt", i) < 0.5:
            # key:value listing, one frame per line
            for t, v in enumerate(series):
                sep = _pick([": ", "=", " -> "], seed, "tpsep", i, t)
                lines.append(f"t{t}{sep}{v}")
        else:
            # CSV: frame,value pairs on one line, mixed delimiter
            d = _pick([",", ";", " "], seed, "tpcsvd", i)
            lines.append("frame" + d + "throughput")
            lines.append(d.join(f"{t}:{v}" for t, v in enumerate(series)))
        counts["warehouses"] += 1
        counts["points"] += len(series)
        lines.append("")
    return "\n".join(lines), counts


def render_package(package: dict) -> dict:
    """Render every source of ``package`` into messy RAW text. Returns ``{raw, counts}`` where ``raw``
    maps source name → text blob and ``counts`` is the per-source truth denominator for recovery."""
    sql_txt, sql_counts = render_sql(package)
    news_txt, news_counts = render_news(package)
    tp_txt, tp_counts = render_throughput(package)
    return {
        "raw": {"sql": sql_txt, "news": news_txt, "throughput": tp_txt},
        "counts": {**sql_counts, **news_counts, **tp_counts},
        "source_id": package.get("source_id"),
        "seed": package.get("seed"),
        "dirtiness": package.get("dirtiness"),
        "link_explicitness": package.get("link_explicitness"),
    }
