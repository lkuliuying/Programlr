import json
import re
import uuid
from collections.abc import Callable
from typing import Any

from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse, JsonResponse

from apps.jobs.audit import active_log, event, finish_http, target_values
from apps.jobs.models import Job, OperationLog
from common.errors import error_body


def operation_target(request: HttpRequest) -> dict[str, Any] | None:
    if request.method not in {"POST", "DELETE"}:
        return None
    match = re.fullmatch(
        r"/api/v1/projects/([0-9a-fA-F-]{36})/((?:folder-)?imports/)?", request.path
    )
    if match and (
        (request.method == "DELETE" and not match[2])
        or (request.method == "POST" and match[2])
    ):
        return {
            "operation": "delete_project" if request.method == "DELETE" else "import",
            "project_id": uuid.UUID(match[1]),
            "source_kind": "folder"
            if match[2] == "folder-imports/"
            else "zip"
            if match[2]
            else "",
        }
    match = re.fullmatch(
        r"/api/v1/snapshots/([0-9a-fA-F-]{36})/(analyses/|source-scans/)?", request.path
    )
    if match and (request.method == "DELETE" or match[2]):
        return {
            "operation": "delete_snapshot"
            if request.method == "DELETE"
            else "source_scan"
            if match[2] == "source-scans/"
            else "analysis",
            "snapshot_id": uuid.UUID(match[1]),
        }
    retry = re.fullmatch(
        r"/api/v1/jobs/([0-9a-fA-F-]{36})/(?:folder-)?retries/", request.path
    )
    if retry:
        return {"operation": "retry", "prior_job_id": uuid.UUID(retry[1])}
    if request.path == "/api/v1/explanations/":
        return {"operation": "explanation"}
    return None


class OperationLogMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            target = operation_target(request)
        except ValueError:
            target = None
        if target is None:
            return self.get_response(request)
        from apps.projects.models import Project, Snapshot

        request_id = uuid.uuid4().hex
        setattr(request, "request_id", request_id)
        key = None
        try:
            key = uuid.UUID(request.headers.get("Idempotency-Key", ""))
        except ValueError:
            pass
        try:
            prior_job_id = target.pop("prior_job_id", None)
            if prior_job_id is not None:
                prior = Job.objects.filter(pk=prior_job_id).first()
                if prior:
                    target.update(target_values(prior))
            if target.get("snapshot_id"):
                snapshot = (
                    Snapshot.objects.select_related("project")
                    .filter(pk=target["snapshot_id"])
                    .first()
                )
                if snapshot:
                    target.update(
                        project_id=snapshot.project_id,
                        project_name=snapshot.project.name,
                        object_name=snapshot.name,
                    )
            elif target.get("project_id"):
                project = Project.objects.filter(pk=target["project_id"]).first()
                if project:
                    target.update(project_name=project.name, object_name=project.name)
            log = OperationLog.objects.create(
                **target,
                request_id=request_id,
                idempotency_key=key,
                events=[
                    event(
                        "submitted",
                        **(
                            {"target_job_id": str(prior_job_id)}
                            if prior_job_id is not None
                            else {}
                        ),
                    )
                ],
            )
        except DatabaseError:
            return JsonResponse(
                error_body(
                    "SERVICE_UNAVAILABLE",
                    "操作日志暂不可保存，本次操作未开始。",
                    request_id,
                ),
                status=503,
            )
        token = active_log.set(log.pk)
        try:
            response = self.get_response(request)
            code = ""
            if response.status_code >= 400:
                try:
                    data = json.loads(response.content)
                    code = data.get("code", "") if isinstance(data, dict) else ""
                except (ValueError, TypeError):
                    pass
            try:
                finish_http(log.pk, response.status_code, code)
            except DatabaseError:
                # 入口事件已经持久化，结果缺失不能伪装成已知成功。
                response = JsonResponse(
                    error_body(
                        "SERVICE_UNAVAILABLE",
                        "操作结果日志未确认，请查询原操作记录。",
                        request_id,
                        {"operation_log_id": str(log.pk)},
                    ),
                    status=503,
                )
            response["X-Operation-Log-ID"] = str(log.pk)
            return response
        finally:
            active_log.reset(token)
