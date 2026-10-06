import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings

from apps.analysis.models import Analysis, AnalysisGraph
from apps.analysis.services import execute_analysis
from apps.analysis.tests.test_analysis import imported, submitted
from apps.analysis.types import GRAPH_VERSION, AnalysisFailed
from apps.jobs.models import Job
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token

pytestmark = pytest.mark.django_db(transaction=True)
GRAPH_PATH = "/api/v1/analyses/{analysis_id}/graph/"


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def completed() -> Analysis:
    job = submitted(imported())
    execute_analysis(str(job.pk))
    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED
    return Analysis.objects.get(job=job)


def test_persisted_graph_queries_match_schema_and_snapshot() -> None:
    analysis, client, schema = completed(), client_with_token(), contract_schema()
    path = GRAPH_PATH.format(analysis_id=analysis.pk)
    response = client.get(path)
    assert_response(response, schema, GRAPH_PATH)
    data = response.json()
    assert response.status_code == 200
    assert data["analysis_id"] == str(analysis.pk)
    assert data["snapshot_id"] == str(analysis.snapshot_id)
    assert data["rule_version"] == analysis.rule_version
    assert data["graph_version"] == GRAPH_VERSION
    assert data["total_nodes"] == data["returned_nodes"] == 13
    assert data["total_edges"] == data["returned_edges"] == 12
    assert not data["truncated"]
    root = next(
        n for n in data["nodes"] if n["endpoint"] and n["endpoint"]["method"] == "POST"
    )
    scoped = client.get(path, {"root_node_id": root["id"], "algorithm": "dfs"})
    assert_response(scoped, schema, GRAPH_PATH)
    assert scoped.json()["returned_nodes"] == 4
    assert not scoped.json()["truncated"]
    limited = client.get(path, {"max_nodes": 2, "max_edges": 1})
    assert limited.json()["truncated"] and limited.json()["returned_edges"] <= 1
    assert_response(limited, schema, GRAPH_PATH)
    jobs_before = Job.objects.count()
    assert client.get(path).json() == data
    assert Job.objects.count() == jobs_before
    execute_analysis(str(analysis.job_id))
    assert AnalysisGraph.objects.count() == 1
    other = completed()
    assert client.get(path).json() == data
    assert (
        client.get(
            GRAPH_PATH.format(analysis_id=other.pk), {"root_node_id": root["id"]}
        ).status_code
        == 404
    )
    for node in data["nodes"]:
        if node["source_ref"]:
            assert node["source_ref"]["snapshot_id"] == str(analysis.snapshot_id)


def test_empty_graph_and_missing_graph_have_distinct_responses() -> None:
    job = submitted(imported({"root_urls.py": b"urlpatterns = []\n"}))
    execute_analysis(str(job.pk))
    analysis, client = Analysis.objects.get(job=job), client_with_token()
    record = AnalysisGraph.objects.get(analysis=analysis)
    assert record.nodes == record.edges == analysis.endpoints == []
    path = GRAPH_PATH.format(analysis_id=analysis.pk)
    empty = client.get(path)
    assert empty.status_code == 200 and empty.json()["nodes"] == []
    assert not empty.json()["truncated"]
    assert client.get(path, {"root_node_id": str(uuid.uuid4())}).status_code == 404
    record.delete()
    before = Analysis.objects.values().get(pk=analysis.pk)
    missing = client.get(path)
    assert (
        missing.status_code == 409 and missing.json()["code"] == "GRAPH_NOT_AVAILABLE"
    )
    assert not AnalysisGraph.objects.exists()
    assert Analysis.objects.values().get(pk=analysis.pk) == before
    assert client.get(f"/api/v1/analyses/{analysis.pk}/").status_code == 200
    assert client.get(GRAPH_PATH.format(analysis_id=uuid.uuid4())).status_code == 404


def test_graph_publication_failure_rolls_back_analysis_and_success() -> None:
    job = submitted(imported())
    with patch(
        "apps.analysis.services.AnalysisGraph.objects.create",
        side_effect=DatabaseError("synthetic-private-marker"),
    ):
        execute_analysis(str(job.pk))
    job.refresh_from_db()
    assert job.status == Job.Status.FAILED and job.result_url is None
    assert not Analysis.objects.exists() and not AnalysisGraph.objects.exists()
    assert job.error and "synthetic-private-marker" not in str(job.error)


