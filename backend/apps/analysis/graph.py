"""把已验证的静态关联投影为有界图，不解释为运行轨迹。"""

import json
import uuid
from collections import Counter, deque
from typing import Any, cast

from apps.analysis.types import (
    GRAPH_VERSION,
    LEGACY_GRAPH_VERSION,
    MAX_GRAPH_BYTES,
    MAX_GRAPH_EDGES,
    MAX_GRAPH_NODES,
    MAX_QUERY_EDGES,
    MAX_QUERY_NODES,
    AnalysisFailed,
    AnalysisResult,
    Evidence,
    GraphData,
    GraphEdge,
    GraphNode,
    GraphQuery,
    GraphRelation,
    GraphSelection,
    GraphSymbolKind,
    Symbol,
)


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_graph(analysis_id: uuid.UUID, result: AnalysisResult) -> GraphData:
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}
    candidates = Counter(
        (e["method"], e["path"], e["path_kind"]) for e in result["endpoints"]
    )

    def symbol_node(kind: GraphSymbolKind, symbol: Symbol) -> str:
        identity = str(uuid.uuid5(analysis_id, canonical([kind, symbol])))
        if identity not in nodes:
            nodes[identity] = {
                "id": identity,
                "kind": kind,
                "name": symbol["name"],
                "source_ref": symbol["source_ref"],
                "evidence": [
                    {
                        "kind": "source_fact",
                        "rule": "python.symbol",
                        "source_ref": symbol["source_ref"],
                    }
                ],
                "endpoint": None,
            }
        return identity

    def connect(
        source: str, target: str, relation: GraphRelation, evidence: list[Evidence]
    ) -> None:
        if not evidence:
            raise AnalysisFailed("invalid_graph_result")
        identity = str(uuid.uuid5(analysis_id, canonical([source, target, relation])))
        if identity not in edges:
            edges[identity] = {
                "id": identity,
                "source_id": source,
                "target_id": target,
                "relation": relation,
                "evidence": [],
            }
        previous = {canonical(e): e for e in edges[identity]["evidence"]}
        previous.update({canonical(e): e for e in evidence})
        edges[identity]["evidence"] = [previous[k] for k in sorted(previous)]

    for index, endpoint in enumerate(result["endpoints"]):
        identity = str(uuid.uuid5(analysis_id, f"endpoint:{index}"))
        route_evidence = [
            e
            for e in endpoint["evidence"]
            if e["rule"]
            not in {
                "drf.serializer_class",
                "drf.action_serializer_class",
                "drf.model_serializer_meta_model",
            }
        ]
        route_refs = [
            e["source_ref"]
            for e in route_evidence
            if e["rule"] in {"django.path", "drf.router_register", "drf.default_router"}
            and e["source_ref"] is not None
        ]
        nodes[identity] = {
            "id": identity,
            "kind": "endpoint",
            "name": f"{endpoint['method']} {endpoint['path']}",
            "source_ref": route_refs[-1] if route_refs else None,
            "evidence": route_evidence,
            "endpoint": {
                "index": index,
                "method": endpoint["method"],
                "path": endpoint["path"],
                "path_kind": endpoint["path_kind"],
                "action": endpoint["action"],
                "is_candidate": candidates[
                    endpoint["method"], endpoint["path"], endpoint["path_kind"]
                ]
                > 1,
            },
        }
        previous_id = identity
        relations: tuple[
            tuple[GraphSymbolKind, GraphRelation, tuple[str, ...] | None], ...
        ] = (
            ("view", "route_view", None),
            (
                "serializer",
                "serializer_class",
                ("drf.serializer_class", "drf.action_serializer_class"),
            ),
            ("model", "meta_model", ("drf.model_serializer_meta_model",)),
        )
        symbols = {
            "view": endpoint["view"],
            "serializer": endpoint["serializer"],
            "model": endpoint["model"],
        }
        for kind, relation, rules in relations:
            symbol = symbols[kind]
            if symbol is None:
                break
            target = symbol_node(kind, symbol)
            evidence = (
                route_evidence
                if rules is None
                else [e for e in endpoint["evidence"] if e["rule"] in rules]
            )
            connect(previous_id, target, relation, evidence)
            previous_id = target
        if len(nodes) > MAX_GRAPH_NODES or len(edges) > MAX_GRAPH_EDGES:
            raise AnalysisFailed("graph_limit")
    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def validate_graph(
    value: Any,
    snapshot_id: str,
    line_counts: dict[str, int],
    graph_version: str = GRAPH_VERSION,
) -> GraphData:
    """对发布和持久化读取边界校验，拒绝部分或损坏的图。"""

    def require(condition: bool) -> None:
        if not condition:
            raise AnalysisFailed("invalid_graph_result")

    def identifier(item: Any) -> None:
        require(isinstance(item, str) and len(item) == 36)
        try:
            require(str(uuid.UUID(item)) == item)
        except ValueError:
            raise AnalysisFailed("invalid_graph_result") from None

    def text_value(item: Any, maximum: int) -> None:
        require(
            isinstance(item, str)
            and 0 < len(item) <= maximum
            and not any(ord(c) < 32 for c in item)
        )

    def reference(item: Any) -> None:
        require(
            isinstance(item, dict)
            and set(item) == {"snapshot_id", "file_path", "start_line", "end_line"}
        )
        require(item["snapshot_id"] == snapshot_id)
        require(isinstance(item["file_path"], str) and item["file_path"] in line_counts)
        require(type(item["start_line"]) is int and type(item["end_line"]) is int)
        require(
            1
            <= item["start_line"]
            <= item["end_line"]
            <= line_counts[item["file_path"]]
        )

    def evidence_list(items: Any) -> None:
        require(isinstance(items, list) and 0 < len(items) <= 256)
        for item in items:
            require(
                isinstance(item, dict) and set(item) == {"kind", "rule", "source_ref"}
            )
            require(
                item["kind"] in ("source_fact", "static_inference", "framework_rule")
            )
            text_value(item["rule"], 200)
            if item["source_ref"] is None:
                require(item["kind"] == "framework_rule")
            else:
                reference(item["source_ref"])

    require(graph_version in {GRAPH_VERSION, LEGACY_GRAPH_VERSION})
    require(isinstance(value, dict) and set(value) == {"nodes", "edges"})
    require(isinstance(value["nodes"], list) and isinstance(value["edges"], list))
    if len(value["nodes"]) > MAX_GRAPH_NODES or len(value["edges"]) > MAX_GRAPH_EDGES:
        raise AnalysisFailed("graph_limit")
    ids: set[str] = set()
    indices: set[int] = set()
    for node in value["nodes"]:
        require(
            isinstance(node, dict)
            and set(node)
            in (
                {"id", "kind", "name", "source_ref", "evidence", "endpoint"},
                {"id", "kind", "name", "source_ref", "evidence", "endpoint", "request"},
            )
        )
        identifier(node["id"])
        require(node["id"] not in ids)
        ids.add(node["id"])
        kinds = {"endpoint", "view", "serializer", "model"}
        if graph_version == GRAPH_VERSION:
            kinds |= {"frontend_function", "frontend_request"}
        require(isinstance(node["kind"], str) and node["kind"] in kinds)
        text_value(node["name"], 9000)
        evidence_list(node["evidence"])
        if node["source_ref"] is not None:
            reference(node["source_ref"])
        else:
            require(node["kind"] == "endpoint")
        endpoint = node["endpoint"]
        if node["kind"] == "frontend_request":
            request = node.get("request")
            require(
                isinstance(request, dict)
                and set(request)
                == {"method", "original_path", "path", "status", "reason"}
            )
            require(
                request["method"] is None
                or request["method"]
                in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE")
            )
            for key in ("original_path", "path"):
                if request[key] is not None:
                    require(
                        isinstance(request[key], str)
                        and len(request[key]) <= 8192
                        and not any(ord(c) < 32 for c in request[key])
                    )
            require(request["status"] in ("confirmed", "candidate", "unmatched"))
            text_value(request["reason"], 200)
        else:
            require("request" not in node)
        if node["kind"] != "endpoint":
            require(endpoint is None)
            continue
        require(
            isinstance(endpoint, dict)
            and set(endpoint)
            == {"index", "method", "path", "path_kind", "action", "is_candidate"}
        )
        require(type(endpoint["index"]) is int and endpoint["index"] >= 0)
        require(endpoint["index"] not in indices)
        indices.add(endpoint["index"])
        require(
            endpoint["method"]
            in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE")
        )
        require(endpoint["path_kind"] in ("django_path", "router_regex"))
        text_value(endpoint["path"], 8192)
        text_value(endpoint["action"], 8192)
        require(type(endpoint["is_candidate"]) is bool)
    edge_ids: set[str] = set()
    for edge in value["edges"]:
        require(
            isinstance(edge, dict)
            and set(edge) == {"id", "source_id", "target_id", "relation", "evidence"}
        )
        for field in ("id", "source_id", "target_id"):
            identifier(edge[field])
        require(edge["id"] not in edge_ids)
        edge_ids.add(edge["id"])
        require(edge["source_id"] in ids and edge["target_id"] in ids)
        relations = {"route_view", "serializer_class", "meta_model"}
        if graph_version == GRAPH_VERSION:
            relations |= {
                "direct_call",
                "contains_function",
                "contains_request",
                "callback_binding",
                "method_path_match",
                "candidate_match",
            }
        require(isinstance(edge["relation"], str) and edge["relation"] in relations)
        evidence_list(edge["evidence"])
    size = 0
    for chunk in json.JSONEncoder(ensure_ascii=False, separators=(",", ":")).iterencode(
        value
    ):
        size += len(chunk.encode("utf-8"))
        if size > MAX_GRAPH_BYTES:
            raise AnalysisFailed("graph_limit")
    return cast(GraphData, value)


