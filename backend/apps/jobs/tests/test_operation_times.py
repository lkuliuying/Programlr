import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.jobs.audit import finish_http, record_job_event
from apps.jobs.models import OperationLog
from apps.jobs.tests.test_jobs import client_with_token, create_job

pytestmark = pytest.mark.django_db
BASE = datetime(2026, 10, 3, 10, 0, tzinfo=UTC)
PATH = "/api/v1/operation-logs/"


def terminal_log(result: str = "succeeded", *, at: datetime = BASE) -> OperationLog:
    return OperationLog.objects.create(
        operation="analysis",
        result=result,
        events=[{"result": result, "at": at.isoformat()}],
    )


def test_list_and_detail_share_independent_start_and_end_times() -> None:
    started = BASE - timedelta(minutes=5)
    ended = BASE - timedelta(minutes=1)
    log = terminal_log(at=ended)
    OperationLog.objects.filter(pk=log.pk).update(created_at=started, updated_at=BASE)
    client = client_with_token()
    listing = client.get(PATH)
    detail = client.get(f"{PATH}{log.pk}/")
    assert listing.status_code == detail.status_code == 200
    row = listing.json()["results"][0]
    assert row == detail.json()
    assert row["started_at"] == row["created_at"] == "2026-10-03T09:55:00Z"
    assert row["ended_at"] == "2026-10-03T09:59:00Z"
    assert row["updated_at"] == "2026-10-03T10:00:00Z"


@pytest.mark.parametrize("result", ["submitted", "accepted", "running"])
def test_unfinished_operations_do_not_invent_end_times(result: str) -> None:
    log = terminal_log(result)
    # 非终态不能借用旧事件或 updated_at 伪造本次操作的完成时间。
    log.events.append({"result": "failed", "at": BASE.isoformat()})
    log.save()
    client = client_with_token()
    assert client.get(f"{PATH}{log.pk}/").json()["ended_at"] is None
    assert client.get(PATH, {"ended_before": BASE.isoformat()}).json()["count"] == 0


def test_first_reliable_terminal_event_remains_stable() -> None:
    log = OperationLog.objects.create(
        operation="analysis",
        result="succeeded",
        events=[
            {"result": "running", "at": BASE.isoformat()},
            {"result": "failed", "at": "2026-02-30T09:00:00Z"},
            {"result": "succeeded", "at": BASE.isoformat()},
            {
                "result": "succeeded",
                "at": (BASE + timedelta(hours=1)).isoformat(),
            },
        ],
    )
    client = client_with_token()
    assert client.get(f"{PATH}{log.pk}/").json()[
        "ended_at"
    ] == BASE.isoformat().replace("+00:00", "Z")
    log.updated_at = BASE + timedelta(hours=2)
    log.save(update_fields=["updated_at"])
    assert client.get(f"{PATH}{log.pk}/").json()["ended_at"] == "2026-10-03T10:00:00Z"


def test_http_replay_ends_at_its_response_before_original_job_finishes() -> None:
    job = create_job(kind="analysis", status="running")
    log = OperationLog.objects.create(
        operation="analysis",
        result="replayed",
        request_id="replay-request",
        job=job,
        events=[{"result": "replayed", "at": BASE.isoformat()}],
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "apps.jobs.audit.timezone.now", lambda: BASE + timedelta(seconds=1)
        )
        finish_http(log.pk, 200)
        patch.setattr("apps.jobs.audit.timezone.now", lambda: BASE + timedelta(hours=1))
        job.status = "succeeded"
        record_job_event(job)
        finish_http(log.pk, 200)
    detail = client_with_token().get(f"{PATH}{log.pk}/")
    assert detail.status_code == 200
    assert detail.json()["result"] == "replayed"
    assert detail.json()["ended_at"] == "2026-10-03T10:00:01Z"


def test_internal_replay_ends_at_its_own_replay_event() -> None:
    log = OperationLog.objects.create(
        operation="source_scan",
        result="replayed",
        events=[
            {"result": "replayed", "at": BASE.isoformat()},
            {"result": "succeeded", "at": (BASE + timedelta(hours=1)).isoformat()},
        ],
    )
    assert client_with_token().get(f"{PATH}{log.pk}/").json()["ended_at"] == (
        "2026-10-03T10:00:00Z"
    )


