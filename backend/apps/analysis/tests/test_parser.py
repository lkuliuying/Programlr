import json
import uuid
from pathlib import Path

import pytest

from apps.analysis.parser import analyze
from apps.analysis.protocol import validate_result
from apps.analysis.types import AnalysisFailed, Source

ROOT = Path(__file__).resolve().parents[4]
SNAPSHOT_ID = str(uuid.UUID(int=1))


def fixture_sources() -> list[Source]:
    return [
        Source(p.name, p.read_text(encoding="utf-8"))
        for p in sorted((ROOT / "testdata/analysis/drf-static").glob("*.py"))
    ]


def replace(sources: list[Source], path: str, before: str, after: str) -> list[Source]:
    return [
        Source(s.file_path, s.content.replace(before, after))
        if s.file_path == path
        else s
        for s in sources
    ]


def test_router_matches_manual_annotations_and_framework_evidence() -> None:
    sources = fixture_sources()
    expected = json.loads(
        (ROOT / "testdata/analysis/drf-static-expected.json").read_text(
            encoding="utf-8"
        )
    )
    result = validate_result(
        analyze(SNAPSHOT_ID, sources, "root_urls.py"), SNAPSHOT_ID, sources
    )
    primary = [e for e in result["endpoints"] if e["method"] not in {"HEAD", "OPTIONS"}]
    assert sorted([e["method"], e["path"], e["action"]] for e in primary) == sorted(
        expected["endpoints"]
    )
    assert result["coverage"]["complete"]
    for endpoint in primary:
        assert endpoint["path_kind"] == "router_regex"
        for field in ("view", "serializer", "model"):
            symbol = endpoint[field]
            assert symbol is not None
            assert symbol["source_ref"] == {
                "snapshot_id": SNAPSHOT_ID,
                **expected[field],
            }
        assert any(
            e["source_ref"] == {"snapshot_id": SNAPSHOT_ID, **expected["registration"]}
            for e in endpoint["evidence"]
        )
        action = next(
            e
            for e in endpoint["evidence"]
            if e["rule"] == "drf/3.18.1." + endpoint["action"]
        )
        assert action["kind"] == "framework_rule" and action["source_ref"] is None


def test_task_board_matches_existing_manual_backend_baseline() -> None:
    example = ROOT / "examples/task-board"
    sources = [
        Source(p.relative_to(example).as_posix(), p.read_text(encoding="utf-8"))
        for folder in (example / "backend/apps", example / "backend/config")
        for p in folder.rglob("*.py")
    ]
    result = analyze(SNAPSHOT_ID, sources, "backend/config/urls.py")
    validate_result(result, SNAPSHOT_ID, sources)
    endpoint = next(
        e
        for e in result["endpoints"]
        if e["method"] == "POST" and e["path"] == "/api/v1/tasks/"
    )
    expected = json.loads(
        (ROOT / "testdata/analysis/task-board-create.json").read_text(encoding="utf-8")
    )
    annotations = {n["id"]: n["source_ref"] for n in expected["nodes"]}
    for name in ("view", "serializer", "model"):
        actual = endpoint[name]
        assert actual is not None
        assert actual["source_ref"]["file_path"] == annotations[name]["file_path"]
        assert actual["source_ref"]["start_line"] == annotations[name]["start_line"]
        assert actual["source_ref"]["end_line"] >= annotations[name]["end_line"]
    for name in ("root_route", "route"):
        assert any(
            e["source_ref"]
            and all(
                e["source_ref"][k] == annotations[name][k]
                for k in ("file_path", "start_line", "end_line")
            )
            for e in endpoint["evidence"]
        )
    assert any(
        e["rule"] == "python.method" and e["kind"] == "source_fact"
        for e in endpoint["evidence"]
    )