def select_graph(graph: GraphData, query: GraphQuery) -> GraphSelection:
    """默认沿出边；接口视角仅回溯前端上游并展开后端下游。"""
    if (
        query.algorithm not in {"bfs", "dfs"}
        or type(query.max_nodes) is not int
        or type(query.max_edges) is not int
        or not 1 <= query.max_nodes <= MAX_QUERY_NODES
        or not 1 <= query.max_edges <= MAX_QUERY_EDGES
        or (
            query.endpoint_index is not None
            and (
                type(query.endpoint_index) is not int
                or query.endpoint_index < 0
                or query.root_node_id is not None
            )
        )
    ):
        raise ValueError("图查询参数无效。")
    ordered = sorted(
        graph["nodes"],
        key=lambda n: (
            0 if n["endpoint"] is not None else 1,
            n["endpoint"]["index"] if n["endpoint"] is not None else 0,
            n["kind"],
            n["name"],
            n["id"],
        ),
    )
    nodes = {n["id"]: n for n in ordered}
    rank = {identity: i for i, identity in enumerate(nodes)}
    adjacent: dict[str, set[str]] = {identity: set() for identity in nodes}
    root_id = query.root_node_id
    if query.endpoint_index is not None:
        root_id = next(
            (
                n["id"]
                for n in ordered
                if n["endpoint"] is not None
                and n["endpoint"]["index"] == query.endpoint_index
            ),
            None,
        )
        if root_id is None:
            raise KeyError(query.endpoint_index)
    for edge in graph["edges"]:
        source, target = edge["source_id"], edge["target_id"]
        if query.endpoint_index is not None and nodes[source]["kind"].startswith(
            "frontend_"
        ):
            adjacent[target].add(source)
        else:
            adjacent[source].add(target)
    neighbors = {
        identity: sorted(targets, key=rank.__getitem__)
        for identity, targets in adjacent.items()
    }
    if root_id is not None and root_id not in nodes:
        raise KeyError(root_id)
    roots = [root_id] if root_id is not None else list(nodes)
    selected: dict[str, GraphNode] = {}
    truncated_nodes = False
    for root in roots:
        pending = deque([root])
        while pending:
            identity = pending.popleft() if query.algorithm == "bfs" else pending.pop()
            if identity in selected:
                continue
            if len(selected) == query.max_nodes:
                truncated_nodes = True
                break
            selected[identity] = nodes[identity]
            targets = neighbors[identity]
            pending.extend(targets if query.algorithm == "bfs" else reversed(targets))
        if truncated_nodes:
            break
    position = {identity: i for i, identity in enumerate(selected)}
    edges = sorted(
        [
            e
            for e in graph["edges"]
            if e["source_id"] in selected and e["target_id"] in selected
        ],
        key=lambda e: (position[e["source_id"]], position[e["target_id"]], e["id"]),
    )
    reasons = (["max_nodes"] if truncated_nodes else []) + (
        ["max_edges"] if len(edges) > query.max_edges else []
    )
    returned_edges = edges[: query.max_edges]
    return {
        "nodes": list(selected.values()),
        "edges": returned_edges,
        "total_nodes": len(nodes),
        "total_edges": len(graph["edges"]),
        "returned_nodes": len(selected),
        "returned_edges": len(returned_edges),
        "truncated": bool(reasons),
        "truncation_reasons": reasons,
    }
