import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any

import pytest
from django.db import close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from rest_framework.test import APIClient

from apps.jobs.models import Job, NotificationRead, NotificationReadState
from apps.jobs.notifications import advance_read_through
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import HOST, ORIGIN, client_with_token, create_job
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)
LIST = "/api/v1/notifications/"
STATE = "/api/v1/notification-read-state/"


def terminal() -> Job:
    return create_job(kind="import", status=Job.Status.SUCCEEDED)


def test_notification_get_is_derived_paginated_and_never_creates_state() -> None:
    client, schema = client_with_token(), contract_schema()
    assert client.get(LIST).json()["unread_count"] == 0
    first, second = terminal(), terminal()
    failed = create_job(kind="analysis", status=Job.Status.FAILED)
    create_job(status=Job.Status.QUEUED)
    create_job(status=Job.Status.RUNNING)
    result = client.get(LIST + "?page_size=1")
    assert result.status_code == 200
    assert_response(result, schema, LIST)
    page = result.json()
    assert page["count"] == page["unread_count"] == 3
    assert page["read_through"] is None
    assert page["results"][0]["job"]["id"] == str(failed.pk)
    assert page["results"][0]["read"] is False
    seen = [failed.pk]
    while page["next"]:
        page = client.get(page["next"]).json()
        seen.append(uuid.UUID(page["results"][0]["job"]["id"]))
    assert seen == [failed.pk, second.pk, first.pk]
    assert (
        NotificationRead.objects.count() == NotificationReadState.objects.count() == 0
    )
    assert Job.objects.count() == 5
    for query in ("page=0", "page_size=101", "page=1&page=2", "q=anything"):
        assert client.get(LIST + "?" + query).status_code == 400
    assert client.get(LIST + "?page=99").status_code == 404


def test_historical_single_read_watermark_and_new_completion_remain_independent() -> (
    None
):
    client, schema = client_with_token(), contract_schema()
    first, second = terminal(), terminal()
    path = f"{LIST}{first.pk}/"
    result = client.patch(path, {"read": True}, format="json")
    assert result.status_code == 410 and result.json()["code"] == "FEATURE_RETIRED"
    assert_response(result, schema, "/api/v1/notifications/{job_id}/", "patch")
    assert client.patch(path, {"read": True}, format="json").status_code == 410
    assert not NotificationRead.objects.exists()
    NotificationRead.objects.create(job=first)
    page = client.get(LIST).json()
    assert page["unread_count"] == 1
    assert {item["job"]["id"]: item["read"] for item in page["results"]} == {
        str(first.pk): True,
        str(second.pk): False,
    }
    state = client.patch(STATE, {"read_through": page["as_of"]}, format="json")
    assert state.status_code == 410 and state.json()["code"] == "FEATURE_RETIRED"
    assert_response(state, schema, STATE, "patch")
    assert not NotificationReadState.objects.exists()
    NotificationReadState.objects.create(pk=1, read_through=page["as_of"])
    assert client.get(LIST).json()["unread_count"] == 0
    newer = terminal()
    page = client.get(LIST).json()
    assert page["unread_count"] == 1 and page["results"][0]["job"]["id"] == str(
        newer.pk
    )
    assert all(item["read"] for item in page["results"][1:])
    older = (timezone.now() - timedelta(days=1)).isoformat()
    assert (
        client.patch(STATE, {"read_through": older}, format="json").status_code == 410
    )
    assert client.get(LIST).json()["read_through"] == page["read_through"]
    assert NotificationReadState.objects.count() == 1 and Job.objects.count() == 3


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"read": False},
        {"read": 1},
        {"read": "true"},
        {"read": None},
        {"read": True, "other": 1},
        [],
    ],
)
def test_single_read_retired_before_payload_validation(payload: Any) -> None:
    job = terminal()
    result = client_with_token().patch(f"{LIST}{job.pk}/", payload, format="json")
    assert result.status_code == 410 and result.json()["code"] == "FEATURE_RETIRED"
    assert_response(result, contract_schema())
    assert not NotificationRead.objects.exists()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"read_through": None},
        {"read_through": 1},
        {"read_through": "2026-10-03"},
        {"read_through": "2026-10-03T01:00:00"},
        {"read_through": "invalid"},
        {"read_through": "2026-99-99T01:00:00Z"},
        {"read_through": "2999-01-01T00:00:00Z"},
        {"read_through": "2026-10-03T00:00:00Z", "extra": 1},
        [],
    ],
)
def test_read_through_retired_for_all_payloads(payload: Any) -> None:
    result = client_with_token().patch(STATE, payload, format="json")
    assert result.status_code == 410 and result.json()["code"] == "FEATURE_RETIRED"
    assert_response(result, contract_schema())
    assert not NotificationReadState.objects.exists()


