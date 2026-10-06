"""操作事件独立保存，任务和业务结果清理不能删除审计记录。"""

import uuid
from contextvars import ContextVar
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.jobs.models import DeletionRequest, Job, OperationLog

active_log: ContextVar[uuid.UUID | None] = ContextVar("operation_log", default=None)


def event(result: str, **values: Any) -> dict[str, Any]:
    return {"result": result, "at": timezone.now().isoformat(), **values}


def deletion_record(job: Job) -> DeletionRequest | None:
    record = DeletionRequest.objects.filter(
        Q(initial_job=job) | Q(current_job=job)
    ).first()
    cursor = job.previous_job_id
    visited = {job.pk}
    while record is None and cursor is not None and cursor not in visited:
        visited.add(cursor)
        record = DeletionRequest.objects.filter(initial_job_id=cursor).first()
        if record is None:
            cursor = Job.objects.get(pk=cursor).previous_job_id
    return record


def target_values(job: Job) -> dict[str, Any]:
    from apps.projects.models import ImportRequest, Project, Snapshot

    values: dict[str, Any] = {"source_kind": job.source_kind}
    if job.kind == "import" and not job.source_kind:
        values["source_kind"] = (
            ImportRequest.objects.filter(job=job)
            .values_list("source_kind", flat=True)
            .first()
            or "zip"
        )
    if job.kind == "delete":
        deletion = deletion_record(job)
        if deletion:
            values.update(
                project_id=deletion.project_id,
                project_name=deletion.project_name,
                object_name=deletion.object_name,
                snapshot_id=deletion.target_id
                if deletion.target_type == "snapshot"
                else None,
            )
            return values
    if job.snapshot_id:
        values["snapshot_id"] = job.snapshot_id
        snapshot = (
            Snapshot.objects.select_related("project")
            .filter(pk=job.snapshot_id)
            .first()
        )
        if snapshot:
            values.update(
                project_id=snapshot.project_id,
                project_name=snapshot.project.name,
                snapshot_id=snapshot.pk,
                object_name=snapshot.name,
            )
            return values
        previous = OperationLog.objects.filter(
            job=job, project_id__isnull=False
        ).first()
        if previous:
            values.update(
                project_id=previous.project_id,
                project_name=previous.project_name,
                object_name=previous.object_name,
            )
            return values
    owner = None
    if job.scope.startswith(("imports_create:", "folder_imports_create:")):
        try:
            owner = Project.objects.filter(
                pk=uuid.UUID(job.scope.split(":", 1)[1])
            ).first()
        except ValueError:
            pass
    elif job.kind == "import" and job.previous_job_id:
        original = (
            ImportRequest.objects.select_related("project")
            .filter(job_id=job.previous_job_id)
            .first()
        )
        owner = original.project if original else None
    if owner:
        values.update(
            project_id=owner.pk, project_name=owner.name, object_name=owner.name
        )
    elif not values.get("project_id"):
        previous = OperationLog.objects.filter(
            job=job, project_id__isnull=False
        ).first()
        if previous:
            values.update(
                project_id=previous.project_id,
                project_name=previous.project_name,
                object_name=previous.object_name,
                snapshot_id=previous.snapshot_id,
            )
    return values


def attach_job(job: Job, created: bool) -> None:
    identifier = active_log.get()
    with transaction.atomic():
        log = (
            OperationLog.objects.select_for_update().filter(pk=identifier).first()
            if identifier
            else None
        )
        if log is not None and log.job_id is not None and log.job_id != job.pk:
            log = None
        if log is None:
            log = OperationLog.objects.create(
                operation=job.kind,
                idempotency_key=job.idempotency_key,
                job=job,
                **target_values(job),
            )
        log.job = job
        values = target_values(job)
        for name, value in values.items():
            if value not in (None, ""):
                setattr(log, name, value)
        log.result = "accepted" if created else "replayed"
        log.events = [*log.events, event(log.result, job_id=str(job.pk))]
        log.save()


def record_job_event(job: Job) -> None:
    result = {"queued": "accepted", "running": "running"}.get(job.status, job.status)
    with transaction.atomic():
        logs = OperationLog.objects.select_for_update().filter(job=job)
        for log in logs:
            if log.result != "replayed":
                log.result = result
            code = (
                str(job.error.get("code", ""))[:80]
                if isinstance(job.error, dict)
                else ""
            )
            log.error_code = code
            log.events = [*log.events, event(result, stage=job.stage, error_code=code)]
            values = target_values(job)
            for name, value in values.items():
                if value not in (None, ""):
                    setattr(log, name, value)
            log.save()


def finish_http(identifier: uuid.UUID, status: int, code: str = "") -> None:
    with transaction.atomic():
        log = OperationLog.objects.select_for_update().get(pk=identifier)
        if log.job_id:
            log.events = [*log.events, event("response", http_status=status)]
        else:
            log.result = "rejected" if status >= 400 else "succeeded"
            log.error_code = code[:80]
            log.events = [
                *log.events,
                event(log.result, http_status=status, error_code=log.error_code),
            ]
        log.save()


def reconcile_receiving() -> None:
    deadline = timezone.now() - timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS)
    with transaction.atomic():
        expired = OperationLog.objects.select_for_update().filter(
            Q(operation="import")
            | Q(operation="retry", source_kind__in=["zip", "folder"]),
            result="submitted",
            job__isnull=True,
            created_at__lte=deadline,
        )
        for log in expired:
            log.result, log.error_code = "failed", "RECEIVE_TIMEOUT"
            log.events = [*log.events, event("failed", error_code="RECEIVE_TIMEOUT")]
            log.save(update_fields=["result", "error_code", "events", "updated_at"])
