import hashlib
import uuid
from collections.abc import Callable
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from kombu.exceptions import OperationalError

from apps.jobs.audit import attach_job, reconcile_receiving, record_job_event
from apps.jobs.models import Job
from common.errors import ApiProblem, Conflict, error_body
from common.retirement import (
    RETIRED_JOB_KINDS,
    require_active_job_kind,
    retired_feature,
)
from config.celery import app

EMPTY_DIGEST = hashlib.sha256(b"{}").hexdigest()


def audited_creation[**P](
    function: Callable[P, tuple[Job, bool]],
) -> Callable[P, tuple[Job, bool]]:
    @wraps(function)
    def call(*args: P.args, **kwargs: P.kwargs) -> tuple[Job, bool]:
        with transaction.atomic():
            job, created = function(*args, **kwargs)
            attach_job(job, created)
            return job, created

    return call


def audit_current(job_id: str) -> None:
    record_job_event(Job.objects.get(pk=job_id))


def refuse_retired_job(job_id: str) -> bool:
    job = Job.objects.filter(pk=job_id).first()
    if job is None or job.kind not in RETIRED_JOB_KINDS:
        return False
    changed = Job.objects.filter(pk=job_id, status=Job.Status.QUEUED).update(
        status=Job.Status.FAILED,
        stage="retired",
        updated_at=timezone.now(),
        error=error_body(
            "FEATURE_RETIRED", "该功能已退役，任务未执行。", uuid.uuid4().hex
        ),
    )
    if changed:
        audit_current(job_id)
    return True


def require_retryable(previous: Job, key: uuid.UUID) -> None:
    require_active_job_kind(previous.kind)
    if previous.result_deleted_at is not None:
        raise ApiProblem(410, "RESOURCE_DELETED", "任务所属源码及结果已永久清理。")
    if previous.status != Job.Status.FAILED:
        raise ApiProblem(409, "JOB_NOT_RETRYABLE", "只能显式重试已失败的任务。")
    if key == previous.idempotency_key:
        raise Conflict
    if previous.kind not in {
        "system_check",
        "import",
        "analysis",
        "explanation",
        "lab",
        "snapshot_comparison",
        "source_scan",
        "delete",
    }:
        raise ApiProblem(409, "JOB_NOT_RETRYABLE", "该任务类型尚不支持重试。")


@audited_creation
def create_retry_job(previous: Job, key: uuid.UUID, digest: str) -> tuple[Job, bool]:
    require_retryable(previous, key)
    if digest != previous.request_digest:
        raise Conflict
    job, created = Job.objects.get_or_create(
        scope=f"jobs_retry:{previous.pk}",
        idempotency_key=key,
        defaults={
            "kind": previous.kind,
            "previous_job": previous,
            "snapshot_id": previous.snapshot_id
            if previous.kind
            in {"analysis", "snapshot_comparison", "source_scan", "delete"}
            else None,
            "parent_job": previous.parent_job,
            "source_kind": previous.source_kind,
            "request_digest": digest,
            "expires_at": timezone.now()
            + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
        },
    )
    if job.request_digest != digest:
        raise Conflict
    return job, created


def submit_check(
    key: uuid.UUID, *, previous: Job | None = None
) -> tuple[Job, bool, bool]:
    retired_feature("system_check")


def dispatch_job(job: Job, task_name: str) -> bool:
    require_active_job_kind(job.kind)
    try:
        # 提交事务退出后才投递；数据库记录是恢复与幂等的唯一依据。
        app.send_task(task_name, args=[str(job.pk)], task_id=str(job.pk), retry=False)
    except (OperationalError, OSError):
        Job.objects.filter(pk=job.pk, status=Job.Status.QUEUED).update(
            status=Job.Status.FAILED,
            stage="failed",
            updated_at=timezone.now(),
            error=error_body(
                "QUEUE_UNAVAILABLE",
                "队列投递未确认，任务记录已保留，请查询状态。",
                uuid.uuid4().hex,
            ),
        )
        audit_current(str(job.pk))
        return False
    return True


def execute_check(job_id: str) -> None:
    refuse_retired_job(job_id)


