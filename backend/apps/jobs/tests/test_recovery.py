import multiprocessing
import os
import socket
import time
import uuid
from collections.abc import Callable
from datetime import timedelta
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.db import DatabaseError, connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings
from django.utils import timezone
from kombu.exceptions import OperationalError

from apps.analysis.models import Analysis, AnalysisGraph
from apps.analysis.services import execute_analysis, submit_analysis
from apps.analysis.tests.test_analysis import imported
from apps.jobs import services as jobs
from apps.jobs.models import Job, SystemCheck
from apps.jobs.retries import submit_retry
from apps.jobs.tests.test_jobs import client_with_token, create_job
from apps.projects.models import Snapshot, SourceFile
from apps.projects.services import (
    create_project,
    execute_import,
    source_content,
    submit_import,
)
from apps.projects.storage import storage_root
from apps.projects.tests.test_projects import upload

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def run_process(target: Callable[..., None], *args: Any, expected: int = 0) -> None:
    connections.close_all()
    process = multiprocessing.get_context("fork").Process(target=target, args=args)
    process.start()
    try:
        process.join(15)
        assert process.exitcode == expected
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
        process.close()


def submit(kind: str, key: uuid.UUID, snapshot_id: uuid.UUID) -> Job:
    if kind == "analysis":
        return submit_analysis(
            Snapshot.objects.get(pk=snapshot_id), key, "root_urls.py"
        )[0]
    if kind == "import":
        return submit_import(
            create_project(uuid.uuid4(), "恢复测试")[0], key, upload()
        )[0]
    return jobs.submit_check(key)[0]


def crash_before_dispatch(kind: str, key: uuid.UUID, snapshot_id: uuid.UUID) -> None:
    with (
        override_settings(JOB_QUEUE_TIMEOUT_SECONDS=1),
        patch(
            "apps.jobs.services.app.send_task", side_effect=lambda *a, **k: os._exit(23)
        ),
    ):
        submit(kind, key, snapshot_id)


def reconcile_in_process() -> None:
    call_command("reconcile_jobs", stdout=StringIO())


def assert_history_in_process(snapshot_id: uuid.UUID, job_id: uuid.UUID) -> None:
    client = client_with_token()
    assert client.get(f"/api/v1/snapshots/{snapshot_id}/").status_code == 200
    detail = client.get(f"/api/v1/jobs/{job_id}/")
    assert detail.status_code == 200 and detail.json()["status"] == "succeeded"
    assert client.get(detail.json()["result_url"]).status_code == 200
    assert client.get(detail.json()["result_url"] + "graph/").status_code == 200


@pytest.mark.parametrize("kind", ["system_check", "import", "analysis"])
def test_submit_process_death_after_commit_is_reconciled(kind: str) -> None:
    snapshot, key = imported(), uuid.uuid4()
    run_process(crash_before_dispatch, kind, key, snapshot.pk, expected=23)
    job = Job.objects.get(idempotency_key=key)
    assert job.status == "queued"
    time.sleep(max(0, (job.expires_at - timezone.now()).total_seconds()) + 0.05)
    run_process(reconcile_in_process)
    job.refresh_from_db()
    assert (
        job.status == "failed"
        and job.error is not None
        and job.error["code"] == "QUEUE_TIMEOUT"
    )
    for execute in (
        jobs.execute_check,
        execute_import if kind == "import" else execute_analysis,
    ):
        execute(str(job.pk))
    assert not Analysis.objects.exists() and not SystemCheck.objects.exists()
    assert Snapshot.objects.count() == 1
    assert not list((storage_root() / "staging").iterdir())


def crashing_worker(queue: str) -> None:
    from celery.contrib.testing.worker import start_worker

    import apps.analysis.tasks  # noqa: F401
    from config.celery import app

    with (
        override_settings(JOB_EXECUTION_TIMEOUT_SECONDS=1),
        patch(
            "apps.analysis.services.run_parser",
            side_effect=lambda *a, **k: os._exit(23),
        ),
    ):
        with start_worker(
            app,
            pool="solo",
            queues=[queue],
            perform_ping_check=False,
            shutdown_timeout=5,
        ):
            time.sleep(12)