def test_graph_budget_and_expired_claim_cannot_publish() -> None:
    from datetime import timedelta

    from django.utils import timezone

    from apps.analysis.graph import build_graph

    job = submitted(imported())
    with patch(
        "apps.analysis.services.build_graph", side_effect=AnalysisFailed("graph_limit")
    ):
        execute_analysis(str(job.pk))
    job.refresh_from_db()
    assert job.status == Job.Status.FAILED
    assert job.error and job.error["details"]["reason"] == "graph_limit"
    late = submitted(imported())

    def expire(*args: Any, **kwargs: Any) -> Any:
        Job.objects.filter(pk=late.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        return build_graph(*args, **kwargs)

    with patch("apps.analysis.services.build_graph", side_effect=expire):
        execute_analysis(str(late.pk))
    assert not Analysis.objects.exists() and not AnalysisGraph.objects.exists()
    from apps.jobs.services import reconcile_expired

    reconcile_expired()
    late.refresh_from_db()
    assert late.status == Job.Status.FAILED and late.result_url is None


@pytest.mark.parametrize("case", ["foreign_ref", "dangling_edge", "unknown_version"])
def test_corrupt_stored_graph_fails_without_partial_success(case: str) -> None:
    analysis = completed()
    record = AnalysisGraph.objects.get(analysis=analysis)
    if case == "foreign_ref":
        record.nodes = deepcopy(record.nodes)
        record.nodes[0]["evidence"][0]["source_ref"]["snapshot_id"] = str(uuid.uuid4())
    elif case == "dangling_edge":
        record.edges[0]["target_id"] = str(uuid.uuid4())
    else:
        record.graph_version = "unsupported"
    record.save()
    response = client_with_token().get(GRAPH_PATH.format(analysis_id=analysis.pk))
    assert response.status_code == 500 and response.json()["code"] == "INTERNAL_ERROR"
    assert "nodes" not in response.json()
    assert_response(response, contract_schema(), GRAPH_PATH)


def test_graph_database_outage_and_request_protection() -> None:
    analysis, client = completed(), client_with_token()
    path = GRAPH_PATH.format(analysis_id=analysis.pk)
    with patch(
        "apps.analysis.services.AnalysisGraph.objects.filter",
        side_effect=DatabaseError("synthetic-private-marker"),
    ):
        response = client.get(path)
    assert response.status_code == 503
    assert_response(response, contract_schema(), GRAPH_PATH)
    assert client.get(path, HTTP_ACCEPT="text/html").status_code == 406
    assert client.post(path, {}, format="json").status_code == 405
    client.credentials(HTTP_HOST="evil.invalid")
    rejected = client.get(path)
    assert rejected.status_code == 403 and rejected.json()["code"] == "ORIGIN_REJECTED"
    client.credentials(HTTP_HOST="127.0.0.1:5173")
    assert client.post(path, {}, format="json").status_code == 403


def test_additive_migration_preserves_legacy_analysis_without_backfill() -> None:
    analysis = completed()
    identity = analysis.pk
    before = Analysis.objects.values().get(pk=identity)
    executor = MigrationExecutor(connection)
    restore_targets = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("analysis", "0001_initial")])
        executor = MigrationExecutor(connection)
        executor.migrate([("analysis", "0003_analysis_frontend")])
        historical = executor.loader.project_state(
            [("analysis", "0003_analysis_frontend")]
        ).apps
        legacy_analysis = historical.get_model("analysis", "Analysis")
        legacy_graph = historical.get_model("analysis", "AnalysisGraph")
        fields = {field.attname for field in legacy_analysis._meta.concrete_fields}
        assert legacy_analysis.objects.values().get(pk=identity) == {
            **{key: value for key, value in before.items() if key in fields},
            "frontend": None,
        }
        assert not legacy_graph.objects.exists()
    finally:
        # 回退分析迁移会同时卸载依赖模块，结束时必须恢复原有完整迁移图。
        MigrationExecutor(connection).migrate(restore_targets)
    # 当前运行模型只访问恢复后的 schema，不能在旧迁移阶段查询新增字段。
    response = client_with_token().get(GRAPH_PATH.format(analysis_id=identity))
    assert response.status_code == 409
