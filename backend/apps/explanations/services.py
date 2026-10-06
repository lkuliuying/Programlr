import logging
import uuid
from typing import Any

from django.conf import settings
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404

from apps.analysis.models import Analysis
from apps.explanations.adapter import ModelFailure, complete
from apps.explanations.configuration import digest
from apps.explanations.context import build_payload, check_preview
from apps.explanations.models import (
    ContextConsent,
    ContextPreview,
    Explanation,
    ExplanationRequest,
)
from apps.explanations.validation import validate_content
from apps.jobs import services as jobs
from apps.jobs.audit import attach_job
from apps.jobs.models import Job
from common.errors import ApiProblem, Conflict
from common.resource_state import lock_snapshot, require_snapshot_available

logger = logging.getLogger(__name__)


@transaction.atomic
def create_preview(
    key: uuid.UUID,
    analysis_id: uuid.UUID,
    endpoint_index: int,
    node_ids: list[str] | None,
    excluded_snippets: list[str] | None = None,
) -> tuple[ContextPreview, bool]:
    analysis = get_object_or_404(Analysis, pk=analysis_id)
    lock_snapshot(analysis.snapshot_id)
    request_digest = digest(
        {
            "analysis_id": str(analysis_id),
            "endpoint_index": endpoint_index,
            "node_ids": sorted(set(node_ids)) if node_ids is not None else None,
            "excluded_snippets": sorted(set(excluded_snippets or [])),
        }
    )
    previous = ContextPreview.objects.filter(idempotency_key=key).first()
    if previous is not None:
        if previous.request_digest != request_digest:
            raise Conflict
        return previous, False
    payload = build_payload(analysis, endpoint_index, node_ids, excluded_snippets)
    preview, created = ContextPreview.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "analysis": analysis,
            "snapshot_id": analysis.snapshot_id,
            "endpoint_index": endpoint_index,
            "request_digest": request_digest,
            "payload": payload,
            "payload_digest": digest(payload),
        },
    )
    if preview.request_digest != request_digest:
        raise Conflict
    return preview, created


@transaction.atomic
def create_consent(
    preview: ContextPreview, key: uuid.UUID
) -> tuple[ContextConsent, bool]:
    lock_snapshot(preview.snapshot_id)
    previous = ContextConsent.objects.filter(
        preview=preview, idempotency_key=key
    ).first()
    if previous is not None:
        return previous, False
    check_preview(preview)
    return ContextConsent.objects.get_or_create(preview=preview, idempotency_key=key)


def submit_explanation(
    key: uuid.UUID, consent_id: uuid.UUID, *, previous: Job | None = None
) -> tuple[Job, bool, bool]:
    scope = f"jobs_retry:{previous.pk}" if previous else "explanations_create"
    request_digest = digest({"consent_id": str(consent_id)})
    with transaction.atomic():
        initial = get_object_or_404(
            ContextConsent.objects.select_related("preview"), pk=consent_id
        )
        lock_snapshot(initial.preview.snapshot_id)
        replay = Job.objects.filter(scope=scope, idempotency_key=key).first()
        if replay is not None:
            if replay.request_digest != request_digest or replay.kind != "explanation":
                raise Conflict
            attach_job(replay, False)
            return replay, False, True
        consent = get_object_or_404(
            ContextConsent.objects.select_for_update(), pk=consent_id
        )
        # 等待确认行锁期间，另一请求可能已提交同一操作。
        replay = Job.objects.filter(scope=scope, idempotency_key=key).first()
        if replay is not None:
            if replay.request_digest != request_digest or replay.kind != "explanation":
                raise Conflict
            attach_job(replay, False)
            return replay, False, True
        preview = consent.preview
        if ExplanationRequest.objects.filter(consent=consent).exists():
            raise ApiProblem(
                409, "CONSENT_STALE", "该确认已用于一次任务；再次调用需明确重新确认。"
            )
        if previous is not None:
            jobs.require_retryable(previous, key)
            original = (
                ExplanationRequest.objects.select_related("consent__preview")
                .filter(job=previous)
                .first()
            )
            if original is None or original.consent.preview_id != preview.pk:
                raise ApiProblem(
                    409, "CONSENT_STALE", "重试必须重新确认原预览；变更范围请新建讲解。"
                )
        check_preview(preview)
        job, created = jobs.create_explanation_job(
            preview.snapshot_id, scope, key, request_digest, previous
        )
        if created:
            ExplanationRequest.objects.create(job=job, consent=consent)
    published = jobs.dispatch_job(job, "explanations.generate") if created else True
    job.refresh_from_db()
    return job, created, published


def execute_explanation(job_id: str) -> None:
    try:
        claim = jobs.claim_explanation(job_id)
    except DatabaseError:
        raise RuntimeError("讲解领取需等待期限核对。") from None
    if claim is None:
        return
    try:
        record = ExplanationRequest.objects.select_related("consent__preview").get(
            job_id=job_id
        )
        preview = record.consent.preview
        config = check_preview(preview)
        if not jobs.explanation_claim_valid(job_id, claim):
            return
        content, model, usage = complete(
            config,
            preview.payload["messages"],
            renew_claim=lambda: jobs.renew_explanation_claim(job_id, claim),
            poll_interval=min(5, settings.JOB_EXECUTION_TIMEOUT_SECONDS / 3),
        )
        result = validate_content(content, preview.payload["snippets"])

        def publish() -> str:
            explanation = Explanation.objects.create(
                job_id=job_id, preview=preview, content=result, model=model, usage=usage
            )
            return f"/api/v1/explanations/{explanation.pk}/"

        jobs.complete_explanation(job_id, claim, publish)
    except Exception as exc:
        if isinstance(exc, ModelFailure):
            code = exc.code
        elif isinstance(exc, ApiProblem):
            code = exc.machine_code
        elif isinstance(exc, TimeoutError):
            code = "EXECUTION_TIMEOUT"
        else:
            code = "EXPLANATION_FAILED"
            logger.error("job_id=%s exception_type=%s", job_id, type(exc).__name__)
        try:
            jobs.fail_explanation(job_id, claim, code)
        except DatabaseError:
            raise RuntimeError("讲解状态需等待期限核对。") from None


def preview_data(preview: ContextPreview) -> dict[str, Any]:
    require_snapshot_available(preview.snapshot)
    return {
        "id": preview.pk,
        "analysis_id": preview.analysis_id,
        "snapshot_id": preview.snapshot_id,
        "endpoint_index": preview.endpoint_index,
        "payload_digest": preview.payload_digest,
        "created_at": preview.created_at,
        **preview.payload,
    }
