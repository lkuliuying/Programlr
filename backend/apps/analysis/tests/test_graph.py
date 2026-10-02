import json
import uuid
from copy import deepcopy
from typing import Any

import pytest

from apps.analysis.graph import build_graph, select_graph, validate_graph
from apps.analysis.parser import analyze
from apps.analysis.protocol import validate_result
from apps.analysis.tests.test_parser import ROOT, SNAPSHOT_ID, fixture_sources, replace
from apps.analysis.types import AnalysisFailed, GraphData, GraphQuery, Source

ANALYSIS_ID = uuid.UUID(int=2)


def parsed_graph(sources: list[Source], root: str = "root_urls.py") -> GraphData:
    result = validate_result(analyze(SNAPSHOT_ID, sources, root), SNAPSHOT_ID, sources)
    return validate_graph(
        build_graph(ANALYSIS_ID, result),
        SNAPSHOT_ID,
        {s.file_path: max(1, len(s.content.splitlines())) for s in sources},
    )


@pytest.mark.parametrize("fixture", ["task-board", "drf-static"])
def test_graph_matches_manual_backend_projection(fixture: str) -> None:
    expected = json.loads(
        (ROOT / "testdata/analysis/graph-expected.json").read_text(encoding="utf-8")
    )
    case = next(c for c in expected["cases"] if c["fixture"] == fixture)
    if fixture == "task-board":
        example = ROOT / "examples/task-board"
        sources = [
            Source(p.relative_to(example).as_posix(), p.read_text(encoding="utf-8"))
            for folder in (example / "backend/apps", example / "backend/config")
            for p in sorted(folder.rglob("*.py"))
        ]
        graph = parsed_graph(sources, "backend/config/urls.py")
        baseline = json.loads(
            (ROOT / "testdata/analysis/task-board-create.json").read_text(
                encoding="utf-8"
            )
        )
        references = {n["id"]: n["source_ref"] for n in baseline["nodes"]}
    else:
        graph = parsed_graph(fixture_sources())
        references = json.loads(
            (ROOT / "testdata/analysis/drf-static-expected.json").read_text(
                encoding="utf-8"
            )
        )
    root = next(
        n
        for n in graph["nodes"]
        if n["endpoint"] is not None
        and n["endpoint"]["method"] == case["method"]
        and n["endpoint"]["path"] == case["path"]
    )
    selected = select_graph(graph, GraphQuery(root_node_id=root["id"]))
    assert selected["returned_nodes"] == 4 and selected["returned_edges"] == 3
    assert not selected["truncated"]
    by_id = {n["id"]: n for n in selected["nodes"]}
    assert sorted(
        [by_id[e["source_id"]]["kind"], by_id[e["target_id"]]["kind"], e["relation"]]
        for e in selected["edges"]
    ) == sorted(expected["relations"])
    for node in selected["nodes"]:
        if node["kind"] == "endpoint":
            continue
        assert node["name"] == case["symbols"][node["kind"]]
        ref = node["source_ref"]
        assert ref is not None
        expected_ref = references[node["kind"]]
        assert ref["snapshot_id"] == SNAPSHOT_ID
        assert ref["file_path"] == expected_ref["file_path"]
        assert ref["start_line"] == expected_ref["start_line"]
        assert ref["end_line"] >= expected_ref["end_line"]
    action = next(e for e in root["evidence"] if e["rule"] == case["action_rule"])
    assert action["kind"] == case["action_evidence_kind"]
    if fixture == "drf-static":
        assert action["source_ref"] is None
        route = next(e for e in root["evidence"] if e["rule"] == "drf.router_register")
        assert route["source_ref"] == {
            "snapshot_id": SNAPSHOT_ID,
            **references["registration"],
        }
    else:
        for key in ("root_route", "route"):
            assert any(
                e["source_ref"] is not None
                and all(
                    e["source_ref"][field] == references[key][field]
                    for field in ("file_path", "start_line", "end_line")
                )
                for e in root["evidence"]
            )
    for edge in selected["edges"]:
        if edge["relation"] != "route_view":
            assert {e["kind"] for e in edge["evidence"]} == {"static_inference"}


