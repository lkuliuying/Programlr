"""只清理工作台拥有的副本，数据库清理与文件清理分阶段恢复。"""

import hashlib
import hmac
import json
import stat
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.jobs.audit import active_log, attach_job, deletion_record, record_job_event
from apps.jobs.models import DeletionRequest, Job, OperationLog
from apps.jobs.services import create_retry_job, dispatch_job, require_retryable
from apps.projects.exceptions import ImportRejected
from apps.projects.models import ImportRequest, Project, Snapshot, SourceFile
from apps.projects.storage import file_lock, remove_owned_directory, storage_root
from common.errors import ApiProblem, Conflict, error_body


def ids(queryset: Any) -> list[str]:
    return sorted(str(value) for value in queryset.values_list("pk", flat=True))


def storage_inventory(identifiers: list[str]) -> list[dict[str, Any]]:
    root = Path(settings.IMPORT_STORAGE_ROOT)
    if (
        not root.is_absolute()
        or root.is_symlink()
        or root.resolve() != root
        or (root.exists() and not root.is_dir())
    ):
        raise ApiProblem(503, "DELETION_STORAGE_FAILED", "内部副本目录无法安全核对。")
    states: list[dict[str, Any]] = []
    try:
        for identifier in identifiers:
            uuid.UUID(identifier)
            state: dict[str, Any] = {"storage_id": identifier}
            for category in ("staging", "snapshots"):
                parent = root / category
                directory = parent / identifier
                if parent.is_symlink() or directory.is_symlink():
                    raise ApiProblem(
                        503, "DELETION_STORAGE_FAILED", "内部副本目录无法安全核对。"
                    )
                if not directory.exists():
                    state[category] = None
                    continue
                if not directory.is_dir() or not parent.is_dir():
                    raise ApiProblem(
                        503, "DELETION_STORAGE_FAILED", "内部副本目录无法安全核对。"
                    )
                entries, pending = [], [directory]
                while pending:
                    item = pending.pop()
                    metadata = item.lstat()
                    entries.append(
                        (
                            item.relative_to(directory).as_posix(),
                            metadata.st_mode,
                            metadata.st_size,
                            metadata.st_mtime_ns,
                        )
                    )
                    if stat.S_ISDIR(metadata.st_mode):
                        pending.extend(item.iterdir())
                state[category] = hashlib.sha256(
                    json.dumps(sorted(entries), separators=(",", ":")).encode()
                ).hexdigest()
            states.append(state)
    except OSError:
        raise ApiProblem(
            503, "DELETION_STORAGE_FAILED", "内部副本目录无法完整核对。"
        ) from None
    return states


def target_object(
    target_type: str, target_id: uuid.UUID, *, locked: bool = False
) -> Project | Snapshot:
    if target_type == "project":
        values = (
            Project.objects.select_for_update() if locked else Project.objects.all()
        )
        return get_object_or_404(values, pk=target_id)
    initial = get_object_or_404(Snapshot, pk=target_id)
    if locked:
        get_object_or_404(Project.objects.select_for_update(), pk=initial.project_id)
    snapshot_values = (
        Snapshot.objects.select_for_update().select_related("project")
        if locked
        else Snapshot.objects.select_related("project")
    )
    return get_object_or_404(snapshot_values, pk=target_id)


