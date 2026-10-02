import json
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.db import DatabaseError, close_old_connections
from django.test import override_settings
from django.utils import timezone
from kombu.exceptions import OperationalError
from rest_framework.test import APIClient

from apps.analysis.models import Analysis, AnalysisGraph
from apps.analysis.runner import run_parser
from apps.analysis.services import execute_analysis, submit_analysis
from apps.analysis.tests.test_parser import SNAPSHOT_ID, fixture_sources
from apps.analysis.types import AnalysisFailed, Source
from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from apps.projects.models import Snapshot, SourceFile
from apps.projects.services import create_project, execute_import, submit_import
from apps.projects.storage import storage_root
from apps.projects.tests.test_archive import zip_bytes
from apps.projects.tests.test_projects import upload

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def imported(extra: dict[str, bytes] | None = None) -> Snapshot:
    project = create_project(uuid.uuid4(), "静态分析合成样例")[0]
    data = zip_bytes(
        {
            **{s.file_path: s.content.encode() for s in fixture_sources()},
            **(extra or {}),
        }
    )
    with patch("apps.jobs.services.app.send_task"):
        job = submit_import(project, uuid.uuid4(), upload(data))[0]
    execute_import(str(job.pk))
    return Snapshot.objects.get(job=job)


def submitted(snapshot: Snapshot) -> Job:
    with patch("apps.jobs.services.app.send_task"):
        return submit_analysis(snapshot, uuid.uuid4(), "root_urls.py")[0]