def test_shared_symbols_candidates_and_stable_ids() -> None:
    result = analyze(SNAPSHOT_ID, fixture_sources(), "root_urls.py")
    result["endpoints"].append(deepcopy(result["endpoints"][0]))
    graph = build_graph(ANALYSIS_ID, result)
    assert graph == build_graph(ANALYSIS_ID, result)
    assert len(graph["nodes"]) == len(result["endpoints"]) + 3
    assert len(graph["edges"]) == len(result["endpoints"]) + 2
    candidates = [
        n for n in graph["nodes"] if n["endpoint"] and n["endpoint"]["is_candidate"]
    ]
    assert len(candidates) == 2 and candidates[0]["id"] != candidates[1]["id"]
    other = build_graph(uuid.UUID(int=3), result)
    assert not ({n["id"] for n in graph["nodes"]} & {n["id"] for n in other["nodes"]})


def test_dynamic_and_cyclic_routes_keep_gaps_and_diagnostics() -> None:
    dynamic = replace(
        fixture_sources(),
        "views.py",
        "serializer_class = TaskSerializer",
        "def get_serializer_class(self): return choose()",
    )
    graph = parsed_graph(dynamic)
    assert {n["kind"] for n in graph["nodes"]} == {"endpoint", "view"}
    assert {e["relation"] for e in graph["edges"]} == {"route_view"}
    cyclic = replace(
        fixture_sources(),
        "root_urls.py",
        'include("router_urls")',
        'include("root_urls")',
    )
    result = analyze(SNAPSHOT_ID, cyclic, "root_urls.py")
    assert any(d["code"] == "ROUTE_CYCLE" for d in result["diagnostics"])
    assert build_graph(ANALYSIS_ID, result) == {"nodes": [], "edges": []}


def test_framework_api_root_remains_an_isolated_endpoint() -> None:
    graph = parsed_graph(
        replace(fixture_sources(), "router_urls.py", "SimpleRouter", "DefaultRouter")
    )
    root = next(
        n
        for n in graph["nodes"]
        if n["endpoint"] and n["endpoint"]["action"] == "api_root"
    )
    selected = select_graph(graph, GraphQuery(root_node_id=root["id"]))
    assert selected["nodes"] == [root] and selected["edges"] == []
    assert not selected["truncated"]


def synthetic_graph() -> GraphData:
    evidence: Any = [
        {
            "kind": "source_fact",
            "rule": "test.symbol",
            "source_ref": {
                "snapshot_id": SNAPSHOT_ID,
                "file_path": "synthetic.py",
                "start_line": 1,
                "end_line": 1,
            },
        }
    ]
    ids = {label: str(uuid.uuid5(ANALYSIS_ID, label)) for label in "ABCDE"}
    return {
        "nodes": [
            {
                "id": ids[label],
                "kind": "view",
                "name": label,
                "source_ref": evidence[0]["source_ref"],
                "evidence": deepcopy(evidence),
                "endpoint": None,
            }
            for label in ids
        ],
        "edges": [
            {
                "id": str(uuid.uuid5(ANALYSIS_ID, pair)),
                "source_id": ids[pair[0]],
                "target_id": ids[pair[1]],
                "relation": "route_view",
                "evidence": deepcopy(evidence),
            }
            for pair in ("AB", "AC", "BD", "CD", "DA", "AA")
        ],
    }


def test_bfs_dfs_cycles_diamond_and_disconnected_components() -> None:
    graph = synthetic_graph()
    bfs = select_graph(graph, GraphQuery())
    dfs = select_graph(graph, GraphQuery(algorithm="dfs"))
    assert [n["name"] for n in bfs["nodes"]] == list("ABCDE")
    assert [n["name"] for n in dfs["nodes"]] == list("ABDCE")
    assert bfs["returned_edges"] == dfs["returned_edges"] == 6
    assert not bfs["truncated"] and not dfs["truncated"]
    graph["nodes"].reverse()
    graph["edges"].reverse()
    assert select_graph(graph, GraphQuery()) == bfs


@pytest.mark.parametrize("algorithm", ["bfs", "dfs"])
def test_limits_are_exact_and_do_not_create_dangling_edges(algorithm: Any) -> None:
    graph = synthetic_graph()
    root = graph["nodes"][0]["id"]
    isolated = graph["nodes"][-1]["id"]
    assert not select_graph(
        graph,
        GraphQuery(root_node_id=root, algorithm=algorithm, max_nodes=4, max_edges=6),
    )["truncated"]
    assert select_graph(graph, GraphQuery(root_node_id=isolated))["returned_nodes"] == 1
    limited = select_graph(
        graph, GraphQuery(algorithm=algorithm, max_nodes=2, max_edges=1)
    )
    assert limited["truncation_reasons"] == ["max_nodes", "max_edges"]
    ids = {n["id"] for n in limited["nodes"]}
    assert all(
        e["source_id"] in ids and e["target_id"] in ids for e in limited["edges"]
    )
    with pytest.raises(KeyError):
        select_graph(graph, GraphQuery(root_node_id=str(uuid.uuid4())))


