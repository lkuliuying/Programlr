"""使用源码身份和唯一性比较，不跨分析匹配 UUID 或行号。"""

from collections import defaultdict
from typing import Any

from apps.analysis.diffs.types import (
    AnalysisInput,
    EndpointChange,
    RelationChange,
    SemanticChangeType,
)
from apps.analysis.graph import canonical
from apps.analysis.types import Evidence, GraphEdge, GraphNode, Symbol


def node_key(node: GraphNode) -> str:
    value: list[str | None]
    endpoint = node["endpoint"]
    if endpoint:
        value = [
            "endpoint",
            endpoint["method"],
            endpoint["path"],
            endpoint["path_kind"],
        ]
    else:
        ref = node["source_ref"]
        value = [node["kind"], ref["file_path"] if ref else None, node["name"]]
    return canonical(value)


def proof_key(items: list[Evidence]) -> set[str]:
    return {
        canonical(
            [
                item["kind"],
                item["rule"],
                item["source_ref"]["file_path"] if item["source_ref"] else None,
            ]
        )
        for item in items
    }


def kind(
    before: list[Any], after: list[Any], ambiguous: bool, changed: bool
) -> SemanticChangeType:
    if ambiguous:
        return "ambiguous"
    return (
        "added"
        if not before
        else "deleted"
        if not after
        else "modified"
        if changed
        else "unchanged"
    )


def compare_semantics(
    base: AnalysisInput, target: AnalysisInput
) -> tuple[list[EndpointChange], list[RelationChange]]:
    graphs = (base["graph"], target["graph"])
    assert all(graphs)
    node_maps = [
        {node["id"]: node for node in graph["nodes"]} for graph in graphs if graph
    ]
    key_groups: list[dict[str, list[GraphNode]]] = []
    for nodes in node_maps:
        groups: dict[str, list[GraphNode]] = defaultdict(list)
        for node in nodes.values():
            groups[node_key(node)].append(node)
        key_groups.append(groups)
    ambiguous = {
        key for groups in key_groups for key, nodes in groups.items() if len(nodes) != 1
    }
    edge_groups: list[dict[tuple[str, str, str], list[GraphEdge]]] = []
    incident: list[dict[str, set[str]]] = []
    for graph, nodes in zip(graphs, node_maps, strict=True):
        assert graph is not None
        edges: dict[tuple[str, str, str], list[GraphEdge]] = defaultdict(list)
        signatures: dict[str, set[str]] = defaultdict(set)
        for edge in graph["edges"]:
            edge_key: tuple[str, str, str] = (
                node_key(nodes[edge["source_id"]]),
                node_key(nodes[edge["target_id"]]),
                edge["relation"],
            )
            edges[edge_key].append(edge)
            if edge_key[0] not in ambiguous and edge_key[1] not in ambiguous:
                signature = canonical([edge_key, sorted(proof_key(edge["evidence"]))])
                signatures[edge_key[0]].add(signature)
                signatures[edge_key[1]].add(signature)
        edge_groups.append(edges)
        incident.append(signatures)
    relations: list[RelationChange] = []
    for key in sorted(edge_groups[0].keys() | edge_groups[1].keys()):
        before, after = edge_groups[0].get(key, []), edge_groups[1].get(key, [])
        old_proof = [proof for edge in before for proof in edge["evidence"]]
        new_proof = [proof for edge in after for proof in edge["evidence"]]
        source = key_groups[0].get(key[0]) or key_groups[1][key[0]]
        destination = key_groups[0].get(key[1]) or key_groups[1][key[1]]
        relations.append(
            {
                "relation": key[2],
                "source_name": source[0]["name"],
                "target_name": destination[0]["name"],
                "change_type": kind(
                    before,
                    after,
                    key[0] in ambiguous
                    or key[1] in ambiguous
                    or len(before) > 1
                    or len(after) > 1,
                    proof_key(old_proof) != proof_key(new_proof),
                ),
                "base_edge_ids": [edge["id"] for edge in before],
                "target_edge_ids": [edge["id"] for edge in after],
                "base_evidence": old_proof,
                "target_evidence": new_proof,
            }
        )
    endpoint_groups: list[dict[tuple[str, str, str], list[int]]] = []
    for analysis in (base, target):
        grouped: dict[tuple[str, str, str], list[int]] = defaultdict(list)
        for index, endpoint in enumerate(analysis["endpoints"]):
            grouped[endpoint["method"], endpoint["path"], endpoint["path_kind"]].append(
                index
            )
        endpoint_groups.append(grouped)
    interfaces: list[EndpointChange] = []
    for endpoint_key in sorted(endpoint_groups[0].keys() | endpoint_groups[1].keys()):
        before_indices, after_indices = (
            endpoint_groups[0].get(endpoint_key, []),
            endpoint_groups[1].get(endpoint_key, []),
        )
        fields: list[str] = []
        if len(before_indices) == len(after_indices) == 1:
            old, new = (
                base["endpoints"][before_indices[0]],
                target["endpoints"][after_indices[0]],
            )
            if old["action"] != new["action"]:
                fields.append("action")
            for field, left, right in (
                ("view", old["view"], new["view"]),
                ("serializer", old["serializer"], new["serializer"]),
                ("model", old["model"], new["model"]),
            ):

                def identity(symbol: Symbol | None) -> tuple[str, str] | None:
                    return (
                        (symbol["name"], symbol["source_ref"]["file_path"])
                        if symbol
                        else None
                    )

                if identity(left) != identity(right):
                    fields.append(field)
            graph_key = canonical(["endpoint", *endpoint_key])
            if incident[0].get(graph_key, set()) != incident[1].get(graph_key, set()):
                fields.append("relations")
        interfaces.append(
            {
                "method": endpoint_key[0],
                "path": endpoint_key[1],
                "path_kind": endpoint_key[2],
                "change_type": kind(
                    before_indices,
                    after_indices,
                    len(before_indices) > 1 or len(after_indices) > 1,
                    bool(fields),
                ),
                "base_indices": before_indices,
                "target_indices": after_indices,
                "changed_fields": fields,
                "base_evidence": [
                    proof
                    for i in before_indices
                    for proof in base["endpoints"][i]["evidence"]
                ],
                "target_evidence": [
                    proof
                    for i in after_indices
                    for proof in target["endpoints"][i]["evidence"]
                ],
            }
        )
    return interfaces, relations