def test_snapshot_to_process_to_persisted_api_result() -> None:
    snapshot = imported({"broken.py": b"def bad(:\n", "ignored.ts": b"const x = 1;\n"})
    client, schema, key = client_with_token(), contract_schema(), str(uuid.uuid4())
    path = f"/api/v1/snapshots/{snapshot.pk}/analyses/"
    with patch("apps.jobs.services.app.send_task") as send:
        first = client.post(
            path,
            {"root_urlconf": "root_urls.py"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert first.status_code == 202
        assert_response(
            first, schema, "/api/v1/snapshots/{snapshot_id}/analyses/", "post"
        )
        again = client.post(
            path,
            {"root_urlconf": "root_urls.py"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
        conflict = client.post(
            path, {"root_urlconf": "views.py"}, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
        assert conflict.status_code == 409
        assert send.call_count == 1
    execute_analysis(first.json()["id"])
    job = Job.objects.get(pk=first.json()["id"])
    assert job.status == "succeeded" and job.snapshot_id == snapshot.pk
    assert job.result_url is not None
    analysis = Analysis.objects.get(job=job)
    assert (
        analysis.coverage["syntax_failed_files"] == 1
        and analysis.coverage["skipped_files"] == 1
    )
    assert analysis.coverage["complete"] is False
    assert len(analysis.endpoints) == 10
    for route, contract in (
        (job.result_url, "/api/v1/analyses/{analysis_id}/"),
        (job.result_url + "endpoints/", "/api/v1/analyses/{analysis_id}/endpoints/"),
        (
            job.result_url + "diagnostics/",
            "/api/v1/analyses/{analysis_id}/diagnostics/",
        ),
        (f"/api/v1/jobs/{job.pk}/", "/api/v1/jobs/{job_id}/"),
    ):
        response = client.get(route)
        assert response.status_code == 200
        assert_response(response, schema, contract)
    page = client.get(job.result_url + "endpoints/?page_size=2")
    assert page.json()["count"] == 10 and len(page.json()["results"]) == 2
    assert page.json()["next"].startswith(job.result_url)
    for query in ("page=0", "page_size=101", "page=1&page=2", "other=x"):
        assert client.get(job.result_url + "endpoints/?" + query).status_code == 400
    assert client.get(job.result_url + "endpoints/?page=99").status_code == 404
    execute_analysis(str(job.pk))
    assert Analysis.objects.filter(job=job).count() == 1
    other_snapshot = imported()
    other_job = submitted(other_snapshot)
    execute_analysis(str(other_job.pk))
    analysis.refresh_from_db()
    assert all(
        e["view"]["source_ref"]["snapshot_id"] == str(snapshot.pk)
        for e in analysis.endpoints
    )
    assert analysis.snapshot_id != Analysis.objects.get(job=other_job).snapshot_id


def test_queue_failure_and_missing_resources_are_explicit() -> None:
    snapshot, client = imported(), client_with_token()
    path = f"/api/v1/snapshots/{snapshot.pk}/analyses/"
    for target, root in (
        (path, "missing.py"),
        (f"/api/v1/snapshots/{uuid.uuid4()}/analyses/", "root_urls.py"),
    ):
        assert (
            client.post(
                target,
                {"root_urlconf": root},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            ).status_code
            == 404
        )
    for suffix in ("", "endpoints/", "diagnostics/"):
        assert (
            client.get(f"/api/v1/analyses/{uuid.uuid4()}/{suffix}").status_code == 404
        )
    with patch(
        "apps.jobs.services.app.send_task",
        side_effect=OperationalError("synthetic-private-marker"),
    ):
        response = client.post(
            path,
            {"root_urlconf": "root_urls.py"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    assert response.status_code == 503 and response["Location"]
    job = Job.objects.get(kind="analysis")
    assert job.error is not None
    assert job.status == "failed" and job.error["code"] == "QUEUE_UNAVAILABLE"
    assert "synthetic-private-marker" not in str(response.json()) + str(job.error)


@pytest.mark.parametrize(
    "failure",
    [
        AnalysisFailed("parser_process_failed"),
        RuntimeError("synthetic-private-marker"),
        DatabaseError("synthetic-private-marker"),
    ],
)
def test_overall_parser_failure_has_no_partial_result(failure: Exception) -> None:
    job = submitted(imported())
    with patch("apps.analysis.services.run_parser", side_effect=failure):
        execute_analysis(str(job.pk))
    job.refresh_from_db()
    assert job.error is not None
    assert job.status == "failed" and job.error["code"] == "ANALYSIS_FAILED"
    assert not Analysis.objects.exists() and "synthetic-private-marker" not in str(
        job.error
    )


def test_corrupt_snapshot_does_not_produce_analysis() -> None:
    snapshot = imported()
    source = SourceFile.objects.filter(snapshot=snapshot).first()
    assert source is not None
    (storage_root() / "snapshots" / str(snapshot.pk) / str(source.pk)).write_bytes(
        b"tampered"
    )
    job = submitted(snapshot)
    execute_analysis(str(job.pk))
    job.refresh_from_db()
    assert job.error is not None
    assert job.status == "failed" and job.error["code"] == "SNAPSHOT_NOT_READY"
    assert not Analysis.objects.exists()


def test_result_commit_failure_rolls_back_and_late_worker_cannot_publish() -> None:
    job = submitted(imported())
    with patch(
        "apps.analysis.services.Analysis.objects.create",
        side_effect=DatabaseError("synthetic-private-marker"),
    ):
        execute_analysis(str(job.pk))
    job.refresh_from_db()
    assert job.status == "failed" and not Analysis.objects.exists()
    late = submitted(Snapshot.objects.get())
    claim = jobs.claim_analysis(str(late.pk))
    assert claim is not None
    Job.objects.filter(pk=late.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert jobs.reconcile_expired() == 1
    with patch("apps.analysis.services.Analysis.objects.create") as create:
        assert not jobs.complete_analysis(str(late.pk), claim, create)
        create.assert_not_called()
    late.refresh_from_db()
    assert late.error is not None
    assert late.status == "failed" and late.error["code"] == "EXECUTION_TIMEOUT"


def test_concurrent_submit_and_claim_use_single_job() -> None:
    snapshot, key = imported(), uuid.uuid4()

    def submit() -> uuid.UUID:
        close_old_connections()
        try:
            return submit_analysis(snapshot, key, "root_urls.py")[0].pk
        finally:
            close_old_connections()

    with (
        patch("apps.jobs.services.app.send_task") as send,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        ids = list(pool.map(lambda _: submit(), range(2)))
    assert ids[0] == ids[1] and send.call_count == 1
    assert jobs.claim_analysis(str(ids[0])) is not None
    assert jobs.claim_analysis(str(ids[0])) is None


def test_real_subprocess_protocol_failure_timeout_and_code_nonexecution(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "must-not-exist"
    sources = fixture_sources() + [
        Source(
            "side_effect.py",
            f'open({str(marker)!r}, "w").write("unexpected")\nraise RuntimeError()\n',
        )
    ]
    result = run_parser(SNAPSHOT_ID, sources, "root_urls.py", 0)
    assert result["endpoints"] and not marker.exists()
    with pytest.raises(AnalysisFailed):
        run_parser(
            SNAPSHOT_ID, [Source("root_urls.py", "def invalid(:\n")], "root_urls.py", 0
        )
    with patch(
        "apps.analysis.runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(["fixed-parser"], 1),
    ):
        with pytest.raises(AnalysisFailed, match="静态分析"):
            run_parser(SNAPSHOT_ID, sources, "root_urls.py", 0)

    def malformed(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        kwargs["stdout"].write(json.dumps({"unknown": 1}).encode())
        return subprocess.CompletedProcess(args[0], 0)

    with patch("apps.analysis.runner.subprocess.run", side_effect=malformed):
        with pytest.raises(AnalysisFailed):
            run_parser(SNAPSHOT_ID, sources, "root_urls.py", 0)


def test_actual_redis_celery_analysis() -> None:
    from celery.contrib.testing.worker import start_worker

    import apps.analysis.tasks  # noqa: F401
    from config.celery import app

    snapshot, queue = imported(), "m2-t02-" + uuid.uuid4().hex
    original_send = app.send_task

    def send(*args: Any, **kwargs: Any) -> Any:
        return original_send(*args, **kwargs, queue=queue)

    with start_worker(
        app, pool="solo", queues=[queue], perform_ping_check=False, shutdown_timeout=10
    ):
        with patch("apps.jobs.services.app.send_task", side_effect=send):
            job = submit_analysis(snapshot, uuid.uuid4(), "root_urls.py")[0]
        deadline = time.monotonic() + 15
        while job.status in ("queued", "running") and time.monotonic() < deadline:
            time.sleep(0.1)
            job.refresh_from_db()
        assert job.status == "succeeded" and Analysis.objects.filter(job=job).exists()
        assert AnalysisGraph.objects.filter(analysis__job=job).exists()


def test_actual_parser_timeout_and_nonzero_exit_are_bounded() -> None:
    original_run = subprocess.run

    def stalled(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return original_run(
            [sys.executable, "-I", "-c", "import time; time.sleep(10)"], **kwargs
        )

    started = time.monotonic()
    with (
        patch("apps.analysis.runner.subprocess.run", side_effect=stalled),
        patch("apps.analysis.runner.PARSER_TIMEOUT_SECONDS", 0.1),
    ):
        with pytest.raises(AnalysisFailed) as failure:
            run_parser(SNAPSHOT_ID, fixture_sources(), "root_urls.py", 0)
    assert failure.value.reason == "parser_timeout" and time.monotonic() - started < 3

    def crashed(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return original_run(
            [sys.executable, "-I", "-c", "import os; os._exit(23)"], **kwargs
        )

    with patch("apps.analysis.runner.subprocess.run", side_effect=crashed):
        with pytest.raises(AnalysisFailed) as failure:
            run_parser(SNAPSHOT_ID, fixture_sources(), "root_urls.py", 0)
    assert failure.value.reason == "parser_process_failed"


def test_root_syntax_error_fails_task_and_local_request_guards_remain() -> None:
    snapshot = imported({"root_urls.py": b"def invalid(:\n"})
    job = submitted(snapshot)
    execute_analysis(str(job.pk))
    job.refresh_from_db()
    assert job.status == "failed" and job.error is not None
    assert job.error["details"]["reason"] == "root_urlconf_unavailable"
    assert not Analysis.objects.exists()
    path = f"/api/v1/snapshots/{snapshot.pk}/analyses/"
    response = APIClient(enforce_csrf_checks=True).post(
        path,
        {"root_urlconf": "root_urls.py"},
        format="json",
        HTTP_HOST="127.0.0.1:5173",
        HTTP_ORIGIN="http://127.0.0.1:5173",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 403 and response.json()["code"] == "CSRF_REJECTED"