def test_missing_http_replay_response_is_unknown_even_when_original_job_finished() -> (
    None
):
    log = OperationLog.objects.create(
        operation="source_scan",
        result="replayed",
        request_id="response-not-persisted",
        events=[
            {"result": "replayed", "at": BASE.isoformat()},
            {"result": "succeeded", "at": (BASE + timedelta(hours=1)).isoformat()},
        ],
    )
    assert client_with_token().get(f"{PATH}{log.pk}/").json()["ended_at"] is None


def test_legacy_and_deleted_summaries_keep_known_times_without_read_writes() -> None:
    job = create_job(status="succeeded", result_deleted_at=BASE)
    log = OperationLog.objects.create(
        operation="system_check",
        result="succeeded",
        job=job,
        object_name="历史对象",
        events=[{"result": "succeeded", "at": BASE.isoformat(), "legacy": True}],
    )
    client = client_with_token()
    before = list(OperationLog.objects.values())
    with CaptureQueriesContext(connection) as queries:
        listing = client.get(PATH)
        detail = client.get(f"{PATH}{log.pk}/")
    assert listing.status_code == detail.status_code == 200
    assert listing.json()["results"][0] == detail.json()
    assert detail.json()["ended_at"] == "2026-10-03T10:00:00Z"
    assert detail.json()["object_name"] == "历史对象"
    assert detail.json()["result_deleted"]
    assert list(OperationLog.objects.values()) == before
    assert not any(
        query["sql"].lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE"))
        for query in queries.captured_queries
    )


@pytest.mark.parametrize(
    "events",
    [
        [],
        {},
        "historical-invalid",
        [None, 3, [], "text"],
        [
            {"result": "succeeded", "at": "2026-02-30T09:00:00Z"},
            {"result": "succeeded", "at": "2026-10-03T10:00:00+99:00"},
            {"result": "succeeded", "at": "2026-10-03T10:00:00"},
            {"result": "succeeded", "at": "infinity"},
            {"result": "succeeded", "at": "10000-10-03T10:00:00Z"},
            {"result": "succeeded", "at": "0000-10-03T10:00:00Z"},
            {"result": "succeeded", "at": 1},
            {"result": "succeeded", "at": None},
            {"result": "succeeded"},
        ],
    ],
)
def test_invalid_historical_events_do_not_break_time_reads(events: object) -> None:
    log = OperationLog.objects.create(
        operation="analysis", result="succeeded", events=events
    )
    client = client_with_token()
    detail = client.get(f"{PATH}{log.pk}/")
    assert detail.status_code == 200 and detail.json()["ended_at"] is None
    assert all(isinstance(item, dict) for item in detail.json()["events"])
    listing = client.get(PATH, {"ended_after": BASE.isoformat()})
    assert listing.status_code == 200 and listing.json()["count"] == 0


def test_end_filter_uses_inclusive_boundaries_before_count_and_pagination() -> None:
    first = terminal_log(at=BASE)
    second = terminal_log(at=BASE + timedelta(minutes=1))
    terminal_log(at=BASE + timedelta(minutes=2))
    terminal_log("running", at=BASE)
    client = client_with_token()
    filters = {
        "ended_after": "2026-10-03T18:00:00+08:00",
        "ended_before": "2026-10-03T18:01:00+08:00",
        "page_size": "1",
        "operation": "analysis",
    }
    response = client.get(PATH, filters)
    assert response.status_code == 200
    page = response.json()
    assert page["count"] == 2 and page["previous"] is None
    query = parse_qs(urlparse(page["next"]).query)
    assert query["ended_after"] == [filters["ended_after"]]
    assert query["ended_before"] == [filters["ended_before"]]
    other = client.get(page["next"])
    assert other.status_code == 200
    assert other.json()["count"] == 2 and other.json()["next"] is None
    assert {page["results"][0]["id"], other.json()["results"][0]["id"]} == {
        str(first.pk),
        str(second.pk),
    }


def test_start_and_end_ranges_remain_independent() -> None:
    matching = terminal_log(at=BASE)
    other = terminal_log(at=BASE)
    OperationLog.objects.filter(pk=matching.pk).update(
        created_at=BASE - timedelta(minutes=1)
    )
    OperationLog.objects.filter(pk=other.pk).update(
        created_at=BASE - timedelta(minutes=5)
    )
    response = client_with_token().get(
        PATH,
        {
            "started_after": (BASE - timedelta(minutes=2)).isoformat(),
            "started_before": (BASE - timedelta(seconds=30)).isoformat(),
            "ended_after": BASE.isoformat(),
            "ended_before": BASE.isoformat(),
        },
    )
    assert response.status_code == 200 and response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(matching.pk)


