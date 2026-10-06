import uuid
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.api.serializers import ErrorSerializer, JobSerializer
from apps.jobs.models import Job
from apps.projects.exceptions import ImportRejected
from apps.projects.models import ImportRequest, Project
from apps.projects.services import submit_import
from common.api import operation_key
from common.errors import ApiProblem, error_body
from common.resource_state import require_project_available


class FolderInputSerializer(serializers.Serializer[dict[str, Any]]):
    manifest = serializers.FileField()
    files = serializers.ListField(
        child=serializers.FileField(), min_length=1, max_length=2000
    )


def submit_folder(
    request: Request, project: Project, previous: Job | None = None
) -> Response:
    require_project_available(project)
    if request.query_params:
        raise ValidationError({"query": ["不接受查询参数。"]})
    if request.content_type.split(";")[0] != "multipart/form-data":
        raise UnsupportedMediaType(request.content_type)
    if (
        set(request.data) != {"manifest", "files"}
        or bool(request._request.POST)
        or len(request.FILES.getlist("manifest")) != 1
    ):
        raise ValidationError({"body": ["仅接受 manifest 文件及有序 files 文件。"]})
    try:
        job, created, published = submit_import(
            project,
            operation_key(request),
            None,
            previous=previous,
            folder_files=request.FILES.getlist("files"),
            manifest=request.FILES["manifest"],
        )
    except ImportRejected as exc:
        raise ApiProblem(
            503
            if exc.code == "IMPORT_STORAGE_FAILED"
            else 413
            if exc.code == "ARCHIVE_LIMIT_EXCEEDED"
            else 400,
            exc.code,
            exc.message,
            {"reason": exc.reason},
        ) from None
    location = f"/api/v1/jobs/{job.pk}/"
    if not published:
        return Response(
            error_body(
                "SERVICE_UNAVAILABLE",
                "目录导入投递未确认，请查看已保存任务。",
                getattr(request, "request_id"),
                {"job_url": location},
            ),
            status=503,
            headers={"Location": location},
        )
    return Response(
        JobSerializer(job).data,
        status=202 if created else 200,
        headers={"Location": location},
    )


class FolderImportsView(APIView):
    parser_classes = [MultiPartParser]

    @extend_schema(
        operation_id="folder_imports_create",
        request=FolderInputSerializer,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
        ],
        responses={
            200: JobSerializer,
            202: JobSerializer,
            **{
                status: ErrorSerializer
                for status in (400, 403, 404, 409, 410, 413, 415, 503)
            },
        },
    )
    def post(self, request: Request, project_id: uuid.UUID) -> Response:
        return submit_folder(request, get_object_or_404(Project, pk=project_id))


class FolderRetriesView(APIView):
    parser_classes = [MultiPartParser]

    @extend_schema(
        operation_id="folder_imports_retry",
        request=FolderInputSerializer,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
        ],
        responses={
            200: JobSerializer,
            202: JobSerializer,
            **{
                status: ErrorSerializer
                for status in (400, 403, 404, 409, 410, 413, 415, 503)
            },
        },
    )
    def post(self, request: Request, job_id: uuid.UUID) -> Response:
        record = get_object_or_404(
            ImportRequest.objects.select_related("job", "project"), job_id=job_id
        )
        if record.source_kind != "folder":
            raise ApiProblem(
                409, "RETRY_SOURCE_MISMATCH", "该任务必须使用原 ZIP 重试入口。"
            )
        return submit_folder(request, record.project, record.job)
