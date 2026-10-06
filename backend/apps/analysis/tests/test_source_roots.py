import uuid

import pytest

from apps.analysis.root_discovery import discover_roots
from apps.analysis.scan_runner import validate_scan
from apps.analysis.types import AnalysisFailed, Source
from apps.learning.source_scan import scan_knowledge_facts

SNAPSHOT = str(uuid.UUID(int=81))


def test_configuration_selects_nested_root_with_source_evidence() -> None:
    sources = [
        Source("backend/config/settings.py", 'ROOT_URLCONF = "config.urls"\n'),
        Source(
            "backend/config/urls.py",
            'from django.urls import path, include\nurlpatterns = [path("api/", include("app.urls"))]\n',
        ),
        Source("backend/app/urls.py", "urlpatterns = []\n"),
    ]
    roots = discover_roots(SNAPSHOT, sources)
    assert roots["selected_root"] == "backend/config/urls.py"
    assert roots["candidates"][0]["reason"] == "literal_root_urlconf"
    assert len(roots["candidates"][0]["source_refs"]) == 2


def test_includes_identify_top_level_root_without_configuration() -> None:
    roots = discover_roots(
        SNAPSHOT,
        [
            Source(
                "urls.py",
                'from django.urls import include\nurlpatterns = [include("child")]\n',
            ),
            Source("child.py", "urlpatterns = []\n"),
        ],
    )
    assert roots["selected_root"] == "urls.py"


def test_conflicting_configs_and_multiple_roots_do_not_guess() -> None:
    sources = [
        Source("settings.py", 'ROOT_URLCONF = "a"\n'),
        Source("test_settings.py", 'ROOT_URLCONF = "b"\n'),
        Source("a.py", "urlpatterns = []\n"),
        Source("b.py", "urlpatterns = []\n"),
    ]
    assert discover_roots(SNAPSHOT, sources)["status"] == "needs_root"
    roots = discover_roots(SNAPSHOT, sources[2:])
    assert roots["selected_root"] is None and len(roots["candidates"]) == 2


def test_dynamic_or_unavailable_config_preserves_choice() -> None:
    for config in ["ROOT_URLCONF = choose()\n", 'ROOT_URLCONF = "missing"\n']:
        roots = discover_roots(
            SNAPSHOT,
            [Source("settings.py", config), Source("urls.py", "urlpatterns = []\n")],
        )
        assert roots["status"] == "needs_root" and roots["selected_root"] is None
        assert roots["diagnostics"]


def test_syntax_errors_no_root_and_cycle_are_explicit() -> None:
    assert (
        discover_roots(SNAPSHOT, [Source("views.py", "def invalid(:\n")])["status"]
        == "no_root"
    )
    sources = [
        Source(
            "a.py", 'from django.urls import include\nurlpatterns = [include("b")]\n'
        ),
        Source(
            "b.py", 'from django.urls import include\nurlpatterns = [include("a")]\n'
        ),
    ]
    assert discover_roots(SNAPSHOT, sources)["selected_root"] is None


def test_scan_protocol_rejects_cross_snapshot_references() -> None:
    sources = [Source("urls.py", "urlpatterns = []\n")]
    result = {
        "roots": discover_roots(SNAPSHOT, sources),
        "knowledge": scan_knowledge_facts(SNAPSHOT, sources),
    }
    assert validate_scan(result, SNAPSHOT, sources) == result
    result["roots"]["candidates"][0]["source_refs"][0]["snapshot_id"] = str(
        uuid.UUID(int=82)
    )
    with pytest.raises(AnalysisFailed):
        validate_scan(result, SNAPSHOT, sources)


@pytest.mark.parametrize("change", ["status", "knowledge", "missing_ref"])
def test_scan_protocol_rejects_inconsistent_or_partial_results(change: str) -> None:
    sources = [Source("urls.py", "urlpatterns = []\n")]
    result = {
        "roots": discover_roots(SNAPSHOT, sources),
        "knowledge": scan_knowledge_facts(SNAPSHOT, sources),
    }
    if change == "status":
        result["roots"]["selected_root"] = None
    elif change == "knowledge":
        result["knowledge"] = {"hits": []}
    else:
        result["roots"]["candidates"][0]["source_refs"] = [{"snapshot_id": SNAPSHOT}]
    with pytest.raises(AnalysisFailed):
        validate_scan(result, SNAPSHOT, sources)