def inventory(target_type: str, target: Project | Snapshot) -> dict[str, Any]:
    from apps.analysis.models import (
        Analysis,
        AnalysisRequest,
        SnapshotComparisonRequest,
        SourceScan,
        SourceScanRequest,
    )
    from apps.explanations.models import ContextPreview, Explanation, ExplanationRequest
    from apps.labs.models import LabRun, SystemLabRun
    from apps.learning.models import ExerciseAttempt

    snapshots = (
        Snapshot.objects.filter(project_id=target.pk)
        if target_type == "project"
        else Snapshot.objects.filter(pk=target.pk)
    )
    snapshot_ids = ids(snapshots)
    owner_id = target.pk if isinstance(target, Project) else target.project_id
    imports = ImportRequest.objects.filter(project_id=owner_id)
    if target_type == "snapshot":
        imports = imports.filter(storage_id=target.pk)
    analyses = Analysis.objects.filter(snapshot_id__in=snapshot_ids)
    scans = SourceScan.objects.filter(snapshot_id__in=snapshot_ids)
    previews = ContextPreview.objects.filter(snapshot_id__in=snapshot_ids)
    comparisons = SnapshotComparisonRequest.objects.filter(
        Q(base_snapshot_id__in=snapshot_ids) | Q(target_snapshot_id__in=snapshot_ids)
    )
    attempts = set(ids(ExerciseAttempt.objects.filter(snapshot_id__in=snapshot_ids)))
    while True:
        expanded = attempts | set(
            ids(
                ExerciseAttempt.objects.filter(
                    previous_attempt_id__in=[uuid.UUID(value) for value in attempts]
                )
            )
        )
        if expanded == attempts:
            break
        attempts = expanded
    lab_ids = set(
        LabRun.objects.filter(analysis__snapshot_id__in=snapshot_ids).values_list(
            "job_id", flat=True
        )
    )
    lab_ids.update(
        SystemLabRun.objects.filter(analysis__snapshot_id__in=snapshot_ids).values_list(
            "job_id", flat=True
        )
    )
    job_ids = set(
        Job.objects.filter(snapshot_id__in=snapshot_ids).values_list("pk", flat=True)
    )
    job_ids.update(imports.values_list("job_id", flat=True))
    job_ids.update(comparisons.values_list("job_id", flat=True))
    job_ids.update(lab_ids)
    job_ids.update(analyses.values_list("job_id", flat=True))
    job_ids.update(scans.values_list("job_id", flat=True))
    job_ids.update(
        AnalysisRequest.objects.filter(snapshot_id__in=snapshot_ids).values_list(
            "job_id", flat=True
        )
    )
    job_ids.update(
        SourceScanRequest.objects.filter(snapshot_id__in=snapshot_ids).values_list(
            "job_id", flat=True
        )
    )
    job_ids.update(
        ExplanationRequest.objects.filter(consent__preview_id__in=previews).values_list(
            "job_id", flat=True
        )
    )
    job_ids.update(
        Explanation.objects.filter(preview_id__in=previews).values_list(
            "job_id", flat=True
        )
    )
    counts = {
        "snapshots": len(snapshot_ids),
        "files": SourceFile.objects.filter(snapshot_id__in=snapshot_ids).count(),
        "analyses": analyses.count(),
        "source_scans": scans.count(),
        "explanations": Explanation.objects.filter(preview_id__in=previews).count(),
        "attempts": len(attempts),
        "lab_runs": len(lab_ids),
        "comparisons": comparisons.count(),
    }
    storage_ids = sorted(
        set(snapshot_ids)
        | {str(value) for value in imports.values_list("storage_id", flat=True)}
    )
    return {
        "snapshot_ids": snapshot_ids,
        "storage_ids": storage_ids,
        "storage_state": storage_inventory(storage_ids),
        "job_ids": sorted(str(value) for value in job_ids),
        "comparison_ids": ids(comparisons),
        "analysis_ids": ids(analyses),
        "scan_ids": ids(scans),
        "preview_ids": ids(previews),
        "attempt_ids": sorted(attempts),
        "manifests": sorted(
            (str(identifier), digest)
            for identifier, digest in snapshots.values_list("pk", "manifest_digest")
        ),
        "scope": counts,
    }


