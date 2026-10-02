"""验证差异、跨版本身份、引用适用性及有界输出。"""

import copy
import hashlib
import uuid
from typing import cast
from unittest.mock import patch

import pytest

from apps.analysis.diffs.engine import compare
from apps.analysis.diffs.files import file_change
from apps.analysis.diffs.protocol import validate_comparison
from apps.analysis.diffs.runner import run_comparison
from apps.analysis.diffs.types import (
    AnalysisInput,
    AnalysisVersion,
    ComparisonData,
    ComparisonFailed,
    ComparisonInput,
    FileInput,
)
from apps.analysis.graph import build_graph
from apps.analysis.parser import analyze
from apps.analysis.tests.test_parser import fixture_sources
from apps.analysis.types import Source, SourceRef

BASE, TARGET, COMPARISON = [str(uuid.UUID(int=i)) for i in (1, 2, 3)]


def file_input(path: str, old: str | None, new: str | None) -> FileInput:
    def ref(snapshot: str, text: str | None) -> SourceRef | None:
        return (
            {
                "snapshot_id": snapshot,
                "file_path": path,
                "start_line": 1,
                "end_line": max(1, len(text.splitlines())),
            }
            if text is not None
            else None
        )

    return {
        "file_path": path,
        "base_ref": ref(BASE, old),
        "target_ref": ref(TARGET, new),
        "base_sha256": hashlib.sha256(old.encode()).hexdigest()
        if old is not None
        else None,
        "target_sha256": hashlib.sha256(new.encode()).hexdigest()
        if new is not None
        else None,
        "base_content": old,
        "target_content": new,
    }


def payload(
    old: list[Source] | None = None, new: list[Source] | None = None
) -> ComparisonInput:
    old, new = (
        old if old is not None else fixture_sources(),
        new if new is not None else fixture_sources(),
    )
    maps = [
        {item.file_path: item.content for item in sources} for sources in (old, new)
    ]

    def analysis(snapshot: str, sources: list[Source], id: int) -> AnalysisInput:
        result = analyze(snapshot, sources, "root_urls.py")
        return {
            "version": {
                "analysis_id": str(uuid.UUID(int=id)),
                "snapshot_id": snapshot,
                "root_urlconf": "root_urls.py",
                "rule_version": result["rule_version"],
                "graph_version": "analysis-graph/2.0.0",
                "frontend_rule_version": None,
                "association_rule_version": None,
            },
            "graph": build_graph(uuid.UUID(int=id), result),
            "endpoints": result["endpoints"],
        }

    return {
        "comparison_id": COMPARISON,
        "base_snapshot_id": BASE,
        "target_snapshot_id": TARGET,
        "files": [
            file_input(path, maps[0].get(path), maps[1].get(path))
            for path in sorted(maps[0].keys() | maps[1].keys())
        ],
        "base_analysis": analysis(BASE, old, 4),
        "target_analysis": analysis(TARGET, new, 5),
        "evidence": [],
    }


def validated(input: ComparisonInput) -> ComparisonData:
    result = compare(input)
    return validate_comparison(
        result,
        COMPARISON,
        BASE,
        TARGET,
        (
            input["base_analysis"]["version"]["analysis_id"]
            if input["base_analysis"]
            else None,
            input["target_analysis"]["version"]["analysis_id"]
            if input["target_analysis"]
            else None,
        ),
        (
            input["base_analysis"]["graph"] if input["base_analysis"] else None,
            input["target_analysis"]["graph"] if input["target_analysis"] else None,
        ),
    )


def test_same_content_new_uuids_and_line_movement_are_not_semantic_changes() -> None:
    original = payload()
    result = validated(original)
    assert result["summary"]["unchanged"] == len(fixture_sources())
    assert result["comparability"] == "comparable" and result["interfaces"]
    assert all(
        item["change_type"] == "unchanged"
        for item in [*result["interfaces"], *result["relations"]]
    )
    assert original["base_analysis"] and original["target_analysis"]
    assert original["base_analysis"]["graph"] and original["target_analysis"]["graph"]
    assert {
        edge["id"] for edge in original["base_analysis"]["graph"]["edges"]
    }.isdisjoint(edge["id"] for edge in original["target_analysis"]["graph"]["edges"])
    moved = [
        Source(source.file_path, "\n\n" + source.content)
        for source in fixture_sources()
    ]
    result = validated(payload(new=moved))
    assert result["summary"]["modified"] == len(moved)
    assert all(
        item["change_type"] == "unchanged"
        for item in [*result["interfaces"], *result["relations"]]
    )


