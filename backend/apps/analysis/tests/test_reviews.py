"""通过实际快照、图和 PostgreSQL 事务验证人工决定及历史边界。"""

import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.db import DatabaseError, close_old_connections
from django.test import override_settings
from rest_framework.test import APIClient

from apps.analysis.models import (
    Analysis,
    AnalysisGraph,
    RelationReview,
    RelationReviewState,
)
from apps.analysis.reviews import submit_review
from apps.analysis.services import execute_analysis, query_graph
from apps.analysis.tests.test_analysis import imported, submitted
from apps.analysis.types import GraphQuery
from apps.explanations.context import build_payload
from apps.explanations.tests.test_adapter import OPTIONS
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)
URL = "/api/v1/analyses/{analysis_id}/relation-reviews/"


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


@pytest.fixture
def candidate() -> tuple[Analysis, str, list[str]]:
    snapshot = imported(
        {
            "root_urls.py": b"from django.urls import include, path\nurlpatterns = [path('api/', include('router_urls')), path('api/', include('router_urls'))]\n",
            "entry.ts": b"function submit(){fetch('/api/tasks/');}\n",
        }
    )
    job = submitted(snapshot)
    execute_analysis(str(job.pk))
    analysis = Analysis.objects.get(job=job)
    graph = query_graph(analysis, GraphQuery())
    edges = [edge for edge in graph["edges"] if edge["relation"] == "candidate_match"]
    assert len(edges) == 2
    return analysis, edges[0]["source_id"], sorted(edge["target_id"] for edge in edges)


def post(
    client: APIClient,
    analysis: Analysis,
    request_id: str,
    target: str,
    action: str,
    revision: int,
    key: str | None = None,
) -> Any:
    return client.post(
        URL.format(analysis_id=analysis.pk),
        {
            "request_id": request_id,
            "target_id": target,
            "action": action,
            "expected_revision": revision,
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),
    )


def test_decisions_history_replay_and_static_context_unchanged(
    candidate: tuple[Analysis, str, list[str]],
) -> None:
    analysis, request_id, targets = candidate
    client, schema = client_with_token(), contract_schema()
    path = URL.format(analysis_id=analysis.pk)
    before_analysis = Analysis.objects.values().get(pk=analysis.pk)
    before_graph = AnalysisGraph.objects.values().get(analysis=analysis)
    original_selection = query_graph(analysis, GraphQuery())
    with override_settings(MODEL_OPTIONS=OPTIONS):
        original_payload = build_payload(analysis, 0, None)
    empty = client.get(path, {"request_id": request_id})
    assert_response(empty, schema, URL)
    assert empty.json()["state"]["revision"] == 0 and empty.json()["count"] == 0
    assert not RelationReviewState.objects.exists()
    key = str(uuid.uuid4())
    actions = [
        ("confirm", targets[0]),
        ("confirm", targets[1]),
        ("exclude", targets[1]),
        ("reset", targets[1]),
        ("exclude", targets[0]),
        ("confirm", targets[0]),
    ]
    for index, (action, target) in enumerate(actions):
        response = post(
            client,
            analysis,
            request_id,
            target,
            action,
            index,
            key if index == 0 else None,
        )
        assert response.status_code == 201
        assert_response(response, schema, URL, "post")
        state = response.json()["state"]
        assert state["revision"] == index + 1
        if index == 1:
            assert state["confirmed_target_id"] == targets[1]
            assert state["excluded_target_ids"] == []
        if index == 2:
            assert state["confirmed_target_id"] is None
            assert state["excluded_target_ids"] == [targets[1]]
        if index == 3:
            assert (
                state["confirmed_target_id"] is None
                and not state["excluded_target_ids"]
            )
    replay = post(client, analysis, request_id, targets[0], "confirm", 0, key)
    assert replay.status_code == 200 and replay.json()["record"]["revision"] == 1
    assert replay.json()["state"]["revision"] == 6
    assert RelationReview.objects.count() == 6
    history = client.get(path, {"request_id": request_id, "page_size": "2"})
    assert_response(history, schema, URL)
    assert history.json()["count"] == 6
    assert [record["revision"] for record in history.json()["results"]] == [6, 5]
    assert request_id in history.json()["next"]
    assert client.get(history.json()["next"]).json()["state"]["revision"] == 6
    graph = client.get(f"/api/v1/analyses/{analysis.pk}/graph/").json()
    states = {item["target_id"]: item for item in graph["relation_reviews"]}
    assert states[targets[0]]["decision"] == "confirmed"
    assert states[targets[1]]["decision"] == "undecided"
    assert all(item["revision"] == 6 for item in states.values())
    assert (
        next(node for node in graph["nodes"] if node["id"] == request_id)["request"][
            "status"
        ]
        == "candidate"
    )
    endpoints = client.get(f"/api/v1/analyses/{analysis.pk}/endpoints/")
    assert_response(endpoints, schema, "/api/v1/analyses/{analysis_id}/endpoints/")
    reviews = [
        link["relation_review"]
        for endpoint in endpoints.json()["results"]
        for link in endpoint["frontend_links"]
    ]
    assert sorted(item["decision"] for item in reviews) == ["confirmed", "undecided"]
    assert Analysis.objects.values().get(pk=analysis.pk) == before_analysis
    assert AnalysisGraph.objects.values().get(analysis=analysis) == before_graph
    assert query_graph(analysis, GraphQuery()) == original_selection
    with override_settings(MODEL_OPTIONS=OPTIONS):
        assert build_payload(analysis, 0, None) == original_payload


