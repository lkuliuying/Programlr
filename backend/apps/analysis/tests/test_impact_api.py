"""通过实际导入图和直接历史夹具验证只读影响证据与原始记录不变。"""

import copy
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.analysis.models import (
    Analysis,
    AnalysisGraph,
    RelationReview,
    RelationReviewState,
)
from apps.analysis.services import execute_analysis, read_graph
from apps.analysis.tests.test_analysis import imported, submitted
from apps.analysis.tests.test_comparisons import publish_history, submit
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
    state = RelationReviewState.objects.create(
        analysis=analysis,
        request_id=candidate["source_id"],
        revision=1,
        confirmed_target_id=candidate["target_id"],
        excluded_target_ids=[],
    )
    RelationReview.objects.create(
        analysis=analysis,
        request_id=candidate["source_id"],
        target_id=candidate["target_id"],
        action="confirm",
        revision=1,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
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
    state.revision, state.confirmed_target_id, state.excluded_target_ids = (
        2,
        None,
        [candidate["target_id"]],
    )
    state.save(update_fields=["revision", "confirmed_target_id", "excluded_target_ids"])
    RelationReview.objects.create(
        analysis=analysis,
        request_id=candidate["source_id"],
        target_id=candidate["target_id"],
        action="exclude",
        revision=2,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
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
    result = publish_history(comparison_job)
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
    file_only = publish_history(file_job)
    unavailable = client.get(COMPARISON.format(comparison_id=file_only.pk)).json()
    assert (
        unavailable["base"]["impact"] is None and not unavailable["target"]["available"]
    )
    assert "不能判断" in unavailable["base"]["reason"]
    assert result.request.target_analysis_id is not None
    AnalysisGraph.objects.filter(analysis_id=result.request.target_analysis_id).delete()
    assert client.get(path).status_code == 500
    assert (
        result.request.base_analysis is not None
        and result.request.target_analysis is not None
    )
    legacy_job = submit(
        base,
        target,
        analyses=(result.request.base_analysis, result.request.target_analysis),
    )
    legacy = publish_history(legacy_job)
    assert not client.get(COMPARISON.format(comparison_id=legacy.pk)).json()["target"][
        "available"
    ]