def test_added_deleted_modified_and_rename_are_path_changes() -> None:
    result = validated(
        payload(
            old=[*fixture_sources(), Source("old.py", "x=1\n")],
            new=[*fixture_sources(), Source("new.py", "x=1\n")],
        )
    )
    changes = {file["file_path"]: file for file in result["files"]}
    assert (
        changes["old.py"]["change_type"] == "deleted"
        and changes["new.py"]["change_type"] == "added"
    )
    modified = file_change(
        COMPARISON, file_input("lines.py", "a\nb\nc\n", "a\nx\nb\ny\n")
    )
    assert (
        "@@" in modified["diff"]
        and "+x\n" in modified["diff"]
        and "-c\n" in modified["diff"]
    )
    assert modified["base_ranges"] == [
        {"snapshot_id": BASE, "file_path": "lines.py", "start_line": 2, "end_line": 2},
        {"snapshot_id": BASE, "file_path": "lines.py", "start_line": 3, "end_line": 3},
    ]
    assert (
        file_change(COMPARISON, file_input("empty.py", None, ""))["target_ranges"][0][
            "end_line"
        ]
        == 1
    )
    no_newline = file_change(COMPARISON, file_input("last.py", "旧行", "新行\n"))
    assert "\\ No newline at end of file\n+新行\n" in no_newline["diff"]


def test_handler_change_and_duplicate_routes_are_distinct() -> None:
    changed = [
        Source(
            source.file_path, source.content.replace("TaskViewSet", "NewTaskViewSet")
        )
        for source in fixture_sources()
    ]
    result = validated(payload(new=changed))
    assert any(
        item["change_type"] == "modified" and "view" in item["changed_fields"]
        for item in result["interfaces"]
    )
    duplicate = [
        Source(
            source.file_path,
            "from django.urls import include, path\nurlpatterns=[path('api/', include('router_urls')), path('api/', include('router_urls'))]\n",
        )
        if source.file_path == "root_urls.py"
        else source
        for source in fixture_sources()
    ]
    result = validated(payload(new=duplicate))
    assert any(item["change_type"] == "ambiguous" for item in result["interfaces"])
    assert any(item["change_type"] == "ambiguous" for item in result["relations"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("root_urlconf", "other.py"),
        ("rule_version", "python-drf/1.0.0"),
        ("frontend_rule_version", "typescript-react/1.0.0"),
        ("association_rule_version", "different/1"),
        ("graph_version", "analysis-graph/1.0.0"),
    ],
)
def test_rule_or_entry_mismatch_keeps_files_without_attributing_semantic_change(
    field: str, value: str
) -> None:
    input = payload()
    assert input["target_analysis"]
    version = dict(input["target_analysis"]["version"])
    version[field] = value
    input["target_analysis"]["version"] = cast(AnalysisVersion, version)
    result = validated(input)
    assert result["comparability"] == "incomparable" and result["files"]
    assert not result["interfaces"] and not result["relations"]
    input["base_analysis"] = input["target_analysis"] = None
    assert validated(input)["comparability"] == "files_only"


def test_missing_history_graph_and_ambiguous_frontend_symbols_are_explicit() -> None:
    input = payload()
    assert input["base_analysis"] and input["target_analysis"]
    input["base_analysis"]["graph"] = None
    result = validated(input)
    assert result["comparability"] == "incomparable" and not result["relations"]
    input = payload()
    assert input["target_analysis"] and input["target_analysis"]["graph"]
    graph = input["target_analysis"]["graph"]
    symbol = next(node for node in graph["nodes"] if node["kind"] == "view")
    graph["nodes"].append({**symbol, "id": str(uuid.UUID(int=20))})
    result = validated(input)
    assert any(item["change_type"] == "ambiguous" for item in result["relations"])