def preview(target_type: str, target: Project | Snapshot) -> dict[str, Any]:
    plan = inventory(target_type, target)
    owner_id = target.pk if isinstance(target, Project) else target.project_id
    busy = list(
        Job.objects.filter(
            pk__in=plan["job_ids"], status__in=[Job.Status.QUEUED, Job.Status.RUNNING]
        )
    )
    receiving_logs = OperationLog.objects.filter(
        Q(operation="import") | Q(operation="retry", source_kind__in=["zip", "folder"]),
        project_id=owner_id,
        result="submitted",
        job__isnull=True,
        created_at__gte=timezone.now()
        - timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
    )
    current_log = active_log.get()
    if current_log is not None:
        receiving_logs = receiving_logs.exclude(pk=current_log)
    receiving = receiving_logs.exists()
    deleting = target.deletion_request_id is not None
    if isinstance(target, Project):
        deleting = (
            deleting
            or Snapshot.objects.filter(
                project=target, deletion_request_id__isnull=False
            ).exists()
        )
    if isinstance(target, Snapshot):
        deleting = deleting or target.project.deletion_request_id is not None
    basis = {
        "target_type": target_type,
        "target_id": str(target.pk),
        "name": target.name,
        "inventory": plan,
        "busy": sorted((str(job.pk), job.status) for job in busy),
        "receiving": receiving,
    }
    digest = hashlib.sha256(
        json.dumps(
            basis, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return {
        "target_type": target_type,
        "target_id": str(target.pk),
        "project_id": str(owner_id),
        "object_name": target.name,
        "scope": plan["scope"],
        "confirmation_digest": digest,
        "can_delete": not (busy or receiving or deleting),
        "busy_jobs": busy,
        "receiving": receiving,
    }


def submit_deletion(
    target_type: str, target_id: uuid.UUID, key: uuid.UUID, confirmation_digest: str
) -> tuple[Job, bool, bool]:
    scope = f"deletions_create:{target_type}:{target_id}"
    request_digest = hashlib.sha256(confirmation_digest.encode()).hexdigest()

    def existing_job() -> Job | None:
        old = Job.objects.filter(scope=scope, idempotency_key=key).first()
        if old is not None:
            if old.request_digest != request_digest:
                raise Conflict
            attach_job(old, False)
        return old

    with transaction.atomic():
        old = existing_job()
        if old:
            return old, False, True
        try:
            target = target_object(target_type, target_id, locked=True)
        except Http404:
            old = existing_job()
            if old is not None:
                return old, False, True
            raise
        old = existing_job()
        if old:
            return old, False, True
        if target.deletion_request_id is not None or (
            isinstance(target, Snapshot)
            and target.project.deletion_request_id is not None
        ):
            raise ApiProblem(
                409, "DELETION_IN_PROGRESS", "原永久清理尚未结束，请查询或继续原任务。"
            )
        current = preview(target_type, target)
        if not current["can_delete"]:
            raise ApiProblem(
                409, "RESOURCE_BUSY", "有正在接收或执行的操作，不能永久清理。"
            )
        if not hmac.compare_digest(current["confirmation_digest"], confirmation_digest):
            raise ApiProblem(
                409, "DELETION_PREVIEW_STALE", "删除范围已变化，请重新查看并确认。"
            )
        owner_id = target.pk if isinstance(target, Project) else target.project_id
        owner_name = target.name if isinstance(target, Project) else target.project.name
        job = Job.objects.create(
            kind="delete",
            scope=scope,
            idempotency_key=key,
            snapshot_id=target.pk if isinstance(target, Snapshot) else None,
            request_digest=request_digest,
            expires_at=timezone.now()
            + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
        )
        record = DeletionRequest.objects.create(
            initial_job=job,
            current_job=job,
            target_type=target_type,
            target_id=target.pk,
            project_id=owner_id,
            project_name=owner_name,
            object_name=target.name,
            inventory=inventory(target_type, target),
        )
        target.deletion_request_id = record.pk
        target.save(update_fields=["deletion_request_id"])
        if target_type == "project":
            Snapshot.objects.filter(project_id=target.pk).update(
                deletion_request_id=record.pk
            )
        attach_job(job, True)
        log_id = active_log.get()
        if log_id:
            OperationLog.objects.filter(pk=log_id).update(
                project_id=owner_id, project_name=owner_name, object_name=target.name
            )
    published = dispatch_job(job, "jobs.delete")
    job.refresh_from_db()
    return job, True, published


def retry_deletion(previous: Job, key: uuid.UUID) -> tuple[Job, bool, bool]:
    require_retryable(previous, key)
    with transaction.atomic():
        replay = Job.objects.filter(
            scope=f"jobs_retry:{previous.pk}", idempotency_key=key
        ).first()
        if replay:
            attach_job(replay, False)
            return replay, False, True
        original = deletion_record(previous)
        if original is None:
            raise ApiProblem(404, "NOT_FOUND", "永久清理记录不存在。")
        if original.completed_at is not None:
            raise ApiProblem(409, "DELETION_COMPLETE", "永久清理已经完成。")
        target_object(original.target_type, original.target_id, locked=True)
        record = DeletionRequest.objects.select_for_update().get(pk=original.pk)
        replay = Job.objects.filter(
            scope=f"jobs_retry:{previous.pk}", idempotency_key=key
        ).first()
        if replay:
            attach_job(replay, False)
            return replay, False, True
        if record.completed_at is not None:
            raise ApiProblem(409, "DELETION_COMPLETE", "永久清理已经完成。")
        if record.current_job_id != previous.pk:
            raise ApiProblem(
                409, "DELETION_IN_PROGRESS", "请查询当前清理尝试，不重复创建任务。"
            )
        job, created = create_retry_job(previous, key, previous.request_digest)
        if created:
            record.current_job = job
            record.save(update_fields=["current_job"])
    published = dispatch_job(job, "jobs.delete") if created else True
    job.refresh_from_db()
    return job, created, published


def require_claim(record: DeletionRequest, job_id: str, claim: uuid.UUID) -> Job:
    job = Job.objects.select_for_update().get(pk=job_id)
    if (
        record.current_job_id != job.pk
        or job.status != Job.Status.RUNNING
        or job.claim_id != claim
        or job.expires_at <= timezone.now()
    ):
        raise TimeoutError("清理执行资格已失效。")
    return job


def renew_deletion(job_id: str, claim: uuid.UUID) -> None:
    with transaction.atomic():
        record = DeletionRequest.objects.select_for_update().get(
            current_job_id=uuid.UUID(job_id)
        )
        job = require_claim(record, job_id, claim)
        job.expires_at = timezone.now() + timedelta(
            seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS
        )
        job.save(update_fields=["expires_at", "updated_at"])


def delete_database(
    plan: dict[str, Any], target_type: str, target_id: uuid.UUID
) -> None:
    from apps.analysis.models import (
        Analysis,
        AnalysisGraph,
        AnalysisRequest,
        RelationReview,
        RelationReviewState,
        SnapshotComparison,
        SnapshotComparisonRequest,
        SnapshotPreparation,
        SourceScan,
        SourceScanRequest,
    )
    from apps.explanations.models import (
        ContextConsent,
        ContextPreview,
        Explanation,
        ExplanationRequest,
    )
    from apps.labs.models import LabRun, SystemLabRun
    from apps.learning.models import AttemptReview, ExerciseAttempt

    previews = plan["preview_ids"]
    Explanation.objects.filter(preview_id__in=previews).delete()
    ExplanationRequest.objects.filter(consent__preview_id__in=previews).delete()
    ContextConsent.objects.filter(preview_id__in=previews).delete()
    ContextPreview.objects.filter(pk__in=previews).delete()
    attempts = set(plan["attempt_ids"])
    AttemptReview.objects.filter(attempt_id__in=attempts).delete()
    while attempts:
        referenced = {
            str(value)
            for value in ExerciseAttempt.objects.filter(
                previous_attempt_id__in=attempts
            ).values_list("previous_attempt_id", flat=True)
        }
        leaves = attempts - referenced
        if not leaves:
            raise ApiProblem(
                409, "DELETION_DEPENDENCY_BLOCKED", "历史作答依赖无法安全清理。"
            )
        ExerciseAttempt.objects.filter(pk__in=leaves).delete()
        attempts -= leaves
    LabRun.objects.filter(analysis_id__in=plan["analysis_ids"]).delete()
    SystemLabRun.objects.filter(analysis_id__in=plan["analysis_ids"]).delete()
    SnapshotComparison.objects.filter(request_id__in=plan["comparison_ids"]).delete()
    SnapshotComparisonRequest.objects.filter(pk__in=plan["comparison_ids"]).delete()
    RelationReview.objects.filter(analysis_id__in=plan["analysis_ids"]).delete()
    RelationReviewState.objects.filter(analysis_id__in=plan["analysis_ids"]).delete()
    AnalysisGraph.objects.filter(analysis_id__in=plan["analysis_ids"]).delete()
    SnapshotPreparation.objects.filter(snapshot_id__in=plan["snapshot_ids"]).delete()
    AnalysisRequest.objects.filter(snapshot_id__in=plan["snapshot_ids"]).delete()
    Analysis.objects.filter(pk__in=plan["analysis_ids"]).delete()
    SourceScan.objects.filter(pk__in=plan["scan_ids"]).delete()
    SourceScanRequest.objects.filter(snapshot_id__in=plan["snapshot_ids"]).delete()
    SourceFile.objects.filter(snapshot_id__in=plan["snapshot_ids"]).delete()
    ImportRequest.objects.filter(storage_id__in=plan["storage_ids"]).delete()
    Snapshot.objects.filter(pk__in=plan["snapshot_ids"]).delete()
    if target_type == "project":
        Project.objects.filter(pk=target_id).delete()


def execute_deletion(job_id: str) -> None:
    claim, now = uuid.uuid4(), timezone.now()
    acquired = Job.objects.filter(
        pk=job_id, kind="delete", status=Job.Status.QUEUED, expires_at__gt=now
    ).update(
        status=Job.Status.RUNNING,
        stage="cleaning_files",
        claim_id=claim,
        expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
        updated_at=now,
    )
    if not acquired:
        return
    record = DeletionRequest.objects.get(current_job_id=uuid.UUID(job_id))
    record_job_event(Job.objects.get(pk=job_id))
    try:
        if record.plan_version != 1:
            raise ApiProblem(
                409, "DELETION_PLAN_UNSUPPORTED", "清理清单版本不可识别，未继续执行。"
            )
        root = storage_root()
        with file_lock(root / ".guard"):
            for identifier in record.inventory["storage_ids"]:
                renew_deletion(job_id, claim)
                parsed = uuid.UUID(identifier)
                stage = root / "staging" / str(parsed)
                if stage.exists():
                    with file_lock(stage / ".lock", blocking=False) as locked:
                        if not locked:
                            raise ApiProblem(
                                409,
                                "RESOURCE_BUSY",
                                "导入暂存仍被占用，请稍后继续清理。",
                            )
                        remove_owned_directory(stage, root / "staging")
                remove_owned_directory(
                    root / "snapshots" / str(parsed), root / "snapshots"
                )
        with transaction.atomic():
            current = DeletionRequest.objects.select_for_update().get(pk=record.pk)
            job = require_claim(current, job_id, claim)
            current.phase = "files_cleaned"
            current.save(update_fields=["phase"])
        with transaction.atomic():
            target_object(record.target_type, record.target_id, locked=True)
            current = DeletionRequest.objects.select_for_update().get(pk=record.pk)
            job = require_claim(current, job_id, claim)
            delete_database(current.inventory, current.target_type, current.target_id)
            deleted_at = timezone.now()
            Job.objects.filter(pk__in=current.inventory["job_ids"]).update(
                result_deleted_at=deleted_at, result_url=None
            )
            for summary in Job.objects.filter(
                pk__in=current.inventory["job_ids"]
            ).exclude(error=None):
                code = (
                    str(summary.error.get("code", ""))[:80]
                    if isinstance(summary.error, dict)
                    else ""
                )
                summary.error = error_body(
                    code, "所属源码与结果已永久清理，仅保留任务摘要。", ""
                )
                summary.save(update_fields=["error"])
            job.result_url = None
            job.status, job.stage = Job.Status.SUCCEEDED, "completed"
            job.save(update_fields=["result_url", "status", "stage", "updated_at"])
            current.phase, current.completed_at = "completed", deleted_at
            current.inventory = {"scope": current.inventory["scope"]}
            current.save(update_fields=["phase", "completed_at", "inventory"])
            record_job_event(job)
    except DatabaseError:
        # 数据库恢复后由期限核对终结；清单和隔离标记仍是恢复依据。
        raise RuntimeError("永久清理需等待数据库恢复和期限核对。") from None
    except (OSError, ValueError, TimeoutError, ApiProblem, ImportRejected) as exc:
        code = (
            exc.machine_code
            if isinstance(exc, ApiProblem)
            else "EXECUTION_TIMEOUT"
            if isinstance(exc, TimeoutError)
            else "DELETION_STORAGE_FAILED"
        )
        Job.objects.filter(pk=job_id, status=Job.Status.RUNNING, claim_id=claim).update(
            status=Job.Status.FAILED,
            stage="cleanup_pending",
            updated_at=timezone.now(),
            error=error_body(
                code,
                "永久清理未完成，目标保持隔离；可继续原清理任务。",
                uuid.uuid4().hex,
            ),
        )
        record_job_event(Job.objects.get(pk=job_id))
