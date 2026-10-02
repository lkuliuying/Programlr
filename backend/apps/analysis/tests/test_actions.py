"""覆盖标准动作默认、继承、显式序列化器及不支持输入的失败边界。"""

import json
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

from apps.analysis.graph import build_graph, validate_graph
from apps.analysis.parser import analyze
from apps.analysis.protocol import validate_result
from apps.analysis.types import AnalysisFailed, AnalysisResult

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from check_analysis_rules import SNAPSHOT, backend_sources  # noqa: E402


def samples() -> list[dict[str, Any]]:
    return [
        case
        for group in ("development", "evaluation")
        for case in json.loads(
            (ROOT / f"testdata/analysis/v02-{group}.json").read_text(encoding="utf-8")
        )["cases"]
        if case["kind"] == "router"
    ]


@pytest.mark.parametrize("case", samples(), ids=lambda case: case["id"])
def test_action_datasets(case: dict[str, Any]) -> None:
    sources = backend_sources(case)
    result = validate_result(analyze(SNAPSHOT, sources, "urls.py"), SNAPSHOT, sources)
    actual = sorted(
        [
            e["method"],
            e["path"],
            e["action"],
            e["serializer"]["name"] if e["serializer"] else None,
        ]
        for e in result["endpoints"]
        if e["method"] not in {"HEAD", "OPTIONS"}
    )
    assert actual == sorted(case["expected_endpoints"])
    if case["supported"]:
        for endpoint in result["endpoints"]:
            assert any(
                e["rule"] == "drf.action" and e["source_ref"]
                for e in endpoint["evidence"]
            )
            assert any(e["rule"] == "drf.router_register" for e in endpoint["evidence"])
    else:
        assert result["diagnostics"]


@pytest.mark.parametrize("case", samples(), ids=lambda case: case["id"])
def test_action_results_publish_with_traceable_graph(case: dict[str, Any]) -> None:
    sources = backend_sources(case)
    result = validate_result(analyze(SNAPSHOT, sources, "urls.py"), SNAPSHOT, sources)
    graph = validate_graph(
        build_graph(uuid.UUID(int=2), result),
        SNAPSHOT,
        {
            source.file_path: max(1, len(source.content.splitlines()))
            for source in sources
        },
    )
    assert sum(node["kind"] == "endpoint" for node in graph["nodes"]) == len(
        result["endpoints"]
    )
    if case["id"] in {"detail-action-serializer", "inherited-action-path-router"}:
        serializer_edges = [
            edge for edge in graph["edges"] if edge["relation"] == "serializer_class"
        ]
        assert serializer_edges
        assert all(
            item["rule"] == "drf.action_serializer_class" and item["source_ref"]
            for edge in serializer_edges
            for item in edge["evidence"]
        )
        assert not any(
            item["rule"] == "drf.action_serializer_class"
            for edge in graph["edges"]
            if edge["relation"] == "route_view"
            for item in edge["evidence"]
        )


def parse_decorator(
    decorator: str, *, body: str = "", router: str = "SimpleRouter()"
) -> AnalysisResult:
    case = samples()[0].copy()
    case["view_source"] = str(case["view_source"]).replace(
        "@action(detail=False)", decorator
    )
    case["view_source"] = (
        str(case["view_source"]).replace(
            "    serializer_class = ItemSerializer",
            "    serializer_class = ItemSerializer\n" + body,
        )
        if body
        else case["view_source"]
    )
    case["router_source"] = (
        str(case["router_source"])
        .replace("SimpleRouter()", router)
        .replace("import SimpleRouter", "import SimpleRouter, DefaultRouter")
    )
    sources = backend_sources(case)
    return validate_result(analyze(SNAPSHOT, sources, "urls.py"), SNAPSHOT, sources)


