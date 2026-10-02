"""用有界静态规则关联请求，保留候选而不猜测前缀。"""

import re
import uuid
from collections import defaultdict
from typing import Literal

from apps.analysis.frontend_types import (
    ASSOCIATION_RULE_VERSION,
    FrontendAnalysis,
    FrontendResult,
    RequestMatch,
)
from apps.analysis.types import (
    MAX_GRAPH_EDGES,
    AnalysisFailed,
    Endpoint,
    Evidence,
    GraphData,
    GraphEdge,
    GraphNode,
    GraphRelation,
)


def frontend_node_id(analysis_id: uuid.UUID, identity: str) -> str:
    return str(uuid.uuid5(analysis_id, "frontend:" + identity))


def path_matches(endpoint: Endpoint, target: str) -> bool:
    pattern = endpoint["path"]
    if endpoint["path_kind"] == "router_regex":
        if not pattern.endswith("$"):
            return False
        pattern = pattern[:-1]
    expected, actual = pattern.split("/"), target.split("/")
    # Router 默认 lookup 包含斜杠字符类，先把唯一支持的整段规则转成占位符。
    if endpoint["path_kind"] == "router_regex":
        normalized = re.sub(r"\(\?P<\w+>\[\^/\.\]\+\)", "<lookup>", pattern)
        expected = normalized.split("/")
    for index, segment in enumerate(expected):
        if index >= len(actual):
            return False
        value = actual[index]
        converter = re.fullmatch(r"<(?:([a-z]+):)?[A-Za-z_]\w*>", segment)
        if converter and endpoint["path_kind"] == "django_path":
            kind = converter.group(1) or "str"
            if kind == "path" and index == len(expected) - 1:
                return bool("/".join(actual[index:]))
            if kind == "int" and not (value.isascii() and value.isdecimal()):
                return False
            if kind == "slug" and not re.fullmatch(r"[-a-zA-Z0-9_]+", value):
                return False
            if kind == "uuid" and not re.fullmatch(
                r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", value
            ):
                return False
            if kind not in {"str", "int", "slug", "uuid"} or not value:
                return False
        elif segment == "<lookup>" and endpoint["path_kind"] == "router_regex":
            if not value or "." in value:
                return False
        elif segment != value:
            return False
    return len(expected) == len(actual)


def associate(frontend: FrontendResult, endpoints: list[Endpoint]) -> FrontendAnalysis:
    by_method: dict[str, list[tuple[int, Endpoint]]] = defaultdict(list)
    for index, endpoint in enumerate(endpoints):
        by_method[endpoint["method"]].append((index, endpoint))
    matches: list[RequestMatch] = []
    comparisons = candidate_count = 0
    for request in frontend["requests"]:
        candidates = []
        target = request["path"]
        if (
            target is not None
            and request["method"] is not None
            and request["resolution"] != "dynamic"
        ):
            for index, endpoint in by_method[request["method"]]:
                comparisons += 1
                if comparisons > 100_000:
                    raise AnalysisFailed("association_limit")
                match = path_matches(endpoint, target)
                if request["resolution"] == "unknown_base" and not match:
                    # 后缀仅用于呈现候选，绝不把未知前缀删掉后升级为确认连接。
                    match = endpoint["path_kind"] == "django_path" and endpoint[
                        "path"
                    ].endswith("/" + target.lstrip("/"))
                if match:
                    candidates.append(index)
        candidate_count += len(candidates)
        if candidate_count > MAX_GRAPH_EDGES:
            raise AnalysisFailed("association_limit")
        status: Literal["confirmed", "candidate", "unmatched"] = (
            "confirmed"
            if len(candidates) == 1 and request["resolution"] == "static"
            else "candidate"
            if candidates
            else "unmatched"
        )
        reason = (
            "unique_method_path"
            if status == "confirmed"
            else "multiple_endpoints"
            if len(candidates) > 1
            else request["resolution"]
            if request["resolution"] != "static"
            else "no_matching_endpoint"
        )
        matches.append(
            {
                "request_id": request["id"],
                "status": status,
                "reason": reason,
                "endpoint_indices": candidates,
                "evidence": request["evidence"],
            }
        )
    return {
        "parser": frontend,
        "association_rule_version": ASSOCIATION_RULE_VERSION,
        "matches": matches,
    }


def extend_graph(
    analysis_id: uuid.UUID,
    graph: GraphData,
    frontend: FrontendAnalysis,
    endpoints: list[Endpoint],
) -> GraphData:
    nodes: list[GraphNode] = list(graph["nodes"])
    edges: list[GraphEdge] = list(graph["edges"])
    parser = frontend["parser"]
    for function in parser["functions"]:
        nodes.append(
            {
                "id": frontend_node_id(analysis_id, function["id"]),
                "kind": "frontend_function",
                "name": function["name"],
                "source_ref": function["source_ref"],
                "endpoint": None,
                "evidence": [
                    {
                        "kind": "source_fact",
                        "rule": "javascript.function",
                        "source_ref": function["source_ref"],
                    },
                    *function["entry_points"],
                ],
            }
        )
    matches = {match["request_id"]: match for match in frontend["matches"]}
    for request in parser["requests"]:
        match = matches[request["id"]]
        nodes.append(
            {
                "id": frontend_node_id(analysis_id, request["id"]),
                "kind": "frontend_request",
                "name": f"{request['method'] or '未知方法'} {request['path'] or '动态路径'}",
                "source_ref": request["source_ref"],
                "endpoint": None,
                "evidence": request["evidence"],
                "request": {
                    "method": request["method"],
                    "original_path": request["original_path"],
                    "path": request["path"],
                    "status": match["status"],
                    "reason": match["reason"],
                },
            }
        )

    def connect(
        source: str, target: str, relation: GraphRelation, evidence: list[Evidence]
    ) -> None:
        edges.append(
            {
                "id": str(
                    uuid.uuid5(
                        analysis_id, f"{source}:{target}:{relation}:{len(edges)}"
                    )
                ),
                "source_id": source,
                "target_id": target,
                "relation": relation,
                "evidence": evidence,
            }
        )

    for relation in parser["relations"]:
        connect(
            frontend_node_id(analysis_id, relation["source_id"]),
            frontend_node_id(analysis_id, relation["target_id"]),
            relation["relation"],
            relation["evidence"],
        )
    for match in frontend["matches"]:
        for index in match["endpoint_indices"]:
            connect(
                frontend_node_id(analysis_id, match["request_id"]),
                str(uuid.uuid5(analysis_id, f"endpoint:{index}")),
                "method_path_match"
                if match["status"] == "confirmed"
                else "candidate_match",
                [
                    *match["evidence"],
                    *endpoints[index]["evidence"],
                    {
                        "kind": "static_inference",
                        "rule": ASSOCIATION_RULE_VERSION + "." + match["reason"],
                        "source_ref": match["evidence"][0]["source_ref"],
                    },
                ],
            )
    return {"nodes": nodes, "edges": edges}
