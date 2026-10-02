"""验证共享依赖、环、候选路径和预算截断。"""

import uuid
from typing import Literal, cast

from apps.analysis.impact import change_starts, eligible_graph, reverse_impact
from apps.analysis.reviews import ReviewDecision
from apps.analysis.types import (
    GraphData,
    GraphEdge,
    GraphNode,
    GraphRelation,
    SourceRef,
)


def identity(index: int) -> str:
    return str(uuid.UUID(int=index))


def graph() -> GraphData:
    nodes: list[GraphNode] = []
    for index, kind in enumerate(
        (
            "model",
            "serializer",
            "view",
            "endpoint",
            "frontend_request",
            "frontend_function",
            "endpoint",
            "frontend_function",
        ),
        1,
    ):
        nodes.append(
            {
                "id": identity(index),
                "kind": cast(
                    Literal[
                        "endpoint",
                        "view",
                        "serializer",
                        "model",
                        "frontend_function",
                        "frontend_request",
                    ],
                    kind,
                ),
                "name": kind + str(index),
                "source_ref": {
                    "snapshot_id": identity(100),
                    "file_path": kind + ".py",
                    "start_line": 1,
                    "end_line": 10,
                },
                "evidence": [],
                "endpoint": None,
            }
        )

    def edge(
        index: int, source: int, target: int, relation: GraphRelation
    ) -> GraphEdge:
        return {
            "id": identity(index),
            "source_id": identity(source),
            "target_id": identity(target),
            "relation": relation,
            "evidence": [],
        }

    return {
        "nodes": nodes,
        "edges": [
            edge(11, 2, 1, "meta_model"),
            edge(12, 3, 2, "serializer_class"),
            edge(13, 4, 3, "route_view"),
            edge(14, 5, 4, "candidate_match"),
            edge(15, 6, 5, "contains_request"),
            edge(16, 7, 3, "route_view"),
            edge(17, 8, 6, "direct_call"),
            edge(18, 6, 8, "direct_call"),
        ],
    }


def reviews(decision: str = "undecided") -> list[ReviewDecision]:
    return [
        {
            "request_id": identity(5),
            "target_id": identity(4),
            "revision": 0 if decision == "undecided" else 1,
            "decision": cast(Literal["confirmed", "excluded", "undecided"], decision),
        }
    ]


def test_shared_dependency_cycle_and_every_path_belongs_to_graph() -> None:
    source = graph()
    result = reverse_impact(
        source,
        [identity(1)],
        reviews(),
        include_candidates=True,
        max_nodes=200,
        max_edges=400,
    )
    assert not result["truncated"] and result["visited_nodes"] == 8
    results = {item["node"]["id"]: item for item in result["results"]}
    assert results[identity(4)]["via_candidate"] is False
    assert results[identity(6)]["via_candidate"] is True
    edges = {edge["id"]: edge for edge in source["edges"]}
    for item in result["results"]:
        assert item["path_node_ids"][0] == item["node"]["id"]
        assert item["path_node_ids"][-1] == identity(1)
        assert len(item["path_edge_ids"]) + 1 == len(item["path_node_ids"])
        for offset, edge_id in enumerate(item["path_edge_ids"]):
            assert edges[edge_id]["source_id"] == item["path_node_ids"][offset]
            assert edges[edge_id]["target_id"] == item["path_node_ids"][offset + 1]


def test_candidate_default_confirmation_exclusion_and_reliable_path_precedence() -> (
    None
):
    source = graph()

    def run(choice: str, include: bool) -> set[str]:
        return {
            item["node"]["id"]
            for item in reverse_impact(
                source,
                [identity(1)],
                reviews(choice),
                include_candidates=include,
                max_nodes=200,
                max_edges=400,
            )["results"]
        }

    assert identity(5) not in run("undecided", False)
    assert identity(5) in run("confirmed", False)
    assert identity(5) not in run("excluded", True)
    source["edges"].append(
        {
            "id": identity(19),
            "source_id": identity(5),
            "target_id": identity(7),
            "relation": "method_path_match",
            "evidence": [],
        }
    )
    result = reverse_impact(
        source,
        [identity(1)],
        reviews(),
        include_candidates=True,
        max_nodes=200,
        max_edges=400,
    )
    assert not next(
        item for item in result["results"] if item["node"]["id"] == identity(5)
    )["via_candidate"]


def test_isolated_no_results_and_node_edge_budgets() -> None:
    source = graph()
    source["nodes"].append(
        {
            "id": identity(9),
            "kind": "model",
            "name": "isolated",
            "source_ref": None,
            "evidence": [],
            "endpoint": None,
        }
    )
    isolated = reverse_impact(
        source,
        [identity(9)],
        reviews(),
        include_candidates=False,
        max_nodes=200,
        max_edges=400,
    )
    assert isolated["results"] == [] and not isolated["truncated"]
    limited = reverse_impact(
        source,
        [identity(1)],
        reviews(),
        include_candidates=True,
        max_nodes=2,
        max_edges=400,
    )
    assert (
        limited["truncated"]
        and limited["visited_nodes"] == 2
        and "max_nodes" in limited["truncation_reasons"]
    )
    limited = reverse_impact(
        source,
        [identity(1)],
        reviews(),
        include_candidates=True,
        max_nodes=200,
        max_edges=1,
    )
    assert (
        limited["truncated"]
        and limited["visited_edges"] == 1
        and "max_edges" in limited["truncation_reasons"]
    )


def test_route_evidence_locates_change_but_excluded_candidates_do_not_seed_requests() -> (
    None
):
    source = graph()
    ref: SourceRef = {
        "snapshot_id": identity(100),
        "file_path": "urls.py",
        "start_line": 2,
        "end_line": 2,
    }
    for edge in source["edges"]:
        if edge["relation"] in {"route_view", "candidate_match"}:
            edge["evidence"] = [
                {"kind": "source_fact", "rule": "synthetic.route", "source_ref": ref}
            ]
    starts, missing = change_starts(
        eligible_graph(source, reviews("excluded"), True),
        [ref, {**ref, "file_path": "unknown.py"}],
    )
    assert (
        identity(4) in starts
        and identity(5) not in starts
        and missing == ["unknown.py"]
    )
    starts, _ = change_starts(eligible_graph(source, reviews(), False), [ref])
    assert identity(5) not in starts