def test_revision_conflict_and_same_key_conflict(
    candidate: tuple[Analysis, str, list[str]],
) -> None:
    analysis, request_id, targets = candidate
    client, key = client_with_token(), str(uuid.uuid4())
    assert (
        post(client, analysis, request_id, targets[0], "confirm", 0, key).status_code
        == 201
    )
    conflict = post(client, analysis, request_id, targets[1], "confirm", 0)
    assert (
        conflict.status_code == 409
        and conflict.json()["code"] == "RELATION_REVISION_CONFLICT"
    )
    assert conflict.json()["details"]["current_revision"] == 1
    changed = post(client, analysis, request_id, targets[0], "exclude", 1, key)
    assert (
        changed.status_code == 409 and changed.json()["code"] == "IDEMPOTENCY_CONFLICT"
    )
    assert RelationReview.objects.count() == 1


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_first_decisions(
    candidate: tuple[Analysis, str, list[str]], same_key: bool
) -> None:
    analysis, request_id, targets = candidate
    first = uuid.uuid4()
    keys = [first, first if same_key else uuid.uuid4()]

    def submit(key: uuid.UUID) -> str:
        close_old_connections()
        try:
            _, _, created = submit_review(
                analysis,
                key,
                uuid.UUID(request_id),
                uuid.UUID(targets[0]),
                "confirm",
                0,
            )
            return "created" if created else "replayed"
        except ApiProblem as error:
            return error.machine_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(submit, keys))
    assert results == (
        ["created", "replayed"]
        if same_key
        else ["RELATION_REVISION_CONFLICT", "created"]
    )
    assert RelationReview.objects.count() == 1
    assert RelationReviewState.objects.get(analysis=analysis).revision == 1


