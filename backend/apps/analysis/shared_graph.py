"""接口通过共享源码符号连接；每接口至多三边，不展开接口对。"""

import uuid
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from typing import Any

from apps.analysis.graph import canonical
from apps.analysis.types import GraphData, GraphEdge, GraphQuery, GraphRelation

SHARED_GRAPH_VERSION = "shared-interface/1.0.0"


def shared_graph(
    analysis_id: uuid.UUID, endpoints: Sequence[Mapping[str, Any]], original: GraphData
) -> GraphData:
    members: dict[str, list[int]] = defaultdict(list)
    symbols: dict[str, tuple[str, dict[str, Any]]] = {}
    for index, endpoint in enumerate(endpoints):
        for kind in ("view", "serializer", "model"):
            symbol = endpoint[kind]
            if symbol is not None:
                identity = str(uuid.uuid5(analysis_id, canonical([kind, symbol])))
                members[identity].append(index)
                symbols[identity] = (kind, symbol)
    node_map = {node["id"]: node for node in original["nodes"]}
    nodes = [node for node in original["nodes"] if node["kind"] == "endpoint"]
    edges: list[GraphEdge] = []
    relations: dict[str, GraphRelation] = {
        "view": "route_view",
        "serializer": "serializer_class",
        "model": "meta_model",
    }
    for identity in sorted(members):
        if len(members[identity]) < 2:
            continue
        if identity not in node_map:
            continue
        nodes.append(node_map[identity])
        kind, _ = symbols[identity]
        for index in members[identity]:
            source_id = str(uuid.uuid5(analysis_id, f"endpoint:{index}"))
            edges.append(
                {
                    "id": str(
                        uuid.uuid5(analysis_id, f"shared:{source_id}:{identity}")
                    ),
                    "source_id": source_id,
                    "target_id": identity,
                    "relation": relations[kind],
                    "evidence": endpoints[index]["evidence"],
                }
            )
    return {"nodes": nodes, "edges": edges}


def select_shared_graph(graph: GraphData, query: GraphQuery) -> dict[str, Any]:
    nodes = {node["id"]: node for node in graph["nodes"]}
    adjacent: dict[str, list[str]] = {identity: [] for identity in nodes}
    for edge in graph["edges"]:
        adjacent[edge["source_id"]].append(edge["target_id"])
        adjacent[edge["target_id"]].append(edge["source_id"])
    root_id = query.root_node_id
    if query.endpoint_index is not None:
        root_id = next(
            (
                node["id"]
                for node in nodes.values()
                if node["endpoint"]
                and node["endpoint"]["index"] == query.endpoint_index
            ),
            None,
        )
        if root_id is None:
            raise KeyError(query.endpoint_index)
    if root_id is not None and root_id not in nodes:
        raise KeyError(root_id)
    starts = [root_id] if root_id is not None else list(nodes)
    selected: dict[str, Any] = {}
    truncated = False
    for start in starts:
        pending = deque([start])
        while pending:
            identity = pending.popleft() if query.algorithm == "bfs" else pending.pop()
            if identity in selected:
                continue
            if len(selected) >= query.max_nodes:
                truncated = True
                break
            selected[identity] = nodes[identity]
            pending.extend(sorted(adjacent[identity]))
        if truncated:
            break
    edges = [
        edge
        for edge in graph["edges"]
        if edge["source_id"] in selected and edge["target_id"] in selected
    ]
    reasons = (["max_nodes"] if truncated else []) + (
        ["max_edges"] if len(edges) > query.max_edges else []
    )
    edges = edges[: query.max_edges]
    return {
        "nodes": list(selected.values()),
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(graph["edges"]),
        "returned_nodes": len(selected),
        "returned_edges": len(edges),
        "truncated": bool(reasons),
        "truncation_reasons": reasons,
        "direction": "undirected",
        "scope": "connected_shared_symbols" if root_id else "all_shared_symbols",
        "graph_version": SHARED_GRAPH_VERSION,
    }