@pytest.mark.parametrize(
    "decorator",
    [
        "@action()",
        "@action(detail=None)",
        "@action(detail=1)",
        "@action(False)",
        "@action(detail=False, methods=['bad'])",
        "@action(detail=False, methods=[123])",
        "@action(detail=False, url_path=choose())",
        "@action(detail=False, serializer_class=choose())",
        "@action(detail=False, **config)",
        "@action(detail=False, url_name=123)",
        "@other\n    @action(detail=False)",
    ],
)
def test_dynamic_and_invalid_action_parameters_are_not_published(
    decorator: str,
) -> None:
    result = parse_decorator(decorator)
    assert not result["endpoints"]
    assert any(d["code"] == "CUSTOM_ACTION_UNRESOLVED" for d in result["diagnostics"])


@pytest.mark.parametrize(
    "decorator",
    [
        "@action(detail=False, url_path='')",
        "@action(detail=False, methods=None, url_path=None, url_name=None)",
    ],
)
def test_framework_falsey_defaults(decorator: str) -> None:
    result = parse_decorator(decorator)
    assert {e["method"] for e in result["endpoints"]} == {"GET", "HEAD", "OPTIONS"}
    assert all(e["path"] == "/api/items/recent_items/$" for e in result["endpoints"])


def test_empty_methods_follow_locked_framework_instead_of_defaulting() -> None:
    from django.http import HttpResponse
    from rest_framework.decorators import action

    def controlled_action() -> HttpResponse:
        return HttpResponse()

    decorated = action(detail=False, methods=[])(controlled_action)
    assert not decorated.mapping
    assert not parse_decorator("@action(detail=False, methods=[])")["endpoints"]


@pytest.mark.parametrize(
    "body", ["    action = choose()", "    def action(self):\n        pass"]
)
def test_class_scope_shadowing_does_not_use_module_decorator(body: str) -> None:
    assert not parse_decorator("@action(detail=False)", body=body)["endpoints"]


def test_secondary_mapping_and_reserved_action_are_not_guessed() -> None:
    case = samples()[0].copy()
    case["view_source"] = (
        str(case["view_source"])
        + "    @recent_items.mapping.post\n    def post_recent(self, request):\n        pass\n"
    )
    assert not analyze(SNAPSHOT, backend_sources(case), "urls.py")["endpoints"]
    case["view_source"] = (
        str(case["view_source"])
        .split("    @recent_items.mapping")[0]
        .replace("recent_items", "list")
    )
    result = analyze(SNAPSHOT, backend_sources(case), "urls.py")
    assert not result["endpoints"] and any(
        d["code"] == "INVALID_ACTION" for d in result["diagnostics"]
    )


def test_default_router_suffixes_method_filter_and_inherited_override() -> None:
    result = parse_decorator("@action(detail=False)", router="DefaultRouter()")
    assert any(
        e["path"] == r"/api/items/recent_items\.(?P<format>[a-z0-9]+)/?$"
        for e in result["endpoints"]
    )
    filtered = parse_decorator(
        "@action(detail=False)", body="    http_method_names = ['get']"
    )
    assert [e["method"] for e in filtered["endpoints"]] == ["GET"]
    case = samples()[5].copy()
    case["view_source"] = str(case["view_source"]).replace(
        "class ItemViewSet(Base):\n    pass",
        "class ItemViewSet(Base):\n    def summarize(self, request):\n        pass",
    )
    assert not analyze(SNAPSHOT, backend_sources(case), "urls.py")["endpoints"]


def test_action_output_budget_is_still_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("apps.analysis.parser.MAX_RESULTS", 1)
    with pytest.raises(AnalysisFailed):
        parse_decorator("@action(detail=False)")


def test_old_rule_baseline_and_dataset_identity_are_preserved() -> None:
    import hashlib

    baseline = json.loads(
        (ROOT / "testdata/analysis/v02-old-rule-baseline.json").read_text(
            encoding="utf-8"
        )
    )
    assert baseline["backend_rule_version"] == "python-drf/1.0.0"
    assert baseline["frontend_rule_version"] == "typescript-react/1.0.0"
    for group in ("development", "evaluation"):
        data = ROOT / f"testdata/analysis/v02-{group}.json"
        assert (
            hashlib.sha256(data.read_bytes()).hexdigest()
            == baseline["groups"][group]["dataset_sha256"]
        )