def test_only_original_candidate_can_be_reviewed(
    candidate: tuple[Analysis, str, list[str]],
) -> None:
    analysis, request_id, targets = candidate
    client = client_with_token()
    for target in (str(uuid.uuid4()), request_id):
        response = post(client, analysis, request_id, target, "confirm", 0)
        assert (
            response.status_code == 409
            and response.json()["code"] == "RELATION_NOT_CANDIDATE"
        )
    assert (
        post(client, analysis, str(uuid.uuid4()), targets[0], "confirm", 0).status_code
        == 404
    )
    other_job = submitted(analysis.snapshot)
    execute_analysis(str(other_job.pk))
    other = Analysis.objects.get(job=other_job)
    assert post(client, other, request_id, targets[0], "confirm", 0).status_code == 404
    other_edge = next(
        edge
        for edge in query_graph(other, GraphQuery())["edges"]
        if edge["relation"] == "candidate_match"
    )
    assert (
        post(
            client, analysis, request_id, other_edge["target_id"], "confirm", 0
        ).status_code
        == 409
    )
    assert (
        not RelationReview.objects.exists() and not RelationReviewState.objects.exists()
    )
    assert (
        client.get(
            URL.format(analysis_id=other.pk), {"request_id": other_edge["source_id"]}
        ).json()["state"]["revision"]
        == 0
    )
    static_job = submitted(imported({"entry.ts": b"fetch('/api/tasks/');\n"}))
    execute_analysis(str(static_job.pk))
    static = Analysis.objects.get(job=static_job)
    static_edge = next(
        edge
        for edge in query_graph(static, GraphQuery())["edges"]
        if edge["relation"] == "method_path_match"
    )
    assert (
        post(
            client,
            static,
            static_edge["source_id"],
            static_edge["target_id"],
            "confirm",
            0,
        ).status_code
        == 409
    )


@pytest.mark.parametrize(
    "change",
    [
        {"expected_revision": True},
        {"expected_revision": -1},
        {"expected_revision": "0"},
        {"expected_revision": 2147483647},
        {"action": "unknown"},
        {"action": None},
        {"target_id": None},
        {"request_id": "broken"},
        {"extra": "unknown"},
    ],
)
def test_invalid_decision_input(
    candidate: tuple[Analysis, str, list[str]], change: dict[str, Any]
) -> None:
    analysis, request_id, targets = candidate
    response = client_with_token().post(
        URL.format(analysis_id=analysis.pk),
        {
            "request_id": request_id,
            "target_id": targets[0],
            "action": "confirm",
            "expected_revision": 0,
            **change,
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 400
    assert not RelationReviewState.objects.exists()


def test_read_query_validation_and_write_protection(
    candidate: tuple[Analysis, str, list[str]],
) -> None:
    analysis, request_id, targets = candidate
    client, path = client_with_token(), URL.format(analysis_id=analysis.pk)
    for query in (
        "",
        "request_id=bad",
        f"request_id={request_id}&request_id={request_id}",
        f"request_id={request_id}&other=1",
        f"request_id={request_id}&page=0",
    ):
        assert client.get(path + "?" + query).status_code == 400
    assert client.get(path, {"request_id": request_id, "page": "2"}).status_code == 404
    assert (
        APIClient(enforce_csrf_checks=True).post(path, {}, format="json").status_code
        == 403
    )
    assert post(client, analysis, request_id, targets[0], "reset", 0).status_code == 201


def test_failure_rolls_back_state_and_record(
    candidate: tuple[Analysis, str, list[str]],
) -> None:
    analysis, request_id, targets = candidate
    client, key = client_with_token(), str(uuid.uuid4())
    with patch(
        "apps.analysis.reviews.RelationReview.objects.create",
        side_effect=DatabaseError("合成写入失败"),
    ):
        assert (
            post(
                client, analysis, request_id, targets[0], "confirm", 0, key
            ).status_code
            == 503
        )
    assert (
        not RelationReviewState.objects.exists() and not RelationReview.objects.exists()
    )
    assert (
        post(client, analysis, request_id, targets[0], "confirm", 0, key).status_code
        == 201
    )
    RelationReviewState.objects.filter(analysis=analysis).update(
        excluded_target_ids=["broken"]
    )
    response = client.get(
        URL.format(analysis_id=analysis.pk), {"request_id": request_id}
    )
    assert response.status_code == 500 and response.json()["code"] == "INTERNAL_ERROR"
