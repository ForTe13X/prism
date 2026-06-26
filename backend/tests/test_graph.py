"""P2 ontology graph — instance nodes + deterministic relation edges, identity-stable topology.

Verifies the graph is a pure, deterministic function of the spec: byte-identical per frame, node
state evolves while edge topology stays put across frames, edge endpoints are real nodes, and the
whole thing is built domain-agnostically from entities/relations (both demo domains, plus the
null-safe cases of no relations / a relation to an absent entity).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.data_synth import synth_graph
from backend.app.main import app
from backend.app.specs_loader import load_spec

client = TestClient(app)
SPEC_ID = "infra_monitoring"


def _graph(frame: int) -> dict:
    return synth_graph(load_spec(SPEC_ID), SPEC_ID, frame)


def test_node_and_edge_counts_match_spec() -> None:
    g = _graph(36)
    # 8 stations + 14 sensors = 22 nodes; one edge per sensor (sensor installed_at station)
    assert len(g["nodes"]) == 22
    assert len(g["edges"]) == 14
    assert {n["entity_type"] for n in g["nodes"]} == {"station", "sensor"}


def test_graph_is_deterministic_per_frame() -> None:
    assert _graph(20) == _graph(20)
    a = client.get("/api/graph/infra_monitoring?frame=20").json()
    b = client.get("/api/graph/infra_monitoring?frame=20").json()
    assert a == b and a["frame"] == 20


def test_edges_reference_real_nodes_and_respect_direction() -> None:
    g = _graph(10)
    ids = {n["id"] for n in g["nodes"]}
    for e in g["edges"]:
        assert e["from"] in ids and e["to"] in ids
        assert e["from"].startswith("sensor-") and e["to"].startswith("station-")
        assert e["predicate"] == "installed_at"


def test_topology_is_identity_stable_across_frames() -> None:
    # edges must NOT reshuffle as the frame changes (installed_at is identity) …
    e5 = {(e["from"], e["to"]) for e in _graph(5)["edges"]}
    e45 = {(e["from"], e["to"]) for e in _graph(45)["edges"]}
    assert e5 == e45


def test_node_state_evolves_across_frames() -> None:
    # … but node ROWS carry the evolving state used for colouring
    def status_of(g: dict) -> dict:
        return {n["id"]: n["row"].get("status") for n in g["nodes"] if n["entity_type"] == "station"}

    assert status_of(_graph(5)) != status_of(_graph(45))


def test_both_domains_produce_a_graph() -> None:
    lib = synth_graph(load_spec("library_catalog"), "library_catalog", 10)
    assert len(lib["nodes"]) == 15  # 10 books + 5 branches
    assert len(lib["edges"]) == 10  # one per book (book shelved_at branch)
    assert all(e["from"].startswith("book-") and e["to"].startswith("branch-") for e in lib["edges"])


def test_graph_null_safe() -> None:
    # no relations → no edges; a relation to an absent entity is skipped, not fatal
    assert synth_graph({"entities": [], "relations": []}, "x", 0) == {"nodes": [], "edges": []}
    spec = {
        "entities": [{"type": "a", "count": 2, "attributes": [{"name": "n", "semantic_type": "identifier"}]}],
        "relations": [{"from": "a", "predicate": "p", "to": "ghost"}],
    }
    g = synth_graph(spec, "x", 0)
    assert len(g["nodes"]) == 2 and g["edges"] == []


def test_graph_skips_typeless_entity() -> None:
    # a malformed entity with no `type` must be skipped, not 500 the endpoint
    spec = {
        "entities": [
            {"count": 2, "attributes": [{"name": "n", "semantic_type": "identifier"}]},  # no type
            {"type": "ok", "count": 3, "attributes": [{"name": "n", "semantic_type": "identifier"}]},
        ],
        "relations": [],
    }
    g = synth_graph(spec, "x", 0)
    assert [n["entity_type"] for n in g["nodes"]] == ["ok", "ok", "ok"]


def test_graph_unknown_spec_404() -> None:
    assert client.get("/api/graph/nope").status_code == 404