def complete_check(job_id: str, claim: uuid.UUID) -> bool:
    retired_feature("system_check")


def reconcile_expired() -> int:
    reconcile_receiving()
    count = 0
    for status, code, message in (
        (Job.Status.QUEUED, "QUEUE_TIMEOUT", "任务排队超时，请检查队列和 Worker。"),
        (Job.Status.RUNNING, "EXECUTION_TIMEOUT", "任务执行超时，结果未被接受。"),
    ):
        expired = list(
            Job.objects.filter(
                status=status, expires_at__lte=timezone.now()
            ).values_list("pk", flat=True)
        )
        count += Job.objects.filter(
            pk__in=expired, status=status, expires_at__lte=timezone.now()
        ).update(
            status=Job.Status.FAILED,
            stage="failed",
            updated_at=timezone.now(),
            error=error_body(code, message, uuid.uuid4().hex),
        )
        for identifier in expired:
            audit_current(str(identifier))
    return count


@audited_creation
def create_import_job(
    scope: str, key: uuid.UUID, digest: str, *, source_kind: str = "zip"
) -> tuple[Job, bool]:
    job, created = Job.objects.get_or_create(
        scope=scope,
        idempotency_key=key,
        defaults={
            "kind": "import",
            "source_kind": source_kind,
            "request_digest": digest,
            "expires_at": timezone.now()
            + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
        },
    )
    if job.request_digest != digest:
        raise Conflict
    return job, created


def dispatch_import(job: Job) -> bool:
    return dispatch_job(job, "projects.import")


def claim_import(job_id: str) -> uuid.UUID | None:
    claim = uuid.uuid4()
    now = timezone.now()
    acquired = Job.objects.filter(
        pk=job_id, kind="import", status=Job.Status.QUEUED, expires_at__gt=now
    ).update(
        status=Job.Status.RUNNING,
        stage="extracting",
        claim_id=claim,
        expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
        updated_at=now,
    )
    if acquired:
        audit_current(job_id)
    return claim if acquired else None


def complete_import(
    job_id: str, claim: uuid.UUID, publish: Callable[[], uuid.UUID]
) -> bool:
    with transaction.atomic():
        from apps.projects.models import ImportRequest
        from common.resource_state import lock_project

        record = ImportRequest.objects.filter(job_id=uuid.UUID(job_id)).first()
        if record is not None:
            lock_project(record.project_id)
        job = Job.objects.select_for_update().get(pk=job_id)
        if (
            job.status != Job.Status.RUNNING
            or job.claim_id != claim
            or job.expires_at <= timezone.now()
        ):
            return False
        job.stage = "publishing"
        job.save(update_fields=["stage", "updated_at"])
        snapshot_id = publish()
        if job.expires_at <= timezone.now():
            # 文件发布可能已完成；回滚数据库后由扫描器清理不可见目录。
            raise TimeoutError
        job.snapshot_id = snapshot_id
        job.result_url = f"/api/v1/snapshots/{snapshot_id}/"
        job.status = Job.Status.SUCCEEDED
        job.stage = "completed"
        job.save(
            update_fields=["snapshot_id", "result_url", "status", "stage", "updated_at"]
        )
        record_job_event(job)
    return True


def fail_import(
    job_id: str, claim: uuid.UUID, code: str, message: str, reason: str
) -> None:
    Job.objects.filter(pk=job_id, status=Job.Status.RUNNING, claim_id=claim).update(
        status=Job.Status.FAILED,
        stage="failed",
        updated_at=timezone.now(),
        error=error_body(code, message, uuid.uuid4().hex, {"reason": reason}),
    )
    audit_current(job_id)


@audited_creation
def create_analysis_job(
    snapshot_id: uuid.UUID,
    key: uuid.UUID,
    digest: str,
    *,
    parent: Job | None = None,
    source_kind: str = "",
) -> tuple[Job, bool]:
    job, created = Job.objects.get_or_create(
        scope=f"analyses_create:{snapshot_id}",
        idempotency_key=key,
        defaults={
            "kind": "analysis",
            "snapshot_id": snapshot_id,
            "parent_job": parent,
            "source_kind": source_kind,
            "request_digest": digest,
            "expires_at": timezone.now()
            + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
        },
    )
    if job.request_digest != digest:
        raise Conflict
    return job, created


