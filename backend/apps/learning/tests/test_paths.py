import pytest

from apps.learning.paths.graph import MAX_EDGES, MAX_NODES, build_graph


def edge(source: str, target: str) -> dict[str, str]:
    return {"prerequisite": source, "dependent": target}


def test_closure_order_branches_independent_nodes_and_stability() -> None:
    nodes = ["d", "b", "z", "a", "c"]
    edges = [edge("a", "b"), edge("a", "c"), edge("b", "d"), edge("c", "d")]
    graph = build_graph(nodes, edges)
    assert graph.order_for(["d"]) == ["a", "b", "c", "d"]
    assert graph.order_for(["b", "z"]) == ["a", "b", "z"]
    assert build_graph(list(reversed(nodes)), list(reversed(edges))).order_for(
        ["d"]
    ) == graph.order_for(["d"])
    assert build_graph(["a"], []).order_for(["a"]) == ["a"]


@pytest.mark.parametrize(
    ("nodes", "edges"),
    [
        ([], []),
        (["a", "a"], []),
        (["../a"], []),
        (["a", True], []),
        (["a"], [edge("a", "a")]),
        (["a"], [edge("a", "b")]),
        (["a", "b"], [edge("a", "b"), edge("a", "b")]),
        (["a", "b"], [edge("a", "b"), edge("b", "a")]),
        (["a", "b", "c"], [edge("b", "c"), edge("c", "b")]),
        (["a"], [{"prerequisite": "a"}]),
        (["a"], [{"prerequisite": [], "dependent": "a"}]),
        ([f"n{i}" for i in range(MAX_NODES + 1)], []),
        (["a", "b"], [edge("a", "b")] * (MAX_EDGES + 1)),
    ],
)
def test_invalid_entire_configuration_rejected(
    nodes: list[str], edges: list[dict[str, str]]
) -> None:
    with pytest.raises(ValueError):
        build_graph(nodes, edges)


@pytest.mark.parametrize("targets", [[], ["unknown"], ["a", "a"], [True]])
def test_invalid_targets_rejected(targets: list[str]) -> None:
    with pytest.raises(ValueError):
        build_graph(["a"], []).order_for(targets)


def test_boundary_chain_completes_without_recursion() -> None:
    nodes = [f"n{i:03}" for i in range(MAX_NODES)]
    graph = build_graph(
        nodes, [edge(nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1)]
    )
    assert graph.order_for([nodes[-1]]) == nodes
