"""验证受控前端解析、保守匹配、证据和图视角。"""

import json
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from apps.analysis.associations import associate, extend_graph, path_matches
from apps.analysis.frontend_runner import (
    protocol_validator,
    run_frontend_parser,
    validate_frontend,
)
from apps.analysis.graph import build_graph, select_graph, validate_graph
from apps.analysis.parser import analyze
from apps.analysis.tests.test_parser import SNAPSHOT_ID, fixture_sources
from apps.analysis.types import AnalysisFailed, GraphQuery, Source
from apps.jobs.tests.test_contract import contract_schema


def test_frontend_schema_preserves_job_status_enum() -> None:
    schemas = contract_schema()["components"]["schemas"]
    assert schemas["Job"]["properties"]["status"]["allOf"] == [
        {"$ref": "#/components/schemas/StatusEnum"}
    ]
    assert schemas["StatusEnum"]["enum"] == ["queued", "running", "succeeded", "failed"]
    assert schemas["FrontendMatchStatusEnum"]["enum"] == [
        "confirmed",
        "candidate",
        "unmatched",
    ]


def test_legacy_frontend_result_remains_readable_without_reanalysis() -> None:
    sources = [Source("api.ts", "fetch('/api/items/');")]
    result = run_frontend_parser(SNAPSHOT_ID, sources)
    assert result["rule_version"] == "typescript-react/1.1.0"
    result["rule_version"] = "typescript-react/1.0.0"
    assert validate_frontend(result, SNAPSHOT_ID, {"api.ts": 1}) == result
    result["rule_version"] = "unknown/1.0"
    with pytest.raises(AnalysisFailed):
        validate_frontend(result, SNAPSHOT_ID, {"api.ts": 1})


def test_real_node_protocol_and_static_associations() -> None:
    sources = [
        Source(
            "entry.ts",
            "function create(){fetch('/api/tasks/',{method:'POST'});} create();",
        )
    ]
    frontend = run_frontend_parser(SNAPSHOT_ID, sources)
    protocol_validator("output").validate(frontend)
    backend = analyze(SNAPSHOT_ID, fixture_sources(), "root_urls.py")
    result = associate(frontend, backend["endpoints"])
    assert result["matches"][0]["status"] == "confirmed"
    assert (
        backend["endpoints"][result["matches"][0]["endpoint_indices"][0]]["action"]
        == "create"
    )
    analysis_id = uuid.uuid4()
    graph = validate_graph(
        extend_graph(
            analysis_id, build_graph(analysis_id, backend), result, backend["endpoints"]
        ),
        SNAPSHOT_ID,
        {
            **{
                s.file_path: max(1, len(s.content.splitlines()))
                for s in fixture_sources()
            },
            "entry.ts": 1,
        },
    )
    index = result["matches"][0]["endpoint_indices"][0]
    selected = select_graph(graph, GraphQuery(endpoint_index=index))
    assert {n["kind"] for n in selected["nodes"]} == {
        "endpoint",
        "view",
        "serializer",
        "model",
        "frontend_function",
        "frontend_request",
    }
    assert sum(n["kind"] == "endpoint" for n in selected["nodes"]) == 1
    assert any(e["relation"] == "method_path_match" for e in selected["edges"])
    assert select_graph(graph, GraphQuery(endpoint_index=index, max_nodes=2))[
        "truncated"
    ]
    with pytest.raises(KeyError):
        select_graph(graph, GraphQuery(endpoint_index=9999))


def test_unknown_base_duplicates_and_dynamic_requests_are_never_confirmed() -> None:
    sources = [
        Source(
            "entry.ts",
            "import axios from 'axios'; const api=axios.create({baseURL:env}); api.post('/tasks/'); fetch('/api/tasks/',{method:'POST'}); fetch(dynamic);",
        )
    ]
    frontend = run_frontend_parser(SNAPSHOT_ID, sources)
    backend = analyze(SNAPSHOT_ID, fixture_sources(), "root_urls.py")
    endpoint = next(e for e in backend["endpoints"] if e["method"] == "POST")
    endpoint = {**endpoint, "path": "/api/tasks/", "path_kind": "django_path"}
    result = associate(frontend, [endpoint, endpoint])
    assert [m["status"] for m in result["matches"]] == [
        "candidate",
        "candidate",
        "unmatched",
    ]
    assert result["matches"][0]["endpoint_indices"] == [0, 1]
    for target in ("/API/tasks/", "/api/tasks", "/other/tasks/"):
        assert not path_matches(endpoint, target)


def test_schema_references_counts_and_ids_are_verified() -> None:
    frontend = run_frontend_parser(
        SNAPSHOT_ID, [Source("a.ts", "function run(){fetch('/api/');}")]
    )
    variants: list[dict[str, Any]] = []
    for field, value in (
        ("snapshot_id", str(uuid.uuid4())),
        ("protocol_version", "future"),
    ):
        bad: dict[str, Any] = deepcopy(dict(frontend))
        bad[field] = value
        variants.append(bad)
    bad = deepcopy(dict(frontend))
    bad["requests"][0]["source_ref"]["end_line"] = 2
    variants.append(bad)
    bad = deepcopy(dict(frontend))
    bad["coverage"]["request_count"] = 0
    variants.append(bad)
    bad = deepcopy(dict(frontend))
    bad["relations"][0]["target_id"] = "0" * 64
    variants.append(bad)
    bad = deepcopy(dict(frontend))
    bad["relations"] = []
    variants.append(bad)
    bad = deepcopy(dict(frontend))
    bad["relations"][0]["relation"] = "direct_call"
    variants.append(bad)
    for invalid in variants:
        with pytest.raises(AnalysisFailed, match="静态分析"):
            validate_frontend(invalid, SNAPSHOT_ID, {"a.ts": 1})


def test_node_timeout_oversize_and_invalid_protocol_are_bounded(tmp_path: Path) -> None:
    parser = tmp_path / "parser.cjs"
    for program, reason in (
        ("setInterval(()=>{},1000);", "frontend_parser_timeout"),
        ("process.stdout.write('invalid');", "frontend_parser_protocol_or_io_failed"),
        ("process.stdout.write('x'.repeat(8192));", "frontend_output_limit"),
        ("process.exit(7);", "frontend_parser_process_failed"),
    ):
        parser.write_text(program, encoding="utf-8")
        with (
            patch("apps.analysis.frontend_runner.PARSER_PATH", parser),
            patch("apps.analysis.frontend_runner.PARSER_TIMEOUT_SECONDS", 0.3),
            patch("apps.analysis.frontend_runner.MAX_OUTPUT_BYTES", 1024),
        ):
            with pytest.raises(AnalysisFailed) as caught:
                run_frontend_parser(SNAPSHOT_ID, [Source("a.ts", "fetch('/api/');")])
            assert caught.value.reason == reason


def test_node_does_not_execute_imported_source(tmp_path: Path) -> None:
    sentinel = tmp_path / "must-not-exist"
    source = (
        "require('node:fs').writeFileSync("
        + json.dumps(str(sentinel))
        + ", 'executed'); fetch('/ok/');"
    )
    result = run_frontend_parser(SNAPSHOT_ID, [Source("a.js", source)])
    assert result["requests"][0]["path"] == "/ok/"
    assert not sentinel.exists()
    empty = run_frontend_parser(SNAPSHOT_ID, [])
    assert empty["coverage"]["source_files"] == 0 and not empty["requests"]