def dispatch_analysis(job: Job) -> bool:
    return dispatch_job(job, "analysis.parse")


def claim_analysis(job_id: str) -> uuid.UUID | None:
    claim, now = uuid.uuid4(), timezone.now()
    acquired = Job.objects.filter(
        pk=job_id, kind="analysis", status=Job.Status.QUEUED, expires_at__gt=now
    ).update(
        status=Job.Status.RUNNING,
        stage="parsing",
        claim_id=claim,
        expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
        updated_at=now,
    )
    if acquired:
        audit_current(job_id)
    return claim if acquired else None


def complete_analysis(
    job_id: str, claim: uuid.UUID, publish: Callable[[], str]
) -> bool:
    return _complete_result(job_id, claim, publish)


@audited_creation
def create_source_scan_job(
    snapshot_id: uuid.UUID,
    key: uuid.UUID,
    digest: str,
    *,
    previous: Job | None = None,
    parent: Job | None = None,
    source_kind: str = "",
) -> tuple[Job, bool]:
    if previous is not None:
        require_retryable(previous, key)
    job, created = Job.objects.get_or_create(
        scope=f"jobs_retry:{previous.pk}"
        if previous
        else f"source_scans_create:{snapshot_id}",
        idempotency_key=key,
        defaults={
            "kind": "source_scan",
            "snapshot_id": snapshot_id,
            "previous_job": previous,
            "parent_job": parent or (previous.parent_job if previous else None),
            "source_kind": source_kind or (previous.source_kind if previous else ""),
            "request_digest": digest,
            "expires_at": timezone.now()
            + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
        },
    )
    if job.kind != "source_scan" or job.request_digest != digest:
        raise Conflict
    return job, created


def dispatch_source_scan(job: Job) -> bool:
    return dispatch_job(job, "analysis.source_scan")


def claim_source_scan(job_id: str) -> uuid.UUID | None:
    claim, now = uuid.uuid4(), timezone.now()
    acquired = Job.objects.filter(
        pk=job_id, kind="source_scan", status=Job.Status.QUEUED, expires_at__gt=now
    ).update(
        status=Job.Status.RUNNING,
        stage="source_scanning",
        claim_id=claim,
        expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
        updated_at=now,
    )
    if acquired:
        audit_current(job_id)
    return claim if acquired else None


def complete_source_scan(
    job_id: str, claim: uuid.UUID, publish: Callable[[], str]
) -> bool:
    return _complete_result(job_id, claim, publish)


def fail_source_scan(job_id: str, claim: uuid.UUID, code: str, reason: str) -> None:
    Job.objects.filter(
        pk=job_id, kind="source_scan", status=Job.Status.RUNNING, claim_id=claim
    ).update(
        status=Job.Status.FAILED,
        stage="failed",
        updated_at=timezone.now(),
        error=error_body(
            code, "源码扫描未发布有效结果。", uuid.uuid4().hex, {"reason": reason}
        ),
    )
    audit_current(job_id)


def _complete_result(job_id: str, claim: uuid.UUID, publish: Callable[[], str]) -> bool:
    with transaction.atomic():
        from common.resource_state import lock_snapshot

        initial = Job.objects.get(pk=job_id)
        if initial.status != Job.Status.RUNNING or initial.claim_id != claim:
            return False
        require_active_job_kind(initial.kind)
        snapshot_id = initial.snapshot_id
        if snapshot_id is not None:
            lock_snapshot(snapshot_id)
        job = Job.objects.select_for_update().get(pk=job_id)
        if (
            job.status != Job.Status.RUNNING
            or job.claim_id != claim
            or job.expires_at <= timezone.now()
        ):
            return False
        url = publish()
        if job.expires_at <= timezone.now():
            raise TimeoutError
        job.result_url, job.status, job.stage = url, Job.Status.SUCCEEDED, "completed"
        job.save(update_fields=["result_url", "status", "stage", "updated_at"])
        record_job_event(job)
    return True


