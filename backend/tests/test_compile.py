"""NL → policy-IR compile. The LLM call itself is non-deterministic and needs LM Studio, so these
tests cover the parts that MUST hold regardless: strict IR normalization, the honest health shape,
and — crucially — the OBSERVABLE failure path (no fake fallback). HTTP primitives are monkeypatched so
the suite is fast and does not depend on a running model (the live model test is done at the UI)."""
from __future__ import annotations

import urllib.error

from fastapi.testclient import TestClient

from backend.app import llm_client
from backend.app.main import app

client = TestClient(app)


def test_normalize_drops_malformed_and_clamps() -> None:
    obj = {
        "rules": [
            {"when": {"op": ">=", "value": 9}, "do": {"action": "shift", "by": -0.15}},  # ok
            {"when": {"op": "≈", "value": 5}, "do": {"action": "shift", "by": -0.1}},  # bad op → drop
            {"when": {"op": "<=", "value": 3}, "do": {"action": "teleport", "by": -0.1}},  # bad action → drop
            {"when": {"op": ">", "value": "x"}, "do": {"action": "pulse", "by": -0.1}},  # bad value → drop
            {"when": {"op": ">=", "value": float("inf")}, "do": {"action": "shift", "by": -0.1}},  # inf → drop
            {"when": {"op": ">=", "value": 5}, "do": {"action": "shift", "by": float("nan")}},  # NaN by → drop
            {"when": {"op": "<", "value": 2}, "do": {"action": "shift", "by": -5}},  # by clamped to -1
        ]
    }
    rules = llm_client.normalize_rules(obj)
    assert len(rules) == 2
    assert rules[0] == {"when": {"op": ">=", "value": 9.0}, "do": {"action": "shift", "by": -0.15}}
    assert rules[1]["do"]["by"] == -1.0  # clamped, NOT 1.0 from a dead NaN guard


def test_normalize_clamps_trigger_into_range() -> None:
    obj = {"rules": [{"when": {"op": ">=", "value": 999}, "do": {"action": "shift", "by": -0.2}}]}
    rules = llm_client.normalize_rules(obj, lo=0, hi=12)
    assert rules[0]["when"]["value"] == 12.0  # trigger pulled into [0,12]


def test_extract_json_strips_think_and_fences() -> None:
    import json as _json

    body = '<think>let me reason about this</think>\n```json\n{"rules": []}\n```'
    assert _json.loads(llm_client._extract_json(body)) == {"rules": []}
    assert _json.loads(llm_client._extract_json('prefix {"rules": [1]} suffix'))["rules"] == [1]


def test_normalize_caps_at_four_and_keeps_notes() -> None:
    obj = {"rules": [{"when": {"op": ">=", "value": i}, "do": {"action": "shift", "by": -0.1}, "note": f"r{i}"} for i in range(8)]}
    rules = llm_client.normalize_rules(obj)
    assert len(rules) == 4 and rules[0]["note"] == "r0"


def test_normalize_empty_on_garbage() -> None:
    assert llm_client.normalize_rules({"rules": [{"nope": 1}]}) == []
    assert llm_client.normalize_rules({}) == []


def test_health_shape_reachable(monkeypatch) -> None:
    monkeypatch.setattr(llm_client, "_get", lambda *a, **k: {"data": [{"id": "qwen"}, {"id": "x-embed"}]})
    monkeypatch.delenv("PRISM_LLM_MODEL", raising=False)
    body = client.get("/api/llm/health").json()
    for k in ("reachable", "base_url", "model", "models", "compile_calls", "compile_failures"):
        assert k in body
    assert body["reachable"] is True
    assert body["model"] == "qwen"  # first non-embedding model auto-picked


def test_health_reachable_false_when_probe_fails(monkeypatch) -> None:
    def boom(*a, **k):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr(llm_client, "_get", boom)
    assert client.get("/api/llm/health").json()["reachable"] is False


def test_compile_validates_before_calling_llm() -> None:
    assert client.post("/api/compile/nope", json={"entity_type": "station", "attribute": "pressure", "nl": "x"}).status_code == 404
    assert client.post("/api/compile/infra_monitoring", json={"entity_type": "station", "attribute": "status", "nl": "x"}).status_code == 400


def test_compile_fails_observably_when_llm_unreachable(monkeypatch) -> None:
    # the LLM call raises → must 502 with a reason and bump the failure counter, NEVER fabricate an IR
    def boom(*a, **k):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(llm_client, "_post", boom)
    monkeypatch.setenv("PRISM_LLM_MODEL", "unreachable-model")  # skip the models probe
    before = llm_client._stats["compile_failures"]
    r = client.post("/api/compile/infra_monitoring", json={"entity_type": "station", "attribute": "pressure", "nl": "ease off near the limit"})
    assert r.status_code == 502 and "不可达" in r.json()["detail"]
    assert llm_client._stats["compile_failures"] == before + 1


def test_compile_rejects_unparseable_model_output(monkeypatch) -> None:
    # model returns prose, not JSON → observable parse failure, not a guessed rule
    monkeypatch.setattr(llm_client, "_post", lambda *a, **k: {"choices": [{"message": {"content": "sorry I cannot"}}]})
    monkeypatch.setenv("PRISM_LLM_MODEL", "m")
    r = client.post("/api/compile/infra_monitoring", json={"entity_type": "station", "attribute": "pressure", "nl": "ease off"})
    assert r.status_code == 502 and "无法解析" in r.json()["detail"]


def test_compile_happy_path_with_stubbed_model(monkeypatch) -> None:
    payload = {"choices": [{"message": {"content": '{"rules":[{"when":{"op":">=","value":9},"do":{"action":"shift","by":-0.2}}]}'}}], "model": "qwen"}
    monkeypatch.setattr(llm_client, "_post", lambda *a, **k: payload)
    monkeypatch.setenv("PRISM_LLM_MODEL", "qwen")
    r = client.post("/api/compile/infra_monitoring", json={"entity_type": "station", "attribute": "pressure", "nl": "when pressure hits 9 cut 20%"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] and body["source"] == "llm_compiled" and body["model"] == "qwen"
    assert body["rules"] == [{"when": {"op": ">=", "value": 9.0}, "do": {"action": "shift", "by": -0.2}}]


def test_json_schema_block_normalizes_bare_and_passes_wrapper() -> None:
    # LM Studio requires response_format.json_schema to carry a `name`; a bare schema 400s. The normalizer
    # wraps a bare schema and passes a pre-wrapped one through unchanged (so benchmark's fixtures stay valid).
    bare = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
    blk = llm_client._json_schema_block(bare)
    assert blk["name"] == "response" and blk["schema"] == bare
    wrapped = {"name": "ans", "strict": True, "schema": bare}
    assert llm_client._json_schema_block(wrapped) is wrapped


def test_structured_complete_payload_always_names_the_json_schema(monkeypatch) -> None:
    # the actual 400-fix: whatever a caller passes, the outgoing payload's json_schema has a `name`.
    captured: dict = {}
    def fake_post(path, payload):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": '{"x":"ok"}'}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}, "model": "m"}
    monkeypatch.setattr(llm_client, "_post", fake_post)
    monkeypatch.setattr(llm_client, "_fix_save", lambda cache: None)  # never mutate the committed fixture cache
    bare = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
    r = llm_client.structured_complete("sys", "user", bare, model="m", use_fixture=False, allow_live=True)
    assert r["ok"]
    js = captured["payload"]["response_format"]["json_schema"]
    assert js["name"] == "response" and js["schema"] == bare
