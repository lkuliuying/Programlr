import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import DatabaseError, close_old_connections
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.jobs.models import Job, SystemCheck
from apps.jobs.services import (
    EMPTY_DIGEST,
    complete_check,
    execute_check,
    reconcile_expired,
    submit_check,
)

pytestmark = pytest.mark.django_db
HOST = "127.0.0.1:5173"
ORIGIN = f"http://{HOST}"


def client_with_token() -> APIClient:
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/v1/csrf/", HTTP_HOST=HOST)
    assert response.status_code == 200
    client.credentials(
        HTTP_HOST=HOST,
        HTTP_ORIGIN=ORIGIN,
        HTTP_X_CSRFTOKEN=response.json()["csrf_token"],
    )
    return client


def create_job(**kwargs: object) -> Job:
    fields = {
        "idempotency_key": uuid.uuid4(),
        "request_digest": EMPTY_DIGEST,
        "expires_at": timezone.now() + timedelta(seconds=300),
        **kwargs,
    }
    return Job.objects.create(**fields)


def test_csrf_cookie_and_request_id() -> None:
    response = APIClient().get("/api/v1/csrf/", HTTP_HOST=HOST)
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert response["X-Request-ID"]
    cookie = response.cookies["csrftoken"]
    assert cookie["samesite"] == "Strict"
    assert not cookie["domain"]
    assert cookie["httponly"]


@pytest.mark.parametrize(
    "host,origin,token,code",
    [
        (HOST, ORIGIN, False, "CSRF_REJECTED"),
        (HOST, "", True, "ORIGIN_REJECTED"),
        (HOST, "http://evil.invalid", True, "ORIGIN_REJECTED"),
        (HOST, "null", True, "ORIGIN_REJECTED"),
        (HOST, "http://127.0.0.1:5174", True, "ORIGIN_REJECTED"),
        ("evil.invalid:5173", ORIGIN, True, "ORIGIN_REJECTED"),
        ("127.0.0.1:5174", ORIGIN, True, "ORIGIN_REJECTED"),
    ],
)
def test_anonymous_writes_enforce_boundary(
    host: str, origin: str, token: bool, code: str
) -> None:
    client = client_with_token()
    csrf = client.get("/api/v1/csrf/").json()["csrf_token"]
    headers = {"HTTP_HOST": host, "HTTP_ORIGIN": origin}
    if token:
        headers["HTTP_X_CSRFTOKEN"] = csrf
    # APIClient 的 credentials 优先于单次请求参数，攻击值必须写入实际请求头。
    client.credentials(**headers)
    response = client.post(
        "/api/v1/system-checks/",
        {},
        format="json",
        HTTP_HOST=host,
        HTTP_ORIGIN=origin,
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        HTTP_X_FORWARDED_HOST=HOST,
        HTTP_X_FORWARDED_PROTO="http",
    )
    assert response.status_code == 403
    assert response.json()["code"] == code
    assert Job.objects.count() == 0