@pytest.mark.parametrize("name", ["ended_after", "ended_before"])
@pytest.mark.parametrize(
    "value",
    ["", "invalid", "2026-02-30T10:00:00Z", "2026-10-03T10:00:00", "2026-10-03"],
)
def test_invalid_end_filter_is_rejected(name: str, value: str) -> None:
    response = client_with_token().get(PATH, {name: value})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("name", ["ended_after", "ended_before"])
def test_duplicate_end_filter_is_rejected(name: str) -> None:
    response = client_with_token().get(
        PATH, {name: [BASE.isoformat(), BASE.isoformat()]}
    )
    assert response.status_code == 400


@pytest.mark.parametrize("prefix", ["started", "ended"])
def test_reversed_time_range_is_rejected(prefix: str) -> None:
    response = client_with_token().get(
        PATH,
        {
            f"{prefix}_after": (BASE + timedelta(minutes=1)).isoformat(),
            f"{prefix}_before": BASE.isoformat(),
        },
    )
    assert response.status_code == 400


def test_all_ten_log_query_fields_work_without_changing_global_field_limit() -> None:
    owner = uuid.uuid4()
    for _ in range(2):
        log = terminal_log()
        OperationLog.objects.filter(pk=log.pk).update(
            project_id=owner,
            project_name="组合样例",
            created_at=BASE - timedelta(minutes=1),
        )
    filters = {
        "page": "1",
        "page_size": "1",
        "project_id": str(owner),
        "operation": "analysis",
        "result": "succeeded",
        "started_after": (BASE - timedelta(minutes=2)).isoformat(),
        "started_before": BASE.isoformat(),
        "ended_after": BASE.isoformat(),
        "ended_before": BASE.isoformat(),
        "q": "组合样例",
    }
    client = client_with_token()
    response = client.get(PATH, filters)
    assert response.status_code == 200
    assert response.json()["count"] == 2
    following = response.json()["next"]
    query = parse_qs(urlparse(following).query)
    assert len(query) == 10 and query["page"] == ["2"]
    for name, value in filters.items():
        if name != "page":
            assert query[name] == [value]
    assert client.get(following).status_code == 200
    assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS == 5


def test_eleventh_log_query_field_is_bounded_and_does_not_reflect_values() -> None:
    filters = {
        "page": "1",
        "page_size": "1",
        "project_id": str(uuid.uuid4()),
        "operation": "analysis",
        "result": "succeeded",
        "started_after": BASE.isoformat(),
        "started_before": BASE.isoformat(),
        "ended_after": BASE.isoformat(),
        "ended_before": BASE.isoformat(),
        "q": "组合样例",
        "private_marker": "DO_NOT_REFLECT",
    }
    response = client_with_token().get(PATH, filters)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert b"DO_NOT_REFLECT" not in response.content


def test_repeated_filter_is_rejected_even_with_more_than_five_fields() -> None:
    entries = [
        ("page", "1"),
        ("page_size", "1"),
        ("operation", "analysis"),
        ("result", "succeeded"),
        ("ended_after", BASE.isoformat()),
        ("operation", "analysis"),
    ]
    response = client_with_token().get(f"{PATH}?{urlencode(entries)}")
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "operation" in response.json()["details"]["fields"]


@pytest.mark.parametrize(
    "query",
    ["operation=analysis&missing_equals", "operation=%FF", "private_marker=%GG"],
)
def test_malformed_query_is_rejected_without_reflecting_input(query: str) -> None:
    response = client_with_token().get(f"{PATH}?{query}")
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert b"missing_equals" not in response.content
    assert b"%FF" not in response.content
    assert b"%GG" not in response.content


def test_log_query_text_has_an_independent_length_budget() -> None:
    response = client_with_token().get(f"{PATH}?operation=" + "x" * 4097)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_other_endpoints_keep_the_five_field_limit() -> None:
    entries = {
        "page": "1",
        "page_size": "1",
        "kind": "source_scan",
        "snapshot_id": str(uuid.uuid4()),
        "private_marker": "DO_NOT_REFLECT",
        "another": "DO_NOT_REFLECT",
    }
    response = client_with_token().get("/api/v1/jobs/", entries)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["message"] == "请求字段数量超过接口限制。"
    assert b"DO_NOT_REFLECT" not in response.content
    assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS == 5
