import uuid
from collections.abc import Callable
from datetime import timedelta
from importlib import import_module
from unittest.mock import patch

import pytest
from django.apps import apps
from django.db import DatabaseError, connection
from django.utils import timezone
from kombu.exceptions import OperationalError

from apps.jobs import services as jobs
from apps.jobs.models import Job, OperationLog, SystemCheck
from apps.jobs.services import (
    claim_source_scan,
    complete_source_scan,
    create_import_job,
    create_source_scan_job,
    dispatch_source_scan,
    execute_check,
    reconcile_expired,
)
from apps.jobs.tests.test_jobs import client_with_token, create_job, create_snapshot
from apps.labs.services import execute_run, submit_run
from apps.labs.system_services import submit_system_run
from apps.projects.models import Project
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)


def owner() -> Project:
    return Project.objects.create(name="审计样例", idempotency_key=uuid.uuid4())


def test_rejected_upload_and_origin_are_independent_of_jobs() -> None:
    project = owner()
    client = client_with_token()
    path = f"/api/v1/projects/{project.pk}/imports/"
    response = client.post(
        path, {}, format="multipart", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
    )
    assert response.status_code == 400
    assert not Job.objects.exists()
    rejected = OperationLog.objects.get()
    assert rejected.result == "rejected" and rejected.project_id == project.pk
    assert rejected.project_name == "审计样例"
    assert rejected.events[-1]["error_code"] == "VALIDATION_ERROR"
    client.credentials(HTTP_HOST="127.0.0.1:5173", HTTP_ORIGIN="http://evil.invalid")
    response = client.post(
        path, {}, format="multipart", HTTP_ORIGIN="http://evil.invalid"
    )
    assert response.status_code == 403
    assert OperationLog.objects.filter(error_code="ORIGIN_REJECTED").count() == 1


def test_idempotency_replay_keeps_each_attempt() -> None:
    project, key = owner(), uuid.uuid4()
    job, created = create_import_job(f"imports_create:{project.pk}", key, "0" * 64)
    replay, repeated = create_import_job(f"imports_create:{project.pk}", key, "0" * 64)
    assert created and not repeated and replay.pk == job.pk
    assert Job.objects.count() == 1
    assert set(OperationLog.objects.values_list("result", flat=True)) == {
        "accepted",
        "replayed",
    }
    assert OperationLog.objects.filter(project_name="审计样例").count() == 2


def test_source_scan_queue_failure_and_completion_have_events() -> None:
    parent = create_job(kind="import", source_kind="folder")
    job, _ = create_source_scan_job(
        uuid.uuid4(), uuid.uuid4(), "0" * 64, parent=parent, source_kind="folder"
    )
    with patch(
        "apps.jobs.services.app.send_task", side_effect=OperationalError("synthetic")
    ):
        assert not dispatch_source_scan(job)
    assert OperationLog.objects.get(job=job).result == "failed"
    assert OperationLog.objects.get(job=job).error_code == "QUEUE_UNAVAILABLE"
    other, _ = create_source_scan_job(create_snapshot().pk, uuid.uuid4(), "0" * 64)
    claim = claim_source_scan(str(other.pk))
    assert claim is not None
    assert complete_source_scan(
        str(other.pk), claim, lambda: f"/api/v1/source-scans/{uuid.uuid4()}/"
    )
    assert OperationLog.objects.get(job=other).result == "succeeded"
    assert [
        event["result"] for event in OperationLog.objects.get(job=other).events
    ] == ["accepted", "running", "succeeded"]


def test_retired_queued_tasks_never_reach_experiment_adapter() -> None:
    lab = create_job(kind="lab")
    check = create_job()
    with patch("apps.labs.adapter.observe") as observe:
        execute_run(str(lab.pk))
    execute_check(str(check.pk))
    observe.assert_not_called()
    for job in (lab, check):
        job.refresh_from_db()
        assert job.status == "failed" and job.error is not None
        assert job.error["code"] == "FEATURE_RETIRED"


