"""Load semantic-foundation specs from backend/specs/*.json.

A "spec" IS the application: it declares entities, their attributes (each with a semantic_type),
relations, and views. The runtime renders the entire cockpit as a pure function of this spec — no
domain code. Swapping the spec swaps the domain (see infra_monitoring vs library_catalog).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"
_SPEC_ID = re.compile(r"[a-z0-9_]+")


def list_specs() -> list[dict]:
    """Lightweight catalogue of available domain specs (for the domain switcher)."""
    out: list[dict] = []
    for path in sorted(SPECS_DIR.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not doc.get("id"):
            continue
        out.append(
            {
                "id": doc["id"],
                "title": doc.get("title", doc["id"]),
                "title_en": doc.get("title_en", ""),
                "accent": doc.get("accent", "#3b82f6"),
                "entity_count": len(doc.get("entities", [])),
                "view_count": len(doc.get("views", [])),
            }
        )
    return out


def load_spec(spec_id: str) -> dict | None:
    """Load one spec by id. Returns None for unknown / malformed ids (also blocks path traversal)."""
    if not spec_id or not _SPEC_ID.fullmatch(spec_id):
        return None
    path = SPECS_DIR / f"{spec_id}.json"
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if doc.get("id") == spec_id else None