def test_real_redis_worker_death_retry_and_restarted_reader() -> None:
    from celery.contrib.testing.worker import start_worker

    import apps.analysis.tasks  # noqa: F401
    from config.celery import app

    snapshot, key, queue = imported(), uuid.uuid4(), "m2-t04-" + uuid.uuid4().hex
    original_send = app.send_task

    def send(*args: Any, **kwargs: Any) -> Any:
        return original_send(*args, **kwargs, queue=queue)

    try:
        with patch("apps.jobs.services.app.send_task", side_effect=send):
            job = submit_analysis(snapshot, key, "root_urls.py")[0]
        run_process(crashing_worker, queue, expected=23)
        job.refresh_from_db()
        assert job.status == "running" and job.claim_id is not None
        time.sleep(max(0, (job.expires_at - timezone.now()).total_seconds()) + 0.05)
        run_process(reconcile_in_process)
        job.refresh_from_db()
        assert (
            job.status == "failed"
            and job.error is not None
            and job.error["code"] == "EXECUTION_TIMEOUT"
        )
        assert not jobs.complete_analysis(
            str(job.pk), job.claim_id, lambda: "unreachable"
        )
        with start_worker(
            app,
            pool="solo",
            queues=[queue],
            perform_ping_check=False,
            shutdown_timeout=10,
        ):
            with patch("apps.jobs.services.app.send_task", side_effect=send):
                retry = submit_retry(job, uuid.uuid4())[0]
            deadline = time.monotonic() + 15
            while retry.status in ("queued", "running") and time.monotonic() < deadline:
                time.sleep(0.1)
                retry.refresh_from_db()
        assert retry.status == "succeeded" and retry.previous_job_id == job.pk
        assert Analysis.objects.count() == 1 and AnalysisGraph.objects.count() == 1
        run_process(assert_history_in_process, snapshot.pk, retry.pk)
        source = (
            SourceFile.objects.select_related("snapshot")
            .filter(snapshot=snapshot)
            .first()
        )
        assert source is not None and source_content(source, 1, 1)
    finally:
        with app.connection_for_write() as broker:
            broker.default_channel.queue_delete(queue)


@pytest.mark.parametrize("kind", ["system_check", "import", "analysis"])
def test_lost_publish_ack_does_not_overwrite_success(kind: str) -> None:
    snapshot = imported()

    def deliver_then_fail(*args: Any, **kwargs: Any) -> None:
        execute = {
            "system_check": jobs.execute_check,
            "import": execute_import,
            "analysis": execute_analysis,
        }[kind]
        execute(kwargs["args"][0])
        raise OperationalError("untrusted diagnostic")

    with patch("apps.jobs.services.app.send_task", side_effect=deliver_then_fail):
        client = client_with_token()
        if kind == "import":
            response = client.post(
                f"/api/v1/projects/{snapshot.project_id}/imports/",
                {"archive": upload()},
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            )
        else:
            path, payload = (
                (
                    f"/api/v1/snapshots/{snapshot.pk}/analyses/",
                    {"root_urlconf": "root_urls.py"},
                )
                if kind == "analysis"
                else ("/api/v1/system-checks/", {})
            )
            response = client.post(
                path, payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
            )
    assert response.status_code == 503
    assert "投递未确认" in response.json()["message"]
    detail = client.get(response["Location"])
    assert detail.status_code == 200
    job = Job.objects.get(pk=detail.json()["id"])
    assert job.status == "succeeded" and job.error is None
    before = Job.objects.values().get(pk=job.pk)
    assert jobs.reconcile_expired() == 0
    assert Job.objects.values().get(pk=job.pk) == before


def test_result_write_crossing_deadline_rolls_back() -> None:
    claim = uuid.uuid4()
    job = create_job(status="running", claim_id=claim)
    before, after = job.expires_at - timedelta(seconds=1), job.expires_at
    with (
        patch("apps.jobs.services.timezone.now", side_effect=[before, before, after]),
        pytest.raises(TimeoutError),
    ):
        jobs.complete_check(str(job.pk), claim)
    assert not SystemCheck.objects.exists()
    job.refresh_from_db()
    assert job.status == "running"