def test_empty_graph_and_invalid_algorithm_budgets() -> None:
    graph: GraphData = {"nodes": [], "edges": []}
    empty = select_graph(graph, GraphQuery())
    assert empty["returned_nodes"] == empty["returned_edges"] == 0
    assert not empty["truncated"]
    for kwargs in (
        {"algorithm": "other"},
        {"max_nodes": 0},
        {"max_nodes": True},
        {"max_nodes": 1001},
        {"max_edges": 2001},
    ):
        with pytest.raises(ValueError):
            select_graph(graph, GraphQuery(**kwargs))


@pytest.mark.parametrize(
    "case",
    [
        "duplicate_node",
        "duplicate_edge",
        "dangling",
        "foreign",
        "range",
        "missing_file",
        "missing_evidence",
        "null_fact",
        "invalid_kind",
        "invalid_id",
        "invalid_shape",
    ],
)
def test_graph_validator_rejects_invalid_persisted_results(case: str) -> None:
    graph: Any = synthetic_graph()
    if case == "duplicate_node":
        graph["nodes"].append(graph["nodes"][0])
    elif case == "duplicate_edge":
        graph["edges"].append(graph["edges"][0])
    elif case == "dangling":
        graph["edges"][0]["target_id"] = str(uuid.uuid4())
    elif case == "foreign":
        graph["edges"][0]["evidence"][0]["source_ref"]["snapshot_id"] = str(
            uuid.uuid4()
        )
    elif case == "range":
        graph["nodes"][0]["source_ref"]["end_line"] = 2
    elif case == "missing_file":
        graph["nodes"][0]["source_ref"]["file_path"] = "missing.py"
    elif case == "missing_evidence":
        graph["edges"][0]["evidence"] = []
    elif case == "null_fact":
        graph["edges"][0]["evidence"][0]["source_ref"] = None
    elif case == "invalid_kind":
        graph["nodes"][0]["kind"] = []
    elif case == "invalid_id":
        graph["nodes"][0]["id"] = "x" * 36
    else:
        graph["nodes"][0] = None
    with pytest.raises(AnalysisFailed, match="静态分析") as error:
        validate_graph(graph, SNAPSHOT_ID, {"synthetic.py": 1})
    assert error.value.reason == "invalid_graph_result"


def test_storage_budgets_and_missing_relation_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = synthetic_graph()
    size = len(json.dumps(graph, ensure_ascii=False, separators=(",", ":")).encode())
    monkeypatch.setattr("apps.analysis.graph.MAX_GRAPH_BYTES", size)
    assert validate_graph(graph, SNAPSHOT_ID, {"synthetic.py": 1}) == graph
    monkeypatch.setattr("apps.analysis.graph.MAX_GRAPH_BYTES", size - 1)
    with pytest.raises(AnalysisFailed) as error:
        validate_graph(graph, SNAPSHOT_ID, {"synthetic.py": 1})
    assert error.value.reason == "graph_limit"
    monkeypatch.setattr("apps.analysis.graph.MAX_GRAPH_NODES", 1)
    with pytest.raises(AnalysisFailed):
        validate_graph(graph, SNAPSHOT_ID, {"synthetic.py": 1})
    result = analyze(SNAPSHOT_ID, fixture_sources(), "root_urls.py")
    with pytest.raises(AnalysisFailed):
        build_graph(ANALYSIS_ID, result)
    monkeypatch.setattr("apps.analysis.graph.MAX_GRAPH_NODES", 40000)
    monkeypatch.setattr("apps.analysis.graph.MAX_GRAPH_EDGES", 1)
    with pytest.raises(AnalysisFailed) as error:
        validate_graph(graph, SNAPSHOT_ID, {"synthetic.py": 1})
    assert error.value.reason == "graph_limit"
    with pytest.raises(AnalysisFailed):
        build_graph(ANALYSIS_ID, result)
    monkeypatch.setattr("apps.analysis.graph.MAX_GRAPH_EDGES", 30000)
    result["endpoints"][0]["evidence"] = [
        e
        for e in result["endpoints"][0]["evidence"]
        if e["rule"] != "drf.serializer_class"
    ]
    with pytest.raises(AnalysisFailed) as error:
        build_graph(ANALYSIS_ID, result)
    assert error.value.reason == "invalid_graph_result"