def fail_analysis(job_id: str, claim: uuid.UUID, code: str, reason: str) -> None:
    Job.objects.filter(
        pk=job_id, kind="analysis", status=Job.Status.RUNNING, claim_id=claim
    ).update(
        status=Job.Status.FAILED,
        stage="failed",
        updated_at=timezone.now(),
        error=error_body(
            code,
            "静态分析失败，未发布新的分析结果。",
            uuid.uuid4().hex,
            {"reason": reason},
        ),
    )
    audit_current(job_id)


@audited_creation
def create_explanation_job(
    snapshot_id: uuid.UUID,
    scope: str,
    key: uuid.UUID,
    digest: str,
    previous: Job | None,
) -> tuple[Job, bool]:
    job, created = Job.objects.get_or_create(
        scope=scope,
        idempotency_key=key,
        defaults={
            "kind": "explanation",
            "snapshot_id": snapshot_id,
            "previous_job": previous,
            "request_digest": digest,
            "expires_at": timezone.now()
            + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
        },
    )
    if job.kind != "explanation" or job.request_digest != digest:
        raise Conflict
    return job, created


def claim_explanation(job_id: str) -> uuid.UUID | None:
    claim, now = uuid.uuid4(), timezone.now()
    acquired = Job.objects.filter(
        pk=job_id, kind="explanation", status=Job.Status.QUEUED, expires_at__gt=now
    ).update(
        status=Job.Status.RUNNING,
        stage="generating",
        claim_id=claim,
        expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
        updated_at=now,
    )
    if acquired:
        audit_current(job_id)
    return claim if acquired else None


def explanation_claim_valid(job_id: str, claim: uuid.UUID) -> bool:
    return Job.objects.filter(
        pk=job_id,
        kind="explanation",
        status=Job.Status.RUNNING,
        claim_id=claim,
        expires_at__gt=timezone.now(),
    ).exists()


def renew_explanation_claim(job_id: str, claim: uuid.UUID) -> bool:
    now = timezone.now()
    return bool(
        Job.objects.filter(
            pk=job_id,
            kind="explanation",
            status=Job.Status.RUNNING,
            claim_id=claim,
            expires_at__gt=now,
        ).update(
            expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
            updated_at=now,
        )
    )


def complete_explanation(
    job_id: str, claim: uuid.UUID, publish: Callable[[], str]
) -> bool:
    return _complete_result(job_id, claim, publish)


def fail_explanation(job_id: str, claim: uuid.UUID, code: str) -> None:
    Job.objects.filter(pk=job_id, status=Job.Status.RUNNING, claim_id=claim).update(
        status=Job.Status.FAILED,
        stage="failed",
        updated_at=timezone.now(),
        error=error_body(
            code,
            "讲解未生成有效结果。不会自动重发；供应商可能已处理请求，再次尝试可能计费。",
            uuid.uuid4().hex,
        ),
    )
    audit_current(job_id)


def create_lab_job(
    scope: str, key: uuid.UUID, digest: str, previous: Job | None
) -> tuple[Job, bool]:
    retired_feature("lab")


def claim_lab(job_id: str) -> uuid.UUID | None:
    refuse_retired_job(job_id)
    return None


def complete_lab(job_id: str, claim: uuid.UUID, publish: Callable[[], str]) -> bool:
    retired_feature("lab")


def fail_lab(job_id: str, claim: uuid.UUID, code: str) -> None:
    retired_feature("lab")


def create_comparison_job(
    project_id: uuid.UUID, target_id: uuid.UUID, key: uuid.UUID, digest: str
) -> tuple[Job, bool]:
    retired_feature("snapshot_comparison")


def claim_comparison(job_id: str) -> uuid.UUID | None:
    refuse_retired_job(job_id)
    return None


def complete_comparison(
    job_id: str, claim: uuid.UUID, publish: Callable[[], str]
) -> bool:
    retired_feature("snapshot_comparison")


def fail_comparison(job_id: str, claim: uuid.UUID, code: str, reason: str) -> None:
    retired_feature("snapshot_comparison")
