"""在真实事务中验证前后端结果发布、历史兼容和查询归属。"""

import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.analysis.models import Analysis, AnalysisGraph
from apps.analysis.services import execute_analysis
from apps.analysis.tests.test_analysis import imported, submitted
from apps.analysis.types import LEGACY_GRAPH_VERSION, AnalysisFailed
from apps.jobs.models import Job
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def test_frontend_publication_endpoint_scope_and_filtered_history() -> None:
    snapshot = imported(
        {
            "entry.ts": b"function submit(){fetch('/api/tasks/',{method:'POST'});fetch('/missing/');}"
        }
    )
    jobs = [submitted(snapshot), submitted(snapshot)]
    for job in jobs:
        execute_analysis(str(job.pk))
    analysis = Analysis.objects.get(job=jobs[0])
    assert analysis.frontend is not None
    client, schema = client_with_token(), contract_schema()
    path = f"/api/v1/analyses/{analysis.pk}/"
    detail = client.get(path)
    assert_response(detail, schema, "/api/v1/analyses/{analysis_id}/")
    assert detail.json()["frontend"]["confirmed"] == 1
    assert detail.json()["frontend"]["unmatched"] == 1
    endpoints = client.get(path + "endpoints/")
    assert_response(endpoints, schema, "/api/v1/analyses/{analysis_id}/endpoints/")
    endpoint = next(
        item for item in endpoints.json()["results"] if item["frontend_links"]
    )
    graph = client.get(path + "graph/", {"endpoint_index": endpoint["index"]})
    assert_response(graph, schema, "/api/v1/analyses/{analysis_id}/graph/")
    data = graph.json()
    assert sum(node["kind"] == "endpoint" for node in data["nodes"]) == 1
    assert {node["kind"] for node in data["nodes"]} == {
        "frontend_function",
        "frontend_request",
        "endpoint",
        "view",
        "serializer",
        "model",
    }
    assert any(edge["relation"] == "method_path_match" for edge in data["edges"])
    assert client.get(path + "graph/", {"endpoint_index": 9999}).status_code == 404
    assert (
        client.get(
            path + "graph/", {"endpoint_index": "0", "root_node_id": str(uuid.uuid4())}
        ).status_code
        == 400
    )
    before = Analysis.objects.values().get(pk=analysis.pk)
    with patch("apps.analysis.services.run_frontend_parser") as parser:
        assert client.get(path).status_code == 200
        assert client.get(path + "graph/").status_code == 200
        parser.assert_not_called()
    assert Analysis.objects.values().get(pk=analysis.pk) == before
    other = submitted(imported())
    response = client.get(
        "/api/v1/jobs/",
        {"kind": "analysis", "snapshot_id": str(snapshot.pk), "page_size": "1"},
    )
    assert response.status_code == 200 and response.json()["count"] == 2
    next_page = response.json()["next"]
    assert "kind=analysis" in next_page and f"snapshot_id={snapshot.pk}" in next_page
    assert client.get(next_page).json()["results"][0]["id"] != str(other.pk)
    for query in (
        "kind=invalid",
        "snapshot_id=invalid",
        "kind=analysis&kind=import",
        "snapshot_id=",
    ):
        assert client.get("/api/v1/jobs/?" + query).status_code == 400


def test_legacy_frontend_null_differs_from_empty_and_keeps_graph_version() -> None:
    job = submitted(imported())
    execute_analysis(str(job.pk))
    analysis = Analysis.objects.get(job=job)
    assert analysis.frontend is not None
    client = client_with_token()
    path = f"/api/v1/analyses/{analysis.pk}/"
    assert client.get(path).json()["frontend"]["coverage"]["source_files"] == 0
    Analysis.objects.filter(pk=analysis.pk).update(frontend=None)
    AnalysisGraph.objects.filter(analysis=analysis).update(
        graph_version=LEGACY_GRAPH_VERSION
    )
    assert client.get(path).json()["frontend"] is None
    assert client.get(path + "graph/").json()["graph_version"] == LEGACY_GRAPH_VERSION
    assert all(
        not item["frontend_available"]
        for item in client.get(path + "endpoints/").json()["results"]
    )


def test_frontend_failure_rolls_back_and_retry_preserves_snapshot() -> None:
    snapshot = imported({"entry.ts": b"fetch('/api/tasks/');"})
    job = submitted(snapshot)
    with patch(
        "apps.analysis.services.run_frontend_parser",
        side_effect=AnalysisFailed("frontend_parser_timeout"),
    ):
        execute_analysis(str(job.pk))
    job.refresh_from_db()
    assert job.status == Job.Status.FAILED
    assert not Analysis.objects.exists() and not AnalysisGraph.objects.exists()
    key = str(uuid.uuid4())
    with patch("apps.jobs.services.app.send_task"):
        response = client_with_token().post(
            f"/api/v1/jobs/{job.pk}/retries/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert response.status_code == 202
        again = client_with_token().post(
            f"/api/v1/jobs/{job.pk}/retries/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert again.json()["id"] == response.json()["id"]
    execute_analysis(response.json()["id"])
    result = Analysis.objects.get()
    assert result.snapshot_id == snapshot.pk and result.frontend is not None
    job.refresh_from_db()
    assert job.status == Job.Status.FAILED and job.result_url is None
