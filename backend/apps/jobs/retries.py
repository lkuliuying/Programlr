from __future__ import annotations

import uuid
from typing import Any

from django.core.files.uploadedfile import UploadedFile

from apps.analysis.models import AnalysisRequest
from apps.analysis.services import submit_analysis
from apps.jobs.models import Job
from apps.jobs.services import require_retryable, submit_check
from apps.projects.models import ImportRequest, SourceFile
from apps.projects.services import submit_import
from common.errors import ApiProblem


def submit_retry(
    previous: Job,
    key: uuid.UUID,
    upload: UploadedFile[Any] | None = None,
    *,
    consent_id: uuid.UUID | None = None,
) -> tuple[Job, bool, bool]:
    require_retryable(previous, key)
    if previous.kind == "snapshot_comparison":
        from apps.analysis.diffs.services import retry_comparison

        return retry_comparison(previous, key)
    if previous.kind == "lab":
        from apps.labs.models import SystemLabRun
        from apps.labs.services import retry_run
        from apps.labs.system_services import retry_system_run

        if SystemLabRun.objects.filter(job=previous).exists():
            return retry_system_run(previous, key)
        return retry_run(previous, key)
    if previous.kind == "explanation":
        from apps.explanations.services import submit_explanation

        if consent_id is None:
            raise ApiProblem(400, "VALIDATION_ERROR", "讲解重试必须提供新的发送确认。")
        return submit_explanation(key, consent_id, previous=previous)
    if previous.kind == "system_check":
        return submit_check(key, previous=previous)
    if previous.kind == "analysis":
        analysis = (
            AnalysisRequest.objects.select_related("snapshot")
            .filter(job=previous)
            .first()
        )
        if (
            analysis is None
            or not SourceFile.objects.filter(
                snapshot_id=analysis.snapshot_id, file_path=analysis.root_urlconf
            ).exists()
        ):
            raise ApiProblem(
                409, "RETRY_INPUT_UNAVAILABLE", "原分析请求或快照入口不可用。"
            )
        return submit_analysis(
            analysis.snapshot, key, analysis.root_urlconf, previous=previous
        )
    record = (
        ImportRequest.objects.select_related("project").filter(job=previous).first()
    )
    if record is None:
        raise ApiProblem(409, "RETRY_INPUT_UNAVAILABLE", "原导入请求不可用。")
    if upload is None:
        raise ApiProblem(400, "VALIDATION_ERROR", "导入重试必须重新上传原 ZIP 文件。")
    # 原暂存可能已被清理；复用上传校验和摘要比较，不保留未过滤的长期副本。
    return submit_import(record.project, key, upload, previous=previous)