@pytest.mark.parametrize(
    "invoke",
    [
        lambda: jobs.submit_check(uuid.uuid4()),
        lambda: jobs.complete_check(str(uuid.uuid4()), uuid.uuid4()),
        lambda: jobs.create_lab_job("retired", uuid.uuid4(), "0" * 64, None),
        lambda: jobs.complete_lab(str(uuid.uuid4()), uuid.uuid4(), lambda: "unused"),
        lambda: jobs.create_comparison_job(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "0" * 64
        ),
        lambda: jobs.complete_comparison(
            str(uuid.uuid4()), uuid.uuid4(), lambda: "unused"
        ),
        lambda: submit_run(uuid.uuid4(), {}),
        lambda: submit_system_run("container-network", uuid.uuid4(), {}),
    ],
)
def test_retired_services_refuse_before_any_persistence(
    invoke: Callable[[], object],
) -> None:
    with (
        patch("apps.jobs.services.app.send_task") as dispatch,
        pytest.raises(ApiProblem) as refused,
    ):
        invoke()
    assert refused.value.status_code == 410
    assert refused.value.machine_code == "FEATURE_RETIRED"
    dispatch.assert_not_called()
    assert not Job.objects.exists()
    assert not OperationLog.objects.exists()
    assert not SystemCheck.objects.exists()


def test_log_filters_include_rejections_and_reject_invalid_times() -> None:
    project = owner()
    OperationLog.objects.create(
        operation="import", result="rejected", project_id=project.pk
    )
    OperationLog.objects.create(
        operation="analysis", result="succeeded", project_id=project.pk
    )
    client = client_with_token()
    response = client.get(
        "/api/v1/operation-logs/",
        {
            "project_id": str(project.pk),
            "operation": "import",
            "result": "rejected",
            "started_after": (timezone.now() - timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 200 and response.json()["count"] == 1
    assert (
        client.get(
            "/api/v1/operation-logs/?started_after=2026-99-99T10:00:00Z"
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/v1/operation-logs/?started_after=2026-10-03T10:00:00"
        ).status_code
        == 400
    )
    assert client.get("/api/v1/operation-logs/?result=hidden").status_code == 400


def test_historical_summary_backfill_keeps_retired_get_links() -> None:
    job = create_job(status="succeeded")
    check = SystemCheck.objects.create(job=job)
    migration = import_module(
        "apps.jobs.migrations.0006_historical_operation_summaries"
    )
    migration.backfill_summaries(apps, connection.schema_editor())
    migration.backfill_summaries(apps, connection.schema_editor())
    assert OperationLog.objects.filter(job=job).count() == 1
    log = OperationLog.objects.get(job=job)
    assert log.operation == "system_check" and log.events[0]["legacy"]
    assert log.created_at == job.created_at
    client = client_with_token()
    detail = client.get(f"/api/v1/jobs/{job.pk}/")
    assert detail.status_code == 200
    assert detail.json()["result_url"] == f"/api/v1/system-checks/{check.pk}/"
    assert client.get(detail.json()["result_url"]).status_code == 200
    assert (
        client.get("/api/v1/operation-logs/?operation=system_check").json()["count"]
        == 1
    )


@pytest.mark.parametrize("operation", ["import", "retry"])
def test_abandoned_receive_lease_reconciles_without_creating_job(
    operation: str,
) -> None:
    from apps.jobs.cleanup import preview

    project = owner()
    log = OperationLog.objects.create(
        operation=operation, source_kind="folder", project_id=project.pk
    )
    assert preview("project", project)["receiving"]
    OperationLog.objects.filter(pk=log.pk).update(
        created_at=timezone.now() - timedelta(hours=1)
    )
    assert reconcile_expired() == 0
    assert preview("project", project)["can_delete"]
    log.refresh_from_db()
    assert log.result == "failed" and log.error_code == "RECEIVE_TIMEOUT"
    assert not Job.objects.exists()


def test_unavailable_audit_store_refuses_operation_before_dispatch() -> None:
    project, client = owner(), client_with_token()
    with (
        patch(
            "apps.jobs.audit_middleware.OperationLog.objects.create",
            side_effect=DatabaseError,
        ),
        patch("apps.jobs.services.app.send_task") as dispatch,
    ):
        response = client.post(
            f"/api/v1/projects/{project.pk}/imports/",
            {},
            format="multipart",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    assert (
        response.status_code == 503 and response.json()["code"] == "SERVICE_UNAVAILABLE"
    )
    dispatch.assert_not_called()
    assert not Job.objects.exists() and not OperationLog.objects.exists()


def test_rejected_retry_keeps_original_target_without_linking_a_new_job() -> None:
    source = create_snapshot()
    prior, _ = create_source_scan_job(source.pk, uuid.uuid4(), "0" * 64)
    prior.status = "failed"
    prior.save(update_fields=["status"])
    response = client_with_token().post(
        f"/api/v1/jobs/{prior.pk}/retries/",
        "{bad",
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 400
    log = OperationLog.objects.get(result="rejected")
    assert (
        log.job_id is None
        and log.project_id == source.project_id
        and log.snapshot_id == source.pk
    )
    assert log.events[0]["target_job_id"] == str(prior.pk)