def test_evidence_applicability_preserves_old_refs_and_never_claims_semantic_verification() -> (
    None
):
    input = payload()
    input["base_analysis"] = input["target_analysis"] = None
    input["files"] = [
        file_input("changed.py", "x=1\n", "\nx=2\n"),
        file_input("deleted.py", "x=1\n", None),
        file_input("same.py", "x=1\n", "x=1\n"),
    ]
    input["evidence"] = [
        {
            "explanation_id": str(uuid.UUID(int=6)),
            "preview_id": str(uuid.UUID(int=7)),
            "analysis_id": str(uuid.UUID(int=8)),
            "endpoint_index": 0,
            "source_refs": [
                file["base_ref"]
                for file in input["files"]
                if file["base_ref"] is not None
            ],
            "valid": True,
        },
        {
            "explanation_id": str(uuid.UUID(int=9)),
            "preview_id": str(uuid.UUID(int=10)),
            "analysis_id": str(uuid.UUID(int=8)),
            "endpoint_index": 0,
            "source_refs": [],
            "valid": False,
        },
    ]
    result = validated(input)
    refs = result["evidence"][0]["references"]
    assert [ref["applicability"] for ref in refs] == ["review", "deleted", "unchanged"]
    assert all(ref["source_ref"]["snapshot_id"] == BASE for ref in refs)
    assert [ref["target_ref"] for ref in refs[:2]] == [None, None]
    assert refs[2]["target_ref"] is not None
    assert refs[2]["target_ref"]["snapshot_id"] == TARGET
    assert result["evidence"][1]["warning"] and "语义" in result["comparison_notes"][-1]


def test_budgets_fail_instead_of_silent_truncation() -> None:
    with (
        patch("apps.analysis.diffs.files.MAX_FILE_LINES", 1),
        pytest.raises(ComparisonFailed, match="快照对比"),
    ):
        file_change(COMPARISON, file_input("large.py", "a\nb\n", "a\nc\n"))
    with (
        patch("apps.analysis.diffs.files.MAX_FILE_DIFF_BYTES", 1),
        pytest.raises(ComparisonFailed),
    ):
        file_change(COMPARISON, file_input("large.py", "a\n", "c\n"))
    with (
        patch("apps.analysis.diffs.engine.MAX_FILES", 0),
        pytest.raises(ComparisonFailed),
    ):
        compare(payload())
    with (
        patch("apps.analysis.diffs.runner.MAX_INPUT_BYTES", 1),
        pytest.raises(ComparisonFailed) as error,
    ):
        run_comparison(payload())
    assert error.value.reason == "input_limit"


@pytest.mark.parametrize(
    "damage", ["summary", "identity", "scope", "range", "path", "type", "edge"]
)
def test_protocol_rejects_corrupt_or_cross_side_results(damage: str) -> None:
    input = payload()
    assert input["base_analysis"] and input["target_analysis"]
    result = copy.deepcopy(compare(input))
    assert result["files"][0]["base_ref"] is not None
    if damage == "summary":
        result["summary"]["unchanged"] += 1
    elif damage == "identity":
        result["files"][0]["id"] = str(uuid.UUID(int=50))
    elif damage == "scope":
        result["files"][0]["base_ref"]["snapshot_id"] = TARGET
    elif damage == "range":
        result["files"][0]["base_ref"]["end_line"] = 0
    elif damage == "path":
        result["files"][0]["file_path"] = "../unsafe.py"
    elif damage == "type":
        result["summary"]["unchanged"] = True
    else:
        result["relations"][0]["base_edge_ids"] = [str(uuid.UUID(int=50))]
    with pytest.raises(ComparisonFailed):
        validate_comparison(
            result,
            COMPARISON,
            BASE,
            TARGET,
            (str(uuid.UUID(int=4)), str(uuid.UUID(int=5))),
            (input["base_analysis"]["graph"], input["target_analysis"]["graph"]),
        )
