import hashlib
import logging
import uuid
from collections.abc import Callable
from datetime import timedelta

from django.conf import settings
from django.db import DatabaseError, transaction
from django.utils import timezone
from kombu.exceptions import OperationalError

from apps.jobs.models import Job, SystemCheck
from common.errors import ApiProblem, Conflict, error_body
from config.celery import app

logger = logging.getLogger(__name__)
EMPTY_DIGEST = hashlib.sha256(b"{}").hexdigest()


def require_retryable(previous: Job, key: uuid.UUID) -> None:
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
    }:
        raise ApiProblem(409, "JOB_NOT_RETRYABLE", "该任务类型尚不支持重试。")


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
            if previous.kind in {"analysis", "snapshot_comparison"}
            else None,
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
    with transaction.atomic():
        if previous is not None:
            job, created = create_retry_job(previous, key, EMPTY_DIGEST)
        else:
            job, created = Job.objects.get_or_create(
                scope="system_checks_create",
                idempotency_key=key,
                defaults={
                    "request_digest": EMPTY_DIGEST,
                    "expires_at": timezone.now()
                    + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
                },
            )
        if job.kind != "system_check" or job.request_digest != EMPTY_DIGEST:
            raise Conflict
    published = dispatch_job(job, "jobs.system_check") if created else True
    job.refresh_from_db()
    return job, created, published


def dispatch_job(job: Job, task_name: str) -> bool:
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
        return False
    return True


def execute_check(job_id: str) -> None:
    now = timezone.now()
    claim = uuid.uuid4()
    try:
        acquired = Job.objects.filter(
            pk=job_id, kind="system_check", status=Job.Status.QUEUED, expires_at__gt=now
        ).update(
            status=Job.Status.RUNNING,
            stage="checking",
            claim_id=claim,
            expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
            updated_at=now,
        )
    except DatabaseError:
        raise RuntimeError("检查领取需等待期限核对。") from None
    if not acquired:
        return
    try:
        complete_check(job_id, claim)
    except Exception as exc:
        # 任务边界保留失败，日志仅记录类型，不暴露数据库或队列异常中的凭据。
        logger.error("job_id=%s exception_type=%s", job_id, type(exc).__name__)
        code = "EXECUTION_TIMEOUT" if isinstance(exc, TimeoutError) else "CHECK_FAILED"
        try:
            Job.objects.filter(
                pk=job_id, status=Job.Status.RUNNING, claim_id=claim
            ).update(
                status=Job.Status.FAILED,
                stage="failed",
                updated_at=timezone.now(),
                error=error_body(code, "基础链路检查失败。", uuid.uuid4().hex),
            )
        except DatabaseError:
            raise RuntimeError("检查状态需等待期限核对。") from None


def complete_check(job_id: str, claim: uuid.UUID) -> bool:
    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=job_id)
        if (
            job.status != Job.Status.RUNNING
            or job.claim_id != claim
            or job.expires_at <= timezone.now()
        ):
            return False
        SystemCheck.objects.create(job=job)
        if job.expires_at <= timezone.now():
            raise TimeoutError
        job.status = Job.Status.SUCCEEDED
        job.stage = "completed"
        job.save(update_fields=["status", "stage", "updated_at"])
    return True


def reconcile_expired() -> int:
    count = 0
    for status, code, message in (
        (Job.Status.QUEUED, "QUEUE_TIMEOUT", "任务排队超时，请检查队列和 Worker。"),
        (Job.Status.RUNNING, "EXECUTION_TIMEOUT", "任务执行超时，结果未被接受。"),
    ):
        count += Job.objects.filter(
            status=status, expires_at__lte=timezone.now()
        ).update(
            status=Job.Status.FAILED,
            stage="failed",
            updated_at=timezone.now(),
            error=error_body(code, message, uuid.uuid4().hex),
        )
    return count