@pytest.mark.parametrize(
    "base,methods",
    [
        ("ReadOnlyModelViewSet", {"GET", "HEAD", "OPTIONS"}),
        ("ModelViewSet", {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}),
    ],
)
def test_default_router_and_read_only_actions(base: str, methods: set[str]) -> None:
    sources = replace(
        fixture_sources(), "router_urls.py", "SimpleRouter", "DefaultRouter"
    )
    sources = replace(sources, "views.py", "ModelViewSet", base)
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert {e["method"] for e in result["endpoints"]} == methods
    assert any(
        e["action"] == "api_root" and e["view"] is None for e in result["endpoints"]
    )
    assert any("(?P<format>[a-z0-9]+)" in e["path"] for e in result["endpoints"])
    assert result["coverage"]["complete"]


def test_alias_relative_imports_and_literal_route_prefixes() -> None:
    sources = [
        Source(
            "pkg/urls.py",
            'from django.urls import path as route\nfrom .views import Detail as D\nurlpatterns = [route("Case/<int:pk>", D.as_view())]\n',
        ),
        Source(
            "pkg/views.py",
            "from rest_framework.generics import RetrieveAPIView as Base\nfrom .serializers import TaskSerializer\nclass Detail(Base):\n    serializer_class = TaskSerializer\n",
        ),
    ]
    sources.extend(
        Source("pkg/" + s.file_path, s.content.replace("from models", "from .models"))
        for s in fixture_sources()
        if s.file_path in {"serializers.py", "models.py"}
    )
    result = analyze(SNAPSHOT_ID, sources, "pkg/urls.py")
    assert {(e["method"], e["path"]) for e in result["endpoints"]} == {
        (m, "/Case/<int:pk>") for m in ("GET", "HEAD", "OPTIONS")
    }
    assert result["coverage"]["complete"]


@pytest.mark.parametrize(
    "path,before,after,code",
    [
        ("root_urls.py", '"api/"', "prefix()", "DYNAMIC_ROUTE"),
        (
            "views.py",
            "serializer_class = TaskSerializer",
            "serializer_class = choose_serializer()",
            "SERIALIZER_UNRESOLVED",
        ),
        (
            "views.py",
            "serializer_class = TaskSerializer",
            "serializer_class = TaskSerializer\n    def get_serializer_class(self):\n        return choose_serializer()",
            "DYNAMIC_SERIALIZER",
        ),
        (
            "serializers.py",
            "model = Task",
            "model = choose_model()",
            "MODEL_UNRESOLVED",
        ),
        ("router_urls.py", '"tasks"', "prefix()", "DYNAMIC_REGISTER"),
        ("root_urls.py", '"router_urls"', '"missing"', "INCLUDE_UNRESOLVED"),
        (
            "router_urls.py",
            "SimpleRouter()",
            "SimpleRouter(trailing_slash=choose())",
            "ROUTER_UNRESOLVED",
        ),
    ],
)
def test_dynamic_relations_remain_diagnostics(
    path: str, before: str, after: str, code: str
) -> None:
    result = analyze(
        SNAPSHOT_ID, replace(fixture_sources(), path, before, after), "root_urls.py"
    )
    assert code in {d["code"] for d in result["diagnostics"]}
    assert not result["coverage"]["complete"]
    if code in {"SERIALIZER_UNRESOLVED", "DYNAMIC_SERIALIZER"}:
        assert all(
            e["serializer"] is None and e["model"] is None for e in result["endpoints"]
        )
    if code == "MODEL_UNRESOLVED":
        assert all(e["model"] is None for e in result["endpoints"])


def test_syntax_failure_is_partial_but_root_failure_is_fatal() -> None:
    result = analyze(
        SNAPSHOT_ID,
        fixture_sources() + [Source("broken.py", "def invalid(:\n")],
        "root_urls.py",
    )
    assert result["endpoints"] and result["coverage"]["syntax_failed_files"] == 1
    assert result["diagnostics"][0]["code"] == "PYTHON_SYNTAX_ERROR"
    for sources in ([], [Source("root_urls.py", "def invalid(:\n")]):
        with pytest.raises(AnalysisFailed):
            analyze(SNAPSHOT_ID, sources, "root_urls.py")