def test_check_deadline_failure_and_database_error_are_safe() -> None:
    job = create_job()
    with patch("apps.jobs.services.complete_check", side_effect=TimeoutError):
        jobs.execute_check(str(job.pk))
    job.refresh_from_db()
    assert job.status == "failed" and job.error is not None
    assert job.error["code"] == "EXECUTION_TIMEOUT"
    with patch(
        "apps.jobs.services.Job.objects.filter",
        side_effect=DatabaseError("internal-diagnostic-example"),
    ):
        with pytest.raises(RuntimeError, match="检查领取需等待期限核对"):
            jobs.execute_check(str(job.pk))


@pytest.mark.parametrize("kind", ["system_check", "import", "analysis"])
def test_unavailable_broker_connection_is_bounded_and_retained(kind: str) -> None:
    from celery import Celery
    from kombu import Connection

    snapshot, key = imported(), uuid.uuid4()
    # 绑定但不监听本地临时端口，真实触发连接失败，不干扰现有 Redis 服务。
    with socket.socket() as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        with Celery(
            "unavailable-broker",
            broker=f"redis://127.0.0.1:{endpoint.getsockname()[1]}/0",
            set_as_current=False,
        ) as unavailable:
            unavailable.conf.update(
                task_ignore_result=True,
                task_publish_retry=False,
                broker_connection_timeout=0.2,
                broker_transport_options={
                    "socket_connect_timeout": 0.2,
                    "socket_timeout": 0.2,
                    "max_retries": 0,
                },
            )
            start = time.monotonic()
            # 显式连接避免运行环境的 CELERY_BROKER_URL 覆盖故障目标。
            with (
                Connection(
                    f"redis://127.0.0.1:{endpoint.getsockname()[1]}/0",
                    connect_timeout=0.2,
                    transport_options={
                        "socket_connect_timeout": 0.2,
                        "socket_timeout": 0.2,
                        "max_retries": 0,
                    },
                ) as broker,
                patch(
                    "apps.jobs.services.app.send_task",
                    side_effect=lambda *a, **k: unavailable.send_task(
                        *a,
                        **k,
                        connection=broker,
                        queue="m2-t04-unavailable-" + key.hex,
                    ),
                ),
            ):
                job = submit(kind, key, snapshot.pk)
    assert time.monotonic() - start < 5
    assert job.status == "failed" and job.error is not None
    assert job.error["code"] == "QUEUE_UNAVAILABLE"
    assert not Analysis.objects.exists() and not SystemCheck.objects.exists()
    assert not list((storage_root() / "staging").iterdir())


def test_reconciler_recovers_database_outage_and_is_repeatable() -> None:
    job = create_job(expires_at=timezone.now() - timedelta(seconds=1))
    original = jobs.reconcile_expired
    attempts = 0

    def reconcile() -> int:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise DatabaseError("untrusted diagnostic")
        return original()

    output = StringIO()
    with (
        patch(
            "apps.jobs.management.commands.reconcile_jobs.reconcile_expired",
            side_effect=reconcile,
        ),
        patch("apps.jobs.management.commands.reconcile_jobs.signal.signal"),
        patch("threading.Event.wait", side_effect=[False, True]),
    ):
        call_command("reconcile_jobs", loop=True, stdout=StringIO(), stderr=output)
    assert attempts == 2 and "数据库暂不可用" in output.getvalue()
    assert "untrusted" not in output.getvalue()
    job.refresh_from_db()
    assert job.status == "failed" and jobs.reconcile_expired() == 0


def test_additive_migration_keeps_existing_job_and_result() -> None:
    job = create_job()
    jobs.execute_check(str(job.pk))
    before = Job.objects.values().get(pk=job.pk)
    result = SystemCheck.objects.values().get(job=job)
    target = [("jobs", "0003_job_previous_job")]
    restore_targets = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        MigrationExecutor(connection).migrate(
            [("jobs", "0002_job_result_url_job_scope_job_snapshot_id_and_more")]
        )
        MigrationExecutor(connection).migrate(target)
        assert Job.objects.values().get(pk=job.pk) == before
        assert SystemCheck.objects.values().get(job=job) == result
    finally:
        # 回退 jobs 会连带回退依赖它的应用；恢复全部叶节点，避免污染后续测试。
        MigrationExecutor(connection).migrate(restore_targets)
