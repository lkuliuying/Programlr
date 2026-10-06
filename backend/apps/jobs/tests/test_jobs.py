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
    claim_source_scan,
    complete_source_scan,
    create_source_scan_job,
    dispatch_source_scan,
    execute_check,
    reconcile_expired,
)
from apps.projects.models import Project, Snapshot

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


def create_snapshot() -> Snapshot:
    project = Project.objects.create(name="任务隔离夹具", idempotency_key=uuid.uuid4())
    return Snapshot.objects.create(
        id=uuid.uuid4(),
        project=project,
        job=create_job(kind="import", status="succeeded"),
        summary={},
        manifest_digest="0" * 64,
    )


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
    assert response.status_code == 410
    assert response.json()["code"] == "FEATURE_RETIRED"
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
    assert first.status_code == second.status_code == 410
    send.assert_not_called()
    assert not Job.objects.exists()
    job = create_job(status="succeeded")
    SystemCheck.objects.create(job=job)
    detail = client.get(f"/api/v1/jobs/{job.pk}/")
    assert detail.json()["status"] == "succeeded"
    result = client.get(detail.json()["result_url"])
    assert result.json()["worker"] == "passed"
    assert result.json()["job_id"] == str(job.pk)
    assert SystemCheck.objects.count() == 1
    assert "request_digest" not in detail.json()
    assert "idempotency_key" not in detail.json()
    assert detail.json()["created_at"].endswith("Z")


def test_publication_failure_is_retained() -> None:
    job, _ = create_source_scan_job(create_snapshot().pk, uuid.uuid4(), "0" * 64)
    with patch("apps.jobs.services.app.send_task", side_effect=OSError):
        assert not dispatch_source_scan(job)
    detail = client_with_token().get(f"/api/v1/jobs/{job.pk}/")
    assert detail.status_code == 200
    assert detail.json()["error"]["code"] == "QUEUE_UNAVAILABLE"
    replay, created = create_source_scan_job(
        job.snapshot_id or uuid.uuid4(), job.idempotency_key, job.request_digest
    )
    assert not created and replay.status == "failed"
    assert claim_source_scan(str(job.pk)) is None
    assert not SystemCheck.objects.exists()


def test_conflicting_key() -> None:
    job = create_job(request_digest="0" * 64)
    response = client_with_token().post(
        "/api/v1/system-checks/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(job.idempotency_key),
    )
    assert response.status_code == 410
    assert response.json()["code"] == "FEATURE_RETIRED"
    assert Job.objects.count() == 1


def test_missing_key_and_wrong_media_type() -> None:
    client = client_with_token()
    assert client.post("/api/v1/system-checks/", {}, format="json").status_code == 410
    assert (
        client.post(
            "/api/v1/system-checks/", "{}", content_type="text/plain"
        ).status_code
        == 410
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
    assert response.status_code == 410
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
        kind="source_scan",
        status="running",
        claim_id=claim,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert reconcile_expired() == 2
    assert reconcile_expired() == 0
    with patch("apps.jobs.services.record_job_event") as event:
        assert not complete_source_scan(str(running.pk), claim, lambda: "unused")
    event.assert_not_called()
    execute_check(str(queued.pk))
    assert not SystemCheck.objects.exists()
    assert set(Job.objects.values_list("status", flat=True)) == {"failed"}


def test_wrong_execution_claim() -> None:
    job = create_job(kind="source_scan", status="running", claim_id=uuid.uuid4())
    with patch("apps.analysis.models.SourceScan.objects.create") as publish:
        assert not complete_source_scan(str(job.pk), uuid.uuid4(), publish)
    publish.assert_not_called()
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
    assert job.error["code"] == "FEATURE_RETIRED"
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
    key, snapshot_id = uuid.uuid4(), create_snapshot().pk

    def submit() -> str:
        try:
            job, created = create_source_scan_job(snapshot_id, key, "0" * 64)
            if created:
                dispatch_source_scan(job)
            return str(job.pk)
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
            claim = claim_source_scan(ids[0])
            if claim is not None:
                complete_source_scan(
                    ids[0], claim, lambda: "/api/v1/source-scans/offline/"
                )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: execute(), range(2)))
    assert Job.objects.get(pk=ids[0]).status == "succeeded"
    assert not SystemCheck.objects.exists()


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