def test_wrong_csrf_and_foreign_cookie() -> None:
    first = client_with_token()
    second = client_with_token()
    first.cookies = second.cookies
    response = first.post(
        "/api/v1/system-checks/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_REJECTED"


@pytest.mark.parametrize(
    "payload", [{"command": "invalid"}, [], None, "", {"kind": "analysis"}]
)
def test_fixed_input_rejected(payload: object) -> None:
    import json

    response = client_with_token().post(
        "/api/v1/system-checks/",
        json.dumps(payload),
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 400
    assert not Job.objects.exists()


def test_submit_complete_and_replay() -> None:
    client = client_with_token()
    key = str(uuid.uuid4())
    with patch("apps.jobs.services.app.send_task") as send:
        first = client.post(
            "/api/v1/system-checks/", {}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
        second = client.post(
            "/api/v1/system-checks/", {}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
    assert first.status_code == 202
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert send.call_count == 1
    execute_check(first.json()["id"])
    execute_check(first.json()["id"])
    detail = client.get(first["Location"])
    assert detail.json()["status"] == "succeeded"
    result = client.get(detail.json()["result_url"])
    assert result.json()["worker"] == "passed"
    assert result.json()["job_id"] == first.json()["id"]
    assert SystemCheck.objects.count() == 1
    assert "request_digest" not in detail.json()
    assert "idempotency_key" not in detail.json()
    assert detail.json()["created_at"].endswith("Z")


def test_publication_failure_is_retained() -> None:
    client = client_with_token()
    key = str(uuid.uuid4())
    with patch("apps.jobs.services.app.send_task", side_effect=OSError):
        response = client.post(
            "/api/v1/system-checks/", {}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
    assert response.status_code == 503
    detail = client.get(response["Location"])
    assert detail.status_code == 200
    assert detail.json()["error"]["code"] == "QUEUE_UNAVAILABLE"
    replay = client.post(
        "/api/v1/system-checks/", {}, format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "failed"
    execute_check(detail.json()["id"])
    assert not SystemCheck.objects.exists()


def test_conflicting_key() -> None:
    job = create_job(request_digest="0" * 64)
    response = client_with_token().post(
        "/api/v1/system-checks/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(job.idempotency_key),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_missing_key_and_wrong_media_type() -> None:
    client = client_with_token()
    assert client.post("/api/v1/system-checks/", {}, format="json").status_code == 400
    assert (
        client.post(
            "/api/v1/system-checks/", "{}", content_type="text/plain"
        ).status_code
        == 415
    )


@pytest.mark.parametrize(
    "query,code",
    [
        ("page=0", 400),
        ("page=-1", 400),
        ("page=x", 400),
        ("page_size=101", 400),
        ("page=1&page=2", 400),
        ("unexpected=1", 400),
        ("page=2", 404),
    ],
)
def test_pagination_invalid(query: str, code: int) -> None:
    assert client_with_token().get(f"/api/v1/jobs/?{query}").status_code == code


@pytest.mark.parametrize("body", ["", "  ", "{broken"])
def test_missing_or_malformed_body(body: str) -> None:
    response = client_with_token().post(
        "/api/v1/system-checks/",
        body,
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 400
    assert not Job.objects.exists()


def test_empty_list_and_relative_pagination() -> None:
    client = client_with_token()
    assert client.get("/api/v1/jobs/").json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }
    create_job()
    create_job()
    first = client.get("/api/v1/jobs/?page_size=1").json()
    assert first["next"] == "/api/v1/jobs/?page=2&page_size=1"
    assert (
        client.get(first["next"]).json()["results"][0]["id"]
        != first["results"][0]["id"]
    )


def test_reconcile_terminal_and_late_result() -> None:
    claim = uuid.uuid4()
    queued = create_job(expires_at=timezone.now() - timedelta(seconds=1))
    running = create_job(
        status="running",
        claim_id=claim,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert reconcile_expired() == 2
    assert reconcile_expired() == 0
    assert not complete_check(str(running.pk), claim)
    execute_check(str(queued.pk))
    assert not SystemCheck.objects.exists()
    assert set(Job.objects.values_list("status", flat=True)) == {"failed"}


def test_wrong_execution_claim() -> None:
    job = create_job(status="running", claim_id=uuid.uuid4())
    assert not complete_check(str(job.pk), uuid.uuid4())
    assert not SystemCheck.objects.exists()


def test_worker_failure_has_safe_error() -> None:
    job = create_job()
    with patch(
        "apps.jobs.services.complete_check",
        side_effect=RuntimeError("untrusted diagnostic"),
    ):
        execute_check(str(job.pk))
    job.refresh_from_db()
    assert job.status == "failed"
    assert job.error is not None
    assert job.error["code"] == "CHECK_FAILED"
    assert "untrusted" not in str(job.error)


def test_database_failure_is_visible() -> None:
    with patch(
        "apps.jobs.api.views.Job.objects.select_related", side_effect=DatabaseError
    ):
        response = client_with_token().get("/api/v1/jobs/")
    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"


@pytest.mark.django_db(transaction=True)
def test_concurrent_idempotency_and_worker_claim() -> None:
    key = uuid.uuid4()

    def submit() -> str:
        try:
            return str(submit_check(key)[0].pk)
        finally:
            close_old_connections()

    with (
        patch("apps.jobs.services.app.send_task") as send,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        ids = list(pool.map(lambda _: submit(), range(2)))
    assert ids[0] == ids[1]
    assert send.call_count == 1

    def execute() -> None:
        try:
            execute_check(ids[0])
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: execute(), range(2)))
    assert SystemCheck.objects.count() == 1


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/jobs/not-a-uuid/",
        f"/api/v1/jobs/{uuid.uuid4()}/",
        f"/api/v1/system-checks/{uuid.uuid4()}/",
    ],
)
def test_missing_resources_return_json(path: str) -> None:
    with override_settings(DEBUG=False):
        response = client_with_token().get(path)
    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"
