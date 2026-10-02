"""知识先修图的纯算法；代码依赖图的环规则不适用于这里。"""

import heapq
import re
from dataclasses import dataclass

MAX_NODES = 100
MAX_EDGES = 400
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")


@dataclass(frozen=True)
class PrerequisiteGraph:
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]

    def order_for(self, targets: list[str]) -> list[str]:
        if (
            not isinstance(targets, list)
            or not targets
            or any(
                not isinstance(item, str) or item not in self.nodes for item in targets
            )
            or len(set(targets)) != len(targets)
        ):
            raise ValueError("学习目标缺失、重复或引用未知知识点。")
        parents: dict[str, set[str]] = {node: set() for node in self.nodes}
        children: dict[str, set[str]] = {node: set() for node in self.nodes}
        for source, target in self.edges:
            parents[target].add(source)
            children[source].add(target)
        required, pending = set(targets), list(targets)
        while pending:
            for parent in parents[pending.pop()]:
                if parent not in required:
                    required.add(parent)
                    pending.append(parent)
        degrees = {node: len(parents[node] & required) for node in required}
        ready = [node for node, degree in degrees.items() if degree == 0]
        heapq.heapify(ready)
        result: list[str] = []
        while ready:
            node = heapq.heappop(ready)
            result.append(node)
            for child in sorted(children[node] & required):
                degrees[child] -= 1
                if degrees[child] == 0:
                    heapq.heappush(ready, child)
        if len(result) != len(required):
            raise ValueError("知识先修关系存在环，不能发布。")
        return result


def build_graph(nodes: list[str], edges: list[dict[str, str]]) -> PrerequisiteGraph:
    if (
        not isinstance(nodes, list)
        or not isinstance(edges, list)
        or not 1 <= len(nodes) <= MAX_NODES
        or any(not isinstance(node, str) or not SLUG.fullmatch(node) for node in nodes)
        or len(set(nodes)) != len(nodes)
        or len(edges) > MAX_EDGES
    ):
        raise ValueError("知识点缺失、重复、标识无效或超过上限。")
    pairs: set[tuple[str, str]] = set()
    for edge in edges:
        if (
            not isinstance(edge, dict)
            or set(edge) != {"prerequisite", "dependent"}
            or not isinstance(edge["prerequisite"], str)
            or not isinstance(edge["dependent"], str)
        ):
            raise ValueError("先修边结构无效。")
        pair = edge["prerequisite"], edge["dependent"]
        if (
            pair[0] not in nodes
            or pair[1] not in nodes
            or pair[0] == pair[1]
            or pair in pairs
        ):
            raise ValueError("先修边引用未知节点、自身或重复关系。")
        pairs.add(pair)
    graph = PrerequisiteGraph(tuple(sorted(nodes)), tuple(sorted(pairs)))
    graph.order_for(list(graph.nodes))
    return graph