def test_writes_preserve_origin_csrf_media_and_resource_boundaries() -> None:
    client = client_with_token()
    paths = [
        (f"{LIST}{terminal().pk}/", {"read": True}),
        (STATE, {"read_through": timezone.now().isoformat()}),
    ]
    for path, payload in paths:
        assert client.patch(path, payload, format="multipart").status_code == 410
        assert (
            client.patch(path, "", content_type="application/json").status_code == 410
        )
        assert client.patch(path + "?q=no", payload, format="json").status_code == 410
        anonymous = APIClient(enforce_csrf_checks=True)
        csrf = anonymous.patch(
            path, payload, format="json", HTTP_HOST=HOST, HTTP_ORIGIN=ORIGIN
        )
        assert csrf.status_code == 403 and csrf.json()["code"] == "CSRF_REJECTED"
        origin = anonymous.patch(
            path,
            payload,
            format="json",
            HTTP_HOST=HOST,
            HTTP_ORIGIN="http://untrusted.invalid",
        )
        assert origin.status_code == 403 and origin.json()["code"] == "ORIGIN_REJECTED"
    for identifier in (uuid.uuid4(), create_job(status=Job.Status.RUNNING).pk):
        assert (
            client.patch(
                f"{LIST}{identifier}/", {"read": True}, format="json"
            ).status_code
            == 410
        )
    assert (
        NotificationRead.objects.count() == NotificationReadState.objects.count() == 0
    )


def test_concurrent_read_watermarks_never_create_state() -> None:
    now = timezone.now()
    values = [now - timedelta(seconds=offset) for offset in (3, 1, 2, 4)]

    def advance(value: Any) -> None:
        close_old_connections()
        try:
            with pytest.raises(ApiProblem) as error:
                advance_read_through(value)
            assert error.value.machine_code == "FEATURE_RETIRED"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(advance, values))
    assert not NotificationReadState.objects.exists()


def test_new_migrations_reverse_without_changing_old_task_records() -> None:
    job = terminal()
    original: dict[str, Any] = dict(Job.objects.values().get(pk=job.pk))
    executor = MigrationExecutor(connection)
    current = executor.loader.graph.leaf_nodes()
    previous = [
        ("jobs", "0003_job_previous_job"),
        ("learning", "0002_exerciseattempt_previous_attempt_attemptreview_and_more"),
    ]
    try:
        executor.migrate(previous)
        old_job = executor.loader.project_state(previous).apps.get_model("jobs", "Job")
        legacy = old_job.objects.values().get(pk=job.pk)
        assert legacy == {field: original[field] for field in legacy}
        assert "jobs_notificationread" not in connection.introspection.table_names()
        assert (
            "learning_curriculumcardprogress"
            not in connection.introspection.table_names()
        )
        MigrationExecutor(connection).migrate(current)
        assert Job.objects.values().get(pk=job.pk) == original
        assert (
            not NotificationRead.objects.exists()
            and not NotificationReadState.objects.exists()
        )
    finally:
        MigrationExecutor(connection).migrate(current)


def test_historical_read_state_observation_does_not_move_watermark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = timezone.now()
    NotificationReadState.objects.create(pk=1, read_through=boundary)
    client = client_with_token()
    monkeypatch.setattr(
        "apps.jobs.api.notification_views.timezone.now",
        lambda: boundary + timedelta(seconds=1),
    )
    result = client.get(LIST)
    assert result.status_code == 200
    page = result.json()
    assert page["read_through"] == boundary.isoformat().replace("+00:00", "Z")
    assert page["as_of"] > page["read_through"]
    assert NotificationReadState.objects.get().read_through == boundary
    assert not NotificationRead.objects.exists()
