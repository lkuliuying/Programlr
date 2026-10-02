"""有界反向遍历，每个结果保留一条来自原图的依赖路径。"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import TYPE_CHECKING, TypedDict

from apps.analysis.types import GraphData, GraphEdge, GraphNode, SourceRef

if TYPE_CHECKING:
    from apps.analysis.reviews import ReviewDecision


class ImpactResult(TypedDict):
    node: GraphNode
    path_node_ids: list[str]
    path_edge_ids: list[str]
    via_candidate: bool


class ImpactSelection(TypedDict):
    starts: list[str]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    results: list[ImpactResult]
    relation_reviews: list[ReviewDecision]
    visited_nodes: int
    visited_edges: int
    truncated: bool
    truncation_reasons: list[str]


def eligible_graph(
    graph: GraphData, reviews: list[ReviewDecision], include_candidates: bool
) -> GraphData:
    decisions = {
        (item["request_id"], item["target_id"]): item["decision"] for item in reviews
    }
    return {
        "nodes": graph["nodes"],
        "edges": [
            edge
            for edge in graph["edges"]
            if edge["relation"] != "candidate_match"
            or decisions[(edge["source_id"], edge["target_id"])] == "confirmed"
            or (
                include_candidates
                and decisions[(edge["source_id"], edge["target_id"])] == "undecided"
            )
        ],
    }


def overlaps(left: SourceRef | None, right: SourceRef) -> bool:
    return bool(
        left
        and left["snapshot_id"] == right["snapshot_id"]
        and left["file_path"] == right["file_path"]
        and left["start_line"] <= right["end_line"]
        and right["start_line"] <= left["end_line"]
    )


def change_starts(
    graph: GraphData, references: list[SourceRef]
) -> tuple[list[str], list[str]]:
    by_file: dict[str, list[SourceRef]] = defaultdict(list)
    for ref in references:
        by_file[ref["file_path"]].append(ref)
    starts, covered = set(), set()

    def matched(ref: SourceRef | None) -> bool:
        if ref and any(
            overlaps(ref, change) for change in by_file.get(ref["file_path"], [])
        ):
            covered.add(ref["file_path"])
            return True
        return False

    for node in graph["nodes"]:
        if matched(node["source_ref"]) or any(
            matched(proof["source_ref"]) for proof in node["evidence"]
        ):
            starts.add(node["id"])
    for edge in graph["edges"]:
        if any(matched(proof["source_ref"]) for proof in edge["evidence"]):
            starts.update((edge["source_id"], edge["target_id"]))
    return sorted(starts), sorted(by_file.keys() - covered)


def reverse_impact(
    graph: GraphData,
    starts: list[str],
    reviews: list[ReviewDecision],
    *,
    include_candidates: bool,
    max_nodes: int,
    max_edges: int,
) -> ImpactSelection:
    nodes = {node["id"]: node for node in graph["nodes"]}
    if any(identity not in nodes for identity in starts):
        raise KeyError("起点不属于对应图。")
    decisions = {(item["request_id"], item["target_id"]): item for item in reviews}
    incoming: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in graph["edges"]:
        if edge["relation"] == "candidate_match":
            choice = decisions[(edge["source_id"], edge["target_id"])]["decision"]
            if choice == "excluded" or (
                choice == "undecided" and not include_candidates
            ):
                continue
        incoming[edge["target_id"]].append(edge)
    for edges in incoming.values():
        edges.sort(
            key=lambda edge: (
                edge["relation"] == "candidate_match",
                edge["source_id"],
                edge["id"],
            )
        )
    # 先寻找仅依赖静态或人工确认的路径，再扩展未决候选，避免候选捷径掩盖可靠路径。
    paths: dict[str, tuple[list[str], list[str], bool]] = {}
    selected_edges: dict[str, GraphEdge] = {}
    reasons: list[str] = []
    unique_starts = sorted(set(starts))
    for identity in unique_starts[:max_nodes]:
        paths[identity] = ([identity], [], False)
    if len(unique_starts) > max_nodes:
        reasons.append("max_nodes")
    deferred: list[tuple[str, GraphEdge]] = []
    pending = deque(paths)

    def visit(identity: str, edge: GraphEdge) -> None:
        source = edge["source_id"]
        if edge["id"] not in selected_edges:
            if len(selected_edges) >= max_edges:
                if "max_edges" not in reasons:
                    reasons.append("max_edges")
                return
            if source not in paths and len(paths) >= max_nodes:
                if "max_nodes" not in reasons:
                    reasons.append("max_nodes")
                return
            selected_edges[edge["id"]] = edge
        if source in paths:
            return
        node_path, edge_path, candidate = paths[identity]
        unresolved = (
            edge["relation"] == "candidate_match"
            and decisions[(edge["source_id"], edge["target_id"])]["decision"]
            == "undecided"
        )
        paths[source] = (
            [source, *node_path],
            [edge["id"], *edge_path],
            candidate or unresolved,
        )
        pending.append(source)

    while pending or deferred:
        if not pending:
            batch, deferred = deferred, []
            for identity, edge in batch:
                visit(identity, edge)
        while pending:
            identity = pending.popleft()
            for edge in incoming.get(identity, []):
                unresolved = (
                    edge["relation"] == "candidate_match"
                    and decisions[(edge["source_id"], edge["target_id"])]["decision"]
                    == "undecided"
                )
                if unresolved and not paths[identity][2]:
                    deferred.append((identity, edge))
                else:
                    visit(identity, edge)
    used_reviews = [
        decisions[(edge["source_id"], edge["target_id"])]
        for edge in selected_edges.values()
        if edge["relation"] == "candidate_match"
    ]
    return {
        "starts": [identity for identity in unique_starts if identity in paths],
        "nodes": [nodes[identity] for identity in paths],
        "edges": list(selected_edges.values()),
        "results": [
            {
                "node": nodes[identity],
                "path_node_ids": path[0],
                "path_edge_ids": path[1],
                "via_candidate": path[2],
            }
            for identity, path in paths.items()
            if nodes[identity]["kind"]
            in {"endpoint", "frontend_request", "frontend_function"}
        ],
        "relation_reviews": used_reviews,
        "visited_nodes": len(paths),
        "visited_edges": len(selected_edges),
        "truncated": bool(reasons),
        "truncation_reasons": reasons,
    }
