import hashlib
import json
import logging
import time
import uuid
from typing import Any

from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.analysis.models import Analysis
from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.labs import adapter
from apps.labs.definition import definition
from apps.labs.models import LabRun
from common.errors import ApiProblem, Conflict

logger = logging.getLogger(__name__)


def submit_run(
    key: uuid.UUID, values: dict[str, Any], *, previous: Job | None = None
) -> tuple[Job, bool, bool]:
    digest = hashlib.sha256(
        json.dumps(values, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    scope = (
        f"jobs_retry:{previous.pk}" if previous else "labs_create:request-validation"
    )
    with transaction.atomic():
        existing = Job.objects.filter(scope=scope, idempotency_key=key).first()
        if existing is not None:
            if existing.request_digest != digest:
                raise Conflict
            return existing, False, True
        analysis = get_object_or_404(Analysis, pk=values["analysis_id"])
        lab = definition(analysis, values["endpoint_index"])
        if values["snapshot_id"] != analysis.snapshot_id or not lab["applicable"]:
            raise ApiProblem(409, "LAB_NOT_APPLICABLE", "快照或接口不匹配内置示例。")
        if values["lab_version"] != lab["version"]:
            raise ApiProblem(
                409, "LAB_VERSION_MISMATCH", "实验版本已变化，请重新读取。"
            )
        if previous:
            jobs.require_retryable(previous, key)
            if digest != previous.request_digest:
                raise Conflict
        job, created = jobs.create_lab_job(scope, key, digest, previous)
        if created:
            LabRun.objects.create(
                job=job,
                analysis=analysis,
                endpoint_index=values["endpoint_index"],
                definition=lab,
                predictions=values["predictions"],
            )
    published = jobs.dispatch_job(job, "labs.run") if created else True
    job.refresh_from_db()
    return job, created, published


def retry_run(previous: Job, key: uuid.UUID) -> tuple[Job, bool, bool]:
    run = get_object_or_404(LabRun.objects.select_related("analysis"), job=previous)
    return submit_run(
        key,
        {
            "analysis_id": run.analysis_id,
            "snapshot_id": run.analysis.snapshot_id,
            "endpoint_index": run.endpoint_index,
            "lab_version": run.definition["version"],
            "predictions": run.predictions,
        },
        previous=previous,
    )


def checkpoint(run: LabRun, claim: uuid.UUID) -> None:
    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=run.job_id)
        if (
            job.status != Job.Status.RUNNING
            or job.claim_id != claim
            or job.expires_at <= timezone.now()
        ):
            raise adapter.LabFailure("EXECUTION_TIMEOUT")
        run.save(update_fields=["observations", "cleanup"])


def execute_run(job_id: str) -> None:
    claim = jobs.claim_lab(job_id)
    if claim is None:
        return
    run = LabRun.objects.get(job_id=job_id)
    failure: str | None = None
    try:
        initial = adapter.observe(run.id, "open")
        if initial["closed"] or initial["record_count"] != 0:
            raise adapter.LabFailure("LAB_INVALID_RESPONSE")
        for case in run.definition["cases"]:
            checkpoint(run, claim)
            before = adapter.observe(run.id, "observe")
            started = time.monotonic()
            response = adapter.exchange(run.id, case["id"])
            item = {
                "case_id": case["id"],
                "input": case["input"],
                "request_path": f"/internal/labs/runs/{run.id}/cases/{case['id']}/",
                "response": response,
                "before_count": before["record_count"],
                "after_count": None,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "observed_at": timezone.now().isoformat(),
            }
            run.observations.append(item)
            checkpoint(run, claim)
            adapter.validate_case(response, case["id"])
            after = adapter.observe(run.id, "observe")
            item["after_count"] = after["record_count"]
            checkpoint(run, claim)
            if after["closed"] or after["record_count"] - before["record_count"] != (
                1 if case["id"] == "normal" else 0
            ):
                raise adapter.LabFailure("LAB_OBSERVATION_MISMATCH")
    except adapter.LabFailure as exc:
        failure = exc.code
    except Exception as exc:
        logger.error("job_id=%s exception_type=%s", job_id, type(exc).__name__)
        failure = "LAB_FAILED"
    finally:
        try:
            run.cleanup = {
                "status": "completed",
                "observation": adapter.observe(run.id, "close"),
                "error_code": None,
            }
        except adapter.LabFailure as exc:
            run.cleanup = {
                "status": "unconfirmed",
                "observation": None,
                "error_code": exc.code,
            }
            failure = failure or "LAB_CLEANUP_FAILED"
        try:
            checkpoint(run, claim)
        except (adapter.LabFailure, DatabaseError):
            # 失效执行不能覆盖历史；独立示例核对进程仍会关闭过期运行。
            failure = failure or "EXECUTION_TIMEOUT"
    if failure:
        jobs.fail_lab(job_id, claim, failure)
    else:
        jobs.complete_lab(job_id, claim, lambda: f"/api/v1/lab-runs/{run.pk}/")
