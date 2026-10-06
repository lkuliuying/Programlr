import uuid
from copy import deepcopy

from apps.analysis.graph import build_graph
from apps.analysis.parser import analyze
from apps.analysis.shared_graph import select_shared_graph, shared_graph
from apps.analysis.tests.test_parser import SNAPSHOT_ID, fixture_sources
from apps.analysis.types import GraphQuery


def test_shared_projection_reaches_peer_endpoints_and_preserves_evidence() -> None:
    identity = uuid.UUID(int=71)
    result = analyze(SNAPSHOT_ID, fixture_sources(), "root_urls.py")
    original = build_graph(identity, result)
    graph = shared_graph(identity, result["endpoints"], original)
    selection = select_shared_graph(graph, GraphQuery(endpoint_index=0))
    assert len([node for node in selection["nodes"] if node["kind"] == "endpoint"]) > 1
    assert selection["direction"] == "undirected"
    assert all(edge["evidence"] for edge in selection["edges"])
    assert len(graph["edges"]) <= len(result["endpoints"]) * 3
    assert original == build_graph(identity, result)


def test_shared_projection_is_linear_for_large_shared_resources() -> None:
    identity = uuid.UUID(int=72)
    result = analyze(SNAPSHOT_ID, fixture_sources(), "root_urls.py")
    result["endpoints"] = [deepcopy(result["endpoints"][0]) for _ in range(500)]
    graph = shared_graph(identity, result["endpoints"], build_graph(identity, result))
    assert len(graph["nodes"]) == 503 and len(graph["edges"]) == 1500
    assert select_shared_graph(graph, GraphQuery())["returned_edges"] > 0
    selection = select_shared_graph(
        graph, GraphQuery(endpoint_index=0, max_nodes=10, max_edges=4)
    )
    assert selection["returned_nodes"] == 10 and selection["returned_edges"] == 4
    assert selection["truncated"] and set(selection["truncation_reasons"]) == {
        "max_nodes",
        "max_edges",
    }
