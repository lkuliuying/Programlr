"""系统实验的提交、检查点和原子结束，执行资格继续由 jobs 管理。"""

import hashlib
import json
import logging
import uuid
from typing import Any

from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.analysis.models import Analysis
from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.labs.models import SystemLabRun
from apps.labs.system_adapter import PROGRAM, SystemLabFailure, execute_case
from apps.labs.system_definition import system_definition
from common.errors import ApiProblem, Conflict

logger = logging.getLogger(__name__)


def submit_system_run(
    lab_id: str, key: uuid.UUID, values: dict[str, Any], *, previous: Job | None = None
) -> tuple[Job, bool, bool]:
    digest = hashlib.sha256(
        json.dumps(
            {"lab_id": lab_id, **values},
            default=str,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    scope = f"jobs_retry:{previous.pk}" if previous else f"system_labs_create:{lab_id}"
    with transaction.atomic():
        existing = Job.objects.filter(scope=scope, idempotency_key=key).first()
        if existing is not None:
            if existing.request_digest != digest:
                raise Conflict
            return existing, False, True
        analysis = get_object_or_404(Analysis, pk=values["analysis_id"])
        definition = system_definition(lab_id, analysis, values["endpoint_index"])
        if (
            values["snapshot_id"] != analysis.snapshot_id
            or not definition["applicable"]
        ):
            raise ApiProblem(409, "LAB_NOT_APPLICABLE", "快照或接口不匹配内置示例。")
        if values["lab_version"] != definition["version"]:
            raise ApiProblem(
                409, "LAB_VERSION_MISMATCH", "固定实验版本已变化，请重新读取。"
            )
        if previous:
            jobs.require_retryable(previous, key)
            if digest != previous.request_digest:
                raise Conflict
        job, created = jobs.create_lab_job(scope, key, digest, previous)
        if created:
            SystemLabRun.objects.create(
                job=job,
                analysis=analysis,
                endpoint_index=values["endpoint_index"],
                lab_id=lab_id,
                definition=definition,
                predictions=values["predictions"],
            )
    published = jobs.dispatch_job(job, "labs.system_run") if created else True
    job.refresh_from_db()
    return job, created, published


def retry_system_run(previous: Job, key: uuid.UUID) -> tuple[Job, bool, bool]:
    run = get_object_or_404(
        SystemLabRun.objects.select_related("analysis"), job=previous
    )
    return submit_system_run(
        run.lab_id,
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


def checkpoint(run: SystemLabRun, claim: uuid.UUID) -> None:
    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=run.job_id)
        if (
            job.status != Job.Status.RUNNING
            or job.claim_id != claim
            or job.expires_at <= timezone.now()
        ):
            raise SystemLabFailure("EXECUTION_TIMEOUT")
        run.save(update_fields=["observations", "cleanup"])


def execute_system_run(job_id: str) -> None:
    claim = jobs.claim_lab(job_id)
    if claim is None:
        return
    run = SystemLabRun.objects.get(job_id=job_id)
    failure: str | None = None
    try:
        if (
            hashlib.sha256(PROGRAM.read_bytes()).hexdigest()
            != run.definition["program_digest"]
        ):
            raise SystemLabFailure("SYSTEM_LAB_VERSION_MISMATCH")
        for case in ("first", "second"):
            checkpoint(run, claim)
            observation = execute_case(run.lab_id, case)
            observation["observed_at"] = (
                timezone.now().isoformat().replace("+00:00", "Z")
            )
            run.observations.append(observation)
            if observation["reaped"] is False:
                failure = "SYSTEM_LAB_CLEANUP_FAILED"
            elif observation["status"] != "observed":
                failure = failure or observation["error_code"]
            elif (
                run.lab_id == "container-network"
                and case == "second"
                and not observation["connected"]
            ):
                failure = failure or "SYSTEM_LAB_UNAVAILABLE"
            checkpoint(run, claim)
    except SystemLabFailure as exc:
        failure = exc.code
    except Exception as exc:
        logger.error("job_id=%s exception_type=%s", job_id, type(exc).__name__)
        failure = "SYSTEM_LAB_FAILED"
    finally:
        unconfirmed = any(item["reaped"] is False for item in run.observations)
        run.cleanup = {
            "status": "unconfirmed" if unconfirmed else "completed",
            "error_code": "SYSTEM_LAB_CLEANUP_FAILED" if unconfirmed else None,
        }
        try:
            checkpoint(run, claim)
        except (SystemLabFailure, DatabaseError):
            failure = failure or "EXECUTION_TIMEOUT"
    if failure:
        jobs.fail_lab(job_id, claim, failure)
    else:
        jobs.complete_lab(job_id, claim, lambda: f"/api/v1/system-lab-runs/{run.pk}/")
