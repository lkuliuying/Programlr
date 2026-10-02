"""通过真实导入图验证影响查询、两侧变化和原始历史不变。"""

import copy
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.analysis.diffs.services import execute_comparison, submit_comparison
from apps.analysis.models import Analysis, AnalysisGraph, SnapshotComparison
from apps.analysis.reviews import submit_review
from apps.analysis.services import execute_analysis, read_graph
from apps.analysis.tests.test_analysis import imported, submitted
from apps.analysis.tests.test_comparisons import submit
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from apps.projects.models import Snapshot
from apps.projects.services import execute_import, submit_import
from apps.projects.tests.test_archive import zip_bytes
from apps.projects.tests.test_projects import upload

pytestmark = pytest.mark.django_db(transaction=True)
NODE = "/api/v1/analyses/{analysis_id}/impact/"
COMPARISON = "/api/v1/snapshot-comparisons/{comparison_id}/impact/"


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def test_default_candidates_manual_revision_exclude_and_strict_query() -> None:
    snapshot = imported(
        {
            "root_urls.py": b"from django.urls import include,path\nurlpatterns=[path('api/',include('router_urls')),path('api/',include('router_urls'))]\n",
            "entry.ts": b"function submit(){fetch('/api/tasks/');}\n",
        }
    )
    job = submitted(snapshot)
    execute_analysis(str(job.pk))
    analysis = Analysis.objects.get(job=job)
    graph = read_graph(analysis)[0]
    original = copy.deepcopy(AnalysisGraph.objects.values().get(analysis=analysis))
    model = next(node for node in graph["nodes"] if node["kind"] == "model")
    candidate = next(
        edge for edge in graph["edges"] if edge["relation"] == "candidate_match"
    )
    client, path, query = (
        client_with_token(),
        NODE.format(analysis_id=analysis.pk),
        {"node_id": model["id"]},
    )
    first = client.get(path, query)
    assert_response(first, contract_schema(), NODE)
    assert not any(
        item["node"]["kind"].startswith("frontend_") for item in first.json()["results"]
    )
    opted = client.get(path, {**query, "include_candidates": "true"}).json()
    assert any(item["via_candidate"] for item in opted["results"])
    submit_review(
        analysis,
        uuid.uuid4(),
        uuid.UUID(candidate["source_id"]),
        uuid.UUID(candidate["target_id"]),
        "confirm",
        0,
    )
    confirmed = client.get(path, query).json()
    assert any(
        item["node"]["kind"] == "frontend_request" and not item["via_candidate"]
        for item in confirmed["results"]
    )
    assert confirmed["relation_reviews"][0]["revision"] == 1
    assert all(
        item["decision"] == "confirmed" for item in confirmed["relation_reviews"]
    )
    submit_review(
        analysis,
        uuid.uuid4(),
        uuid.UUID(candidate["source_id"]),
        uuid.UUID(candidate["target_id"]),
        "exclude",
        1,
    )
    selected = client.get(path, {**query, "include_candidates": "true"}).json()
    assert candidate["id"] not in {edge["id"] for edge in selected["edges"]}
    assert selected["limitations"] and selected["diagnostics_url"]
    assert AnalysisGraph.objects.values().get(analysis=analysis) == original
    for query in (
        {},
        {"node_id": "bad"},
        {**query, "max_nodes": "0"},
        {**query, "max_edges": "2001"},
        {**query, "include_candidates": "1"},
        {**query, "unknown": "1"},
    ):
        assert client.get(path, query).status_code == 400
    assert client.get(path, {"node_id": str(uuid.uuid4())}).status_code == 404
    assert (
        client.get(path + f"?node_id={model['id']}&node_id={model['id']}").status_code
        == 400
    )
    budget = client.get(path, {"node_id": model["id"], "max_nodes": "1"}).json()
    assert budget["truncated"] and budget["visited_nodes"] == 1


def test_both_sides_deleted_added_unmapped_and_file_only() -> None:
    base = imported(
        {
            "entry.ts": b"function load(){fetch('/api/tasks/');}\n",
            "deleted.ts": b"function old(){fetch('/api/tasks/');}\n",
        }
    )
    from apps.analysis.tests.test_parser import fixture_sources

    files = {source.file_path: source.content.encode() for source in fixture_sources()}
    files.update(
        {
            "entry.ts": b"function load(){fetch('/api/tasks/1/');}\n",
            "added.ts": b"function added(){fetch('/api/tasks/');}\n",
            "unknown.ts": b"const value = 1;\n",
        }
    )
    with patch("apps.jobs.services.app.send_task"):
        job = submit_import(base.project, uuid.uuid4(), upload(zip_bytes(files)))[0]
    execute_import(str(job.pk))
    target = Snapshot.objects.get(job=job)
    comparison_job = submit(base, target, True)
    execute_comparison(str(comparison_job.pk))
    result = SnapshotComparison.objects.get(request__job=comparison_job)
    client, path = client_with_token(), COMPARISON.format(comparison_id=result.pk)
    with patch(
        "apps.explanations.adapter.complete", side_effect=AssertionError("不能调用模型")
    ):
        response = client.get(path)
    assert_response(response, contract_schema(), COMPARISON)
    data = response.json()
    assert data["base"]["snapshot_id"] == str(base.pk) and data["target"][
        "snapshot_id"
    ] == str(target.pk)
    assert (
        "deleted.ts" in data["base"]["changed_files"]
        and "added.ts" in data["target"]["changed_files"]
    )
    assert "unknown.ts" in data["target"]["impact"]["unmapped_files"]
    assert any(
        item["node"]["source_ref"]["file_path"] == "deleted.ts"
        for item in data["base"]["impact"]["results"]
        if item["node"]["source_ref"]
    )
    deleted = next(
        file for file in result.data["files"] if file["file_path"] == "deleted.ts"
    )
    one = client.get(path, {"change_id": deleted["id"]}).json()
    assert (
        one["base"]["changed_files"] == ["deleted.ts"]
        and one["target"]["changed_files"] == []
    )
    assert client.get(path, {"change_id": str(uuid.uuid4())}).status_code == 404
    file_job = submit(base, target)
    execute_comparison(str(file_job.pk))
    file_only = SnapshotComparison.objects.get(request__job=file_job)
    unavailable = client.get(COMPARISON.format(comparison_id=file_only.pk)).json()
    assert (
        unavailable["base"]["impact"] is None and not unavailable["target"]["available"]
    )
    assert "不能判断" in unavailable["base"]["reason"]
    assert result.request.target_analysis_id is not None
    AnalysisGraph.objects.filter(analysis_id=result.request.target_analysis_id).delete()
    assert client.get(path).status_code == 500
    with patch("apps.jobs.services.app.send_task"):
        legacy_job = submit_comparison(
            base.project,
            uuid.uuid4(),
            base,
            target,
            result.request.base_analysis,
            result.request.target_analysis,
        )[0]
    execute_comparison(str(legacy_job.pk))
    legacy = SnapshotComparison.objects.get(request__job=legacy_job)
    assert not client.get(COMPARISON.format(comparison_id=legacy.pk)).json()["target"][
        "available"
    ]
