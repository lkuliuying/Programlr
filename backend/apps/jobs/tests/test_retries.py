import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.db import DatabaseError, close_old_connections, connections
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analysis.models import Analysis, AnalysisGraph, AnalysisRequest
from apps.analysis.services import execute_analysis
from apps.analysis.tests.test_analysis import imported
from apps.analysis.tests.test_analysis import submitted as submitted_analysis
from apps.jobs.models import Job, SystemCheck
from apps.jobs.retries import submit_retry
from apps.jobs.services import execute_check, reconcile_expired
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token, create_job
from apps.projects.models import ImportRequest, Snapshot, SourceFile
from apps.projects.services import execute_import, source_content
from apps.projects.storage import storage_root
from apps.projects.tests.test_archive import zip_bytes
from apps.projects.tests.test_projects import submitted, upload
from common.errors import Conflict

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def fail(job: Job) -> Job:
    Job.objects.filter(pk=job.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    reconcile_expired()
    job.refresh_from_db()
    assert job.status == "failed"
    return job


def retry_path(job: Job) -> str:
    return f"/api/v1/jobs/{job.pk}/retries/"


def test_check_retry_replay_history_and_contract() -> None:
    previous = fail(create_job())
    before = client_with_token().get(f"/api/v1/jobs/{previous.pk}/").json()
    client, key = client_with_token(), str(uuid.uuid4())
    with patch("apps.jobs.services.app.send_task") as send:
        first = client.post(
            retry_path(previous), {}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
        assert first.status_code == 202
        replay = client.post(
            retry_path(previous), {}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
    assert replay.status_code == 200 and replay.json()["id"] == first.json()["id"]
    assert send.call_count == 1
    assert first.json()["previous_job_id"] == str(previous.pk)
    assert_response(first, contract_schema(), "/api/v1/jobs/{job_id}/retries/", "post")
    execute_check(first.json()["id"])
    connections.close_all()
    fresh = client_with_token()
    result = fresh.get(first["Location"]).json()
    assert result["status"] == "succeeded"
    assert fresh.get(result["result_url"]).json()["job_id"] == first.json()["id"]
    assert fresh.get(f"/api/v1/jobs/{previous.pk}/").json() == before
    assert fresh.get("/api/v1/jobs/").json()["count"] == 2
    with patch("apps.jobs.services.app.send_task") as send:
        replay = fresh.post(
            retry_path(previous), {}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
    assert replay.json() == result
    send.assert_not_called()


def test_analysis_retry_preserves_snapshot_and_root_with_new_result() -> None:
    snapshot = imported()
    old_success = submitted_analysis(snapshot)
    execute_analysis(str(old_success.pk))
    old_analysis = Analysis.objects.get(job=old_success)
    previous = fail(submitted_analysis(snapshot))
    with patch("apps.jobs.services.app.send_task"):
        job, created, published = submit_retry(previous, uuid.uuid4())
    assert created and published and job.previous_job_id == previous.pk
    record = AnalysisRequest.objects.get(job=job)
    assert record.snapshot_id == snapshot.pk and record.root_urlconf == "root_urls.py"
    execute_analysis(str(job.pk))
    connections.close_all()
    job.refresh_from_db()
    assert job.status == "succeeded" and job.snapshot_id == snapshot.pk
    assert Analysis.objects.count() == 2 and AnalysisGraph.objects.count() == 2
    client = client_with_token()
    assert job.result_url is not None
    assert client.get(job.result_url).status_code == 200
    assert client.get(f"/api/v1/analyses/{old_analysis.pk}/graph/").status_code == 200
    assert client.get(f"/api/v1/snapshots/{snapshot.pk}/").status_code == 200


def test_import_retry_reuploads_original_and_cleans_conflicting_input() -> None:
    archive = zip_bytes({"a.py": b"one\r\ntwo\n"})
    old_success = submitted()
    execute_import(str(old_success.pk))
    old_source = SourceFile.objects.select_related("snapshot").get()
    with patch("apps.jobs.services.app.send_task", side_effect=OSError):
        from apps.projects.services import submit_import

        previous = submit_import(
            old_source.snapshot.project, uuid.uuid4(), upload(archive)
        )[0]
    assert previous.status == "failed"
    assert not list((storage_root() / "staging").iterdir())
    client, key = client_with_token(), str(uuid.uuid4())
    with patch("apps.jobs.services.app.send_task") as send:
        first = client.post(
            retry_path(previous), {"archive": upload(archive)}, HTTP_IDEMPOTENCY_KEY=key
        )
        replay = client.post(
            retry_path(previous), {"archive": upload(archive)}, HTTP_IDEMPOTENCY_KEY=key
        )
        conflict = client.post(
            retry_path(previous),
            {"archive": upload(zip_bytes({"other.py": b"x=1"}))},
            HTTP_IDEMPOTENCY_KEY=key,
        )
    assert first.status_code == 202 and replay.status_code == 200
    assert (
        conflict.status_code == 409
        and conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    )
    assert send.call_count == 1
    job = Job.objects.get(pk=first.json()["id"])
    assert job.previous_job_id == previous.pk and job.snapshot_id is None
    assert (
        ImportRequest.objects.get(job=job).storage_id
        != ImportRequest.objects.get(job=previous).storage_id
    )
    execute_import(str(job.pk))
    execute_import(str(previous.pk))
    job.refresh_from_db()
    assert job.status == "succeeded" and Snapshot.objects.count() == 2
    assert source_content(old_source, 1, 2) == "one\ntwo\n"
    assert not list((storage_root() / "staging").iterdir())


@pytest.mark.parametrize("status", ["queued", "running", "succeeded"])
def test_non_failed_retry_rejected(status: str) -> None:
    previous = create_job(status=status)
    response = client_with_token().post(
        retry_path(previous), {}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
    )
    assert (
        response.status_code == 409 and response.json()["code"] == "JOB_NOT_RETRYABLE"
    )
    assert Job.objects.count() == 1


@pytest.mark.parametrize(
    "body",
    [
        "",
        " ",
        "null",
        "[]",
        '""',
        '{"root_urlconf":"other.py"}',
        '{"snapshot_id":"other"}',
        "{bad",
    ],
)
def test_invalid_retry_json_creates_nothing(body: str) -> None:
    previous = fail(create_job())
    response = client_with_token().post(
        retry_path(previous),
        body,
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 400 and Job.objects.count() == 1


def test_missing_reused_keys_unknown_kind_and_query_rejected() -> None:
    previous, client = fail(create_job()), client_with_token()
    for key, status in [
        (None, 400),
        ("invalid", 400),
        (str(previous.idempotency_key), 409),
    ]:
        headers: dict[str, Any] = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        response = client.post(retry_path(previous), {}, format="json", **headers)
        assert response.status_code == status
    response = client.post(
        retry_path(previous) + "?unknown=1",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 400
    Job.objects.filter(pk=previous.pk).update(kind="unsupported_kind")
    response = client.post(
        retry_path(previous), {}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
    )
    assert response.status_code == 409 and Job.objects.count() == 1


def test_retry_input_missing_and_wrong_archive_are_explicit() -> None:
    client = client_with_token()
    for kind in ("analysis", "import"):
        previous = fail(create_job(kind=kind))
        args = (
            {"data": {"archive": upload()}}
            if kind == "import"
            else {"data": {}, "format": "json"}
        )
        response = client.post(
            retry_path(previous), HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()), **args
        )
        assert (
            response.status_code == 409
            and response.json()["code"] == "RETRY_INPUT_UNAVAILABLE"
        )
    previous = fail(submitted())
    for payload in (
        {},
        {"archive": "text"},
        {"archive": upload(), "extra": "x"},
        {"archive": [upload(), upload()]},
    ):
        response = client.post(
            retry_path(previous), payload, HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert response.status_code in (400, 413)
    response = client.post(
        retry_path(previous),
        {"archive": upload(b"not a zip")},
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 400 and response.json()["code"] == "INVALID_ARCHIVE"
    with pytest.raises(Conflict), patch("apps.jobs.services.app.send_task"):
        submit_retry(
            previous, uuid.uuid4(), upload(zip_bytes({"different.py": b"x=1"}))
        )


def test_retry_source_protection_and_upload_budget() -> None:
    previous = fail(submitted())
    response = APIClient(enforce_csrf_checks=True).post(
        retry_path(previous),
        {"archive": upload()},
        HTTP_HOST="127.0.0.1:5173",
        HTTP_ORIGIN="http://127.0.0.1:5173",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 403 and response.json()["code"] == "CSRF_REJECTED"
    client = client_with_token()
    client.credentials(HTTP_HOST="127.0.0.1:5173", HTTP_ORIGIN="http://evil.invalid")
    assert (
        client.post(
            retry_path(previous),
            {"archive": upload()},
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        ).status_code
        == 403
    )
    with override_settings(IMPORT_LIMITS={"archive_bytes": 8}):
        response = client_with_token().post(
            retry_path(previous),
            {"archive": upload()},
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    assert (
        response.status_code == 413
        and response.json()["code"] == "ARCHIVE_LIMIT_EXCEEDED"
    )


def test_retry_dispatch_failure_and_second_attempt_chain() -> None:
    previous, key = fail(create_job()), uuid.uuid4()
    with patch("apps.jobs.services.app.send_task", side_effect=OSError):
        response = client_with_token().post(
            retry_path(previous), {}, format="json", HTTP_IDEMPOTENCY_KEY=str(key)
        )
    assert response.status_code == 503
    child = Job.objects.get(previous_job=previous)
    assert child.error is not None
    assert child.status == "failed" and child.error["code"] == "QUEUE_UNAVAILABLE"
    with patch("apps.jobs.services.app.send_task") as send:
        replay, created, _ = submit_retry(previous, key)
        assert not created and replay.pk == child.pk
        send.assert_not_called()
        newest = submit_retry(child, uuid.uuid4())[0]
    assert newest.previous_job_id == child.pk and newest.pk != child.pk
    execute_check(str(newest.pk))
    assert SystemCheck.objects.filter(job=newest).exists()
    assert Job.objects.filter(status="failed").count() == 2


def test_concurrent_retry_has_one_job_request_and_dispatch() -> None:
    previous = fail(submitted_analysis(imported()))
    key = uuid.uuid4()

    def submit() -> str:
        try:
            return str(submit_retry(Job.objects.get(pk=previous.pk), key)[0].pk)
        finally:
            close_old_connections()

    with (
        patch("apps.jobs.services.app.send_task") as send,
        ThreadPoolExecutor(max_workers=4) as pool,
    ):
        ids = list(pool.map(lambda _: submit(), range(4)))
    assert len(set(ids)) == 1 and send.call_count == 1
    assert AnalysisRequest.objects.filter(job__previous_job=previous).count() == 1


def test_retry_database_failure_rolls_back_before_dispatch() -> None:
    previous = fail(submitted_analysis(imported()))
    with (
        patch(
            "apps.analysis.services.AnalysisRequest.objects.create",
            side_effect=DatabaseError,
        ),
        patch("apps.jobs.services.app.send_task") as send,
    ):
        response = client_with_token().post(
            retry_path(previous),
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    assert response.status_code == 503
    assert not Job.objects.filter(previous_job=previous).exists()
    send.assert_not_called()
