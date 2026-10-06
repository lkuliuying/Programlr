import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.jobs.api.operation_views import OPERATION_LABELS
from apps.jobs.models import OperationLog
from apps.jobs.tests.test_jobs import client_with_token, create_job

pytestmark = pytest.mark.django_db
PATH = "/api/v1/operation-logs/"
BASE = datetime(2026, 10, 3, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize("operation,label", list(OPERATION_LABELS.items()))
def test_search_matches_chinese_operation_names_and_internal_codes(
    operation: str, label: str
) -> None:
    log = OperationLog.objects.create(operation=operation)
    client = client_with_token()
    for query in [label, operation.upper()]:
        response = client.get(PATH, {"q": query})
        assert response.status_code == 200 and response.json()["count"] == 1
        assert response.json()["results"][0]["id"] == str(log.pk)


def test_search_uses_or_across_object_and_saved_project_names_in_all_projects() -> None:
    owner = uuid.uuid4()
    first = OperationLog.objects.create(
        operation="analysis", object_name="订单处理", project_id=owner
    )
    second = OperationLog.objects.create(
        operation="import", project_name="订单项目", project_id=uuid.uuid4()
    )
    OperationLog.objects.create(
        operation="explanation", object_name="其他处理器", project_id=owner
    )
    response = client_with_token().get(PATH, {"q": "订单"})
    assert response.status_code == 200 and response.json()["count"] == 2
    assert {row["id"] for row in response.json()["results"]} == {
        str(first.pk),
        str(second.pk),
    }


def test_deleted_project_summary_is_searchable_without_current_project_row() -> None:
    job = create_job(kind="analysis", status="succeeded", result_deleted_at=BASE)
    log = OperationLog.objects.create(
        operation="analysis",
        project_id=uuid.uuid4(),
        project_name="已清理仓库",
        job=job,
    )
    response = client_with_token().get(PATH, {"q": "清理仓库"})
    assert response.status_code == 200 and response.json()["count"] == 1
    row = response.json()["results"][0]
    assert row["id"] == str(log.pk) and row["result_deleted"]


def test_search_runs_before_count_and_pages_and_keeps_stable_numbers() -> None:
    records = [
        OperationLog.objects.create(operation="analysis", object_name="账单匹配")
        for _ in range(3)
    ]
    OperationLog.objects.create(operation="analysis", object_name="其他对象")
    client = client_with_token()
    response = client.get(PATH, {"q": "  账单  ", "page_size": "1"})
    assert response.status_code == 200 and response.json()["count"] == 3
    seen: list[tuple[str, int]] = []
    while True:
        page = response.json()
        assert page["count"] == 3
        seen.extend((row["id"], row["display_id"]) for row in page["results"])
        if page["next"] is None:
            break
        assert parse_qs(urlparse(page["next"]).query)["q"] == ["账单"]
        response = client.get(page["next"])
        assert response.status_code == 200
    assert dict(seen) == {str(row.pk): row.display_id for row in records}


def test_search_combines_with_type_result_project_and_both_time_ranges() -> None:
    owner = uuid.uuid4()
    expected = OperationLog.objects.create(
        operation="analysis",
        result="succeeded",
        project_id=owner,
        project_name="目标仓库",
        events=[{"result": "succeeded", "at": BASE.isoformat()}],
    )
    OperationLog.objects.filter(pk=expected.pk).update(
        created_at=BASE - timedelta(minutes=1)
    )
    OperationLog.objects.create(
        operation="import", result="succeeded", project_name="目标仓库"
    )
    OperationLog.objects.create(
        operation="analysis", result="failed", project_name="目标仓库"
    )
    response = client_with_token().get(
        PATH,
        {
            "page": "1",
            "page_size": "1",
            "project_id": str(owner),
            "operation": "analysis",
            "result": "succeeded",
            "started_after": (BASE - timedelta(minutes=2)).isoformat(),
            "started_before": BASE.isoformat(),
            "ended_after": BASE.isoformat(),
            "ended_before": BASE.isoformat(),
            "q": "目标",
        },
    )
    assert response.status_code == 200 and response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(expected.pk)


@pytest.mark.parametrize("query", ["", " \t\u3000 ", " " * 200])
def test_empty_and_whitespace_search_mean_all_operations(query: str) -> None:
    OperationLog.objects.create(operation="analysis")
    OperationLog.objects.create(operation="import")
    response = client_with_token().get(PATH, {"q": query})
    assert response.status_code == 200 and response.json()["count"] == 2


@pytest.mark.parametrize("query", ["x" * 201, " " + "x" * 200, "🙂" * 201, " " * 201])
def test_search_budget_applies_to_original_unicode_input(query: str) -> None:
    response = client_with_token().get(PATH, {"q": query})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_two_hundred_unicode_characters_are_supported() -> None:
    response = client_with_token().get(PATH, {"q": "🙂" * 200})
    assert response.status_code == 200 and response.json()["count"] == 0


def test_duplicate_search_is_rejected_without_reflecting_values() -> None:
    response = client_with_token().get(PATH, {"q": ["private-query", "private-query"]})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert b"private-query" not in response.content


@pytest.mark.parametrize("query", ["\x00", "private-left\x00private-right"])
def test_nul_search_is_rejected_before_database_query_without_writes(
    query: str,
) -> None:
    OperationLog.objects.create(operation="analysis", object_name="保留对象")
    client = client_with_token()
    original = list(OperationLog.objects.values())
    with CaptureQueriesContext(connection) as queries:
        response = client.get(PATH, {"q": query})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "q" in response.json()["details"]["fields"]
    assert b"private-left" not in response.content
    assert b"private-right" not in response.content
    assert list(OperationLog.objects.values()) == original
    assert not queries.captured_queries


@pytest.mark.parametrize("query", ["%", "_", "' OR 1=1 --"])
def test_search_treats_wildcards_and_sql_as_literal_substrings(query: str) -> None:
    expected = OperationLog.objects.create(
        operation="analysis", object_name=f"前缀{query}后缀"
    )
    OperationLog.objects.create(operation="analysis", object_name="其他对象")
    response = client_with_token().get(PATH, {"q": query})
    assert response.status_code == 200 and response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(expected.pk)


def test_search_does_not_read_internal_ids_errors_or_write_logs() -> None:
    log = OperationLog.objects.create(
        operation="analysis", request_id="internal-marker", error_code="internal-marker"
    )
    client = client_with_token()
    original = list(OperationLog.objects.values())
    with CaptureQueriesContext(connection) as queries:
        response = client.get(PATH, {"q": "internal-marker"})
        id_search = client.get(PATH, {"q": str(log.pk)})
    assert response.status_code == id_search.status_code == 200
    assert response.json()["count"] == id_search.json()["count"] == 0
    assert list(OperationLog.objects.values()) == original
    assert not any(
        query["sql"].lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE"))
        for query in queries.captured_queries
    )