def create_import_job(scope: str, key: uuid.UUID, digest: str) -> tuple[Job, bool]:
    job, created = Job.objects.get_or_create(
        scope=scope,
        idempotency_key=key,
        defaults={
            "kind": "import",
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
    return claim if acquired else None


def complete_import(
    job_id: str, claim: uuid.UUID, publish: Callable[[], uuid.UUID]
) -> bool:
    with transaction.atomic():
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


def create_analysis_job(
    snapshot_id: uuid.UUID, key: uuid.UUID, digest: str
) -> tuple[Job, bool]:
    job, created = Job.objects.get_or_create(
        scope=f"analyses_create:{snapshot_id}",
        idempotency_key=key,
        defaults={
            "kind": "analysis",
            "snapshot_id": snapshot_id,
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
    return claim if acquired else None


def complete_analysis(
    job_id: str, claim: uuid.UUID, publish: Callable[[], str]
) -> bool:
    return _complete_result(job_id, claim, publish)


def _complete_result(job_id: str, claim: uuid.UUID, publish: Callable[[], str]) -> bool:
    with transaction.atomic():
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


def create_lab_job(
    scope: str, key: uuid.UUID, digest: str, previous: Job | None
) -> tuple[Job, bool]:
    job, created = Job.objects.get_or_create(
        scope=scope,
        idempotency_key=key,
        defaults={
            "kind": "lab",
            "previous_job": previous,
            "request_digest": digest,
            "expires_at": timezone.now()
            + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
        },
    )
    if job.request_digest != digest or job.kind != "lab":
        raise Conflict
    return job, created


def claim_lab(job_id: str) -> uuid.UUID | None:
    claim, now = uuid.uuid4(), timezone.now()
    acquired = Job.objects.filter(
        pk=job_id, kind="lab", status=Job.Status.QUEUED, expires_at__gt=now
    ).update(
        status=Job.Status.RUNNING,
        stage="experimenting",
        claim_id=claim,
        expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
        updated_at=now,
    )
    return claim if acquired else None


def complete_lab(job_id: str, claim: uuid.UUID, publish: Callable[[], str]) -> bool:
    return _complete_result(job_id, claim, publish)


def fail_lab(job_id: str, claim: uuid.UUID, code: str) -> None:
    Job.objects.filter(
        pk=job_id, kind="lab", status=Job.Status.RUNNING, claim_id=claim
    ).update(
        status=Job.Status.FAILED,
        stage="failed",
        updated_at=timezone.now(),
        error=error_body(
            code, "实验未完整完成，请查看已知观测与清理状态。", uuid.uuid4().hex
        ),
    )


def create_comparison_job(
    project_id: uuid.UUID, target_id: uuid.UUID, key: uuid.UUID, digest: str
) -> tuple[Job, bool]:
    job, created = Job.objects.get_or_create(
        scope=f"snapshot_comparisons_create:{project_id}",
        idempotency_key=key,
        defaults={
            "kind": "snapshot_comparison",
            "snapshot_id": target_id,
            "request_digest": digest,
            "expires_at": timezone.now()
            + timedelta(seconds=settings.JOB_QUEUE_TIMEOUT_SECONDS),
        },
    )
    if job.request_digest != digest or job.kind != "snapshot_comparison":
        raise Conflict
    return job, created


def claim_comparison(job_id: str) -> uuid.UUID | None:
    claim, now = uuid.uuid4(), timezone.now()
    acquired = Job.objects.filter(
        pk=job_id,
        kind="snapshot_comparison",
        status=Job.Status.QUEUED,
        expires_at__gt=now,
    ).update(
        status=Job.Status.RUNNING,
        stage="comparing",
        claim_id=claim,
        expires_at=now + timedelta(seconds=settings.JOB_EXECUTION_TIMEOUT_SECONDS),
        updated_at=now,
    )
    return claim if acquired else None


def complete_comparison(
    job_id: str, claim: uuid.UUID, publish: Callable[[], str]
) -> bool:
    return _complete_result(job_id, claim, publish)


def fail_comparison(job_id: str, claim: uuid.UUID, code: str, reason: str) -> None:
    Job.objects.filter(
        pk=job_id, kind="snapshot_comparison", status=Job.Status.RUNNING, claim_id=claim
    ).update(
        status=Job.Status.FAILED,
        stage="failed",
        updated_at=timezone.now(),
        error=error_body(
            code, "快照对比失败，未发布新的结果。", uuid.uuid4().hex, {"reason": reason}
        ),
    )