def test_ambiguous_import_shadowing_and_include_cycles() -> None:
    sources = fixture_sources() + [
        Source("duplicate/views.py", "class TaskViewSet: pass\n")
    ]
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert not result["endpoints"]
    assert any(d["code"] == "DYNAMIC_REGISTER" for d in result["diagnostics"])
    sources = replace(
        fixture_sources(),
        "root_urls.py",
        'include("router_urls")',
        'include("root_urls")',
    )
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert not result["endpoints"] and any(
        d["code"] == "ROUTE_CYCLE" for d in result["diagnostics"]
    )
    sources = replace(
        fixture_sources(),
        "views.py",
        "class TaskViewSet",
        "ModelViewSet = choose()\nclass TaskViewSet",
    )
    assert not analyze(SNAPSHOT_ID, sources, "root_urls.py")["endpoints"]


def test_imported_code_is_never_executed(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    sources = fixture_sources() + [
        Source(
            "side_effect.py",
            f'from pathlib import Path\nPath({str(marker)!r}).write_text("unexpected")\nraise RuntimeError("should never run")\n',
        )
    ]
    assert analyze(SNAPSHOT_ID, sources, "root_urls.py")["endpoints"]
    assert not marker.exists()


def test_invalid_protocol_and_foreign_references_are_rejected() -> None:
    sources = fixture_sources()
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    endpoint = result["endpoints"][0]
    assert endpoint["view"] is not None
    endpoint["view"]["source_ref"]["snapshot_id"] = str(uuid.uuid4())
    with pytest.raises(AnalysisFailed):
        validate_result(result, SNAPSHOT_ID, sources)


def test_router_paths_preserve_converters_format_suffix_and_trailing_slash() -> None:
    sources = replace(
        fixture_sources(), "root_urls.py", '"api/"', '"v1.2/<int:tenant>/"'
    )
    sources = replace(
        sources,
        "router_urls.py",
        "SimpleRouter()",
        "DefaultRouter(trailing_slash=False)",
    )
    sources = replace(
        sources, "router_urls.py", "import SimpleRouter", "import DefaultRouter"
    )
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert any(
        e["path"] == r"/v1\.2/(?P<tenant>[0-9]+)/tasks$" for e in result["endpoints"]
    )
    assert any(
        e["action"] == "api_root"
        and e["path"] == r"/v1\.2/(?P<tenant>[0-9]+)/\.(?P<format>[a-z0-9]+)/?$"
        for e in result["endpoints"]
    )
    assert result["coverage"]["complete"]
    sources = replace(
        fixture_sources(),
        "router_urls.py",
        "SimpleRouter()",
        "SimpleRouter(use_regex_path=False)",
    )
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert any(
        e["path"] == "/api/tasks/<str:pk>/" and e["path_kind"] == "django_path"
        for e in result["endpoints"]
    )


def test_head_only_method_filter_and_missing_root_binding() -> None:
    sources = [
        Source(
            "urls.py",
            'from django.urls import path\nfrom rest_framework.generics import ListAPIView\nfrom serializers import TaskSerializer\nclass View(ListAPIView):\n    serializer_class = TaskSerializer\n    http_method_names = ["head"]\nurlpatterns = [path("tasks/", View.as_view())]\n',
        )
    ]
    sources += [
        s for s in fixture_sources() if s.file_path in {"serializers.py", "models.py"}
    ]
    result = analyze(SNAPSHOT_ID, sources, "urls.py")
    assert [(e["method"], e["path"]) for e in result["endpoints"]] == [
        ("HEAD", "/tasks/")
    ]
    with pytest.raises(AnalysisFailed):
        analyze(SNAPSHOT_ID, [Source("urls.py", "x = 1\n")], "urls.py")


def test_conditional_overrides_and_framework_shadowing_do_not_create_connections() -> (
    None
):
    sources = replace(
        fixture_sources(),
        "views.py",
        "serializer_class = TaskSerializer",
        "serializer_class = TaskSerializer\n    if condition:\n        serializer_class = choose()",
    )
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert result["endpoints"] and all(
        e["serializer"] is None for e in result["endpoints"]
    )
    sources = replace(
        fixture_sources(),
        "views.py",
        "serializer_class = TaskSerializer",
        "serializer_class = TaskSerializer\n\nTaskViewSet.serializer_class = choose()",
    )
    assert not analyze(SNAPSHOT_ID, sources, "root_urls.py")["endpoints"]
    sources = fixture_sources() + [
        Source("rest_framework.py", "class viewsets: pass\n")
    ]
    assert not analyze(SNAPSHOT_ID, sources, "root_urls.py")["endpoints"]


def test_direct_viewset_mapping_and_mixins() -> None:
    sources = replace(
        fixture_sources(),
        "views.py",
        "from rest_framework.viewsets import ModelViewSet",
        "from rest_framework.viewsets import GenericViewSet\nfrom rest_framework.mixins import CreateModelMixin",
    )
    sources = replace(
        sources,
        "views.py",
        "TaskViewSet(ModelViewSet)",
        "TaskViewSet(CreateModelMixin, GenericViewSet)",
    )
    sources = replace(
        sources,
        "root_urls.py",
        "from django.urls import include, path",
        "from django.urls import include, path\nfrom views import TaskViewSet",
    )
    sources = replace(
        sources,
        "root_urls.py",
        'include("router_urls")',
        'TaskViewSet.as_view({"post": "create"})',
    )
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert {(e["method"], e["action"]) for e in result["endpoints"]} == {
        ("POST", "create"),
        ("OPTIONS", "metadata"),
    }
    assert result["coverage"]["complete"]


def test_missing_basename_empty_routes_duplicates_and_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = analyze(
        SNAPSHOT_ID, [Source("root_urls.py", "urlpatterns = []\n")], "root_urls.py"
    )
    assert result["coverage"]["complete"] and not result["endpoints"]
    sources = replace(fixture_sources(), "router_urls.py", ', basename="task"', "")
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert (
        not result["endpoints"]
        and result["diagnostics"][0]["code"] == "BASENAME_UNRESOLVED"
    )
    sources = replace(
        fixture_sources(),
        "root_urls.py",
        'path("api/", include("router_urls"))',
        'path("api/", include("router_urls")), path("api/", include("router_urls"))',
    )
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert len(result["endpoints"]) == 20 and any(
        d["code"] == "DUPLICATE_ENDPOINT" for d in result["diagnostics"]
    )
    monkeypatch.setattr("apps.analysis.python_index.MAX_AST_NODES", 1)
    with pytest.raises(AnalysisFailed):
        analyze(SNAPSHOT_ID, fixture_sources(), "root_urls.py")


def test_router_basename_inference_and_duplicate_rejection() -> None:
    sources = replace(fixture_sources(), "router_urls.py", ', basename="task"', "")
    sources = replace(
        sources,
        "views.py",
        "from serializers import TaskSerializer",
        "from serializers import TaskSerializer\nfrom models import Task",
    )
    sources = replace(
        sources,
        "views.py",
        "serializer_class = TaskSerializer",
        "serializer_class = TaskSerializer\n    queryset = Task.objects.all()",
    )
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert result["coverage"]["complete"] and len(result["endpoints"]) == 10
    sources = replace(
        fixture_sources(),
        "router_urls.py",
        "urlpatterns = router.urls",
        'router.register("other", TaskViewSet, basename="task")\nurlpatterns = router.urls',
    )
    result = analyze(SNAPSHOT_ID, sources, "root_urls.py")
    assert not result["endpoints"]
    assert any(d["code"] == "DUPLICATE_BASENAME" for d in result["diagnostics"])
