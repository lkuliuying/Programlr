import uuid

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.api.serializers import ErrorSerializer, JobSerializer
from apps.projects.api.schema import ProjectSchema
from apps.projects.api.serializers import (
    ImportInputSerializer,
    ProjectInputSerializer,
    ProjectPageSerializer,
    ProjectSerializer,
    SnapshotNameInputSerializer,
    SnapshotPageSerializer,
    SnapshotSerializer,
    SourceContentSerializer,
    SourceFilePageSerializer,
    SourceFileSerializer,
)
from apps.projects.exceptions import ImportRejected
from apps.projects.models import Project, Snapshot, SourceFile
from apps.projects.services import (
    create_project,
    rename_snapshot,
    source_content,
    submit_import,
)
from common.api import operation_key, page_response, query_numbers
from common.errors import ApiProblem

ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 409, 413, 415, 503)}
WRITE_HEADERS = [
    OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
    for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
]
PAGES = [OpenApiParameter("page", int), OpenApiParameter("page_size", int)]


class ProjectsView(APIView):
    schema = ProjectSchema()

    @extend_schema(
        operation_id="projects_list",
        parameters=PAGES,
        responses={200: ProjectPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        return page_response(request, Project.objects.all(), ProjectSerializer)

    @extend_schema(
        operation_id="projects_create",
        parameters=WRITE_HEADERS,
        request=ProjectInputSerializer,
        responses={200: ProjectSerializer, 201: ProjectSerializer, **ERRORS},
    )
    def post(self, request: Request) -> Response:
        if request.content_type != "application/json":
            raise UnsupportedMediaType(request.content_type)
        if not request.body.strip():
            raise ValidationError({"body": ["必须提供 JSON 对象。"]})
        payload = ProjectInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        project, created = create_project(
            operation_key(request), payload.validated_data["name"]
        )
        return Response(ProjectSerializer(project).data, status=201 if created else 200)


class ProjectDetailView(APIView):
    @extend_schema(
        operation_id="projects_retrieve", responses={200: ProjectSerializer, **ERRORS}
    )
    def get(self, request: Request, project_id: uuid.UUID) -> Response:
        return Response(
            ProjectSerializer(get_object_or_404(Project, pk=project_id)).data
        )


class ImportsView(APIView):
    schema = ProjectSchema()
    parser_classes = [MultiPartParser]

    @extend_schema(
        operation_id="imports_create",
        parameters=[
            *WRITE_HEADERS,
            OpenApiParameter(
                "Location", str, OpenApiParameter.HEADER, response=[200, 202, 503]
            ),
        ],
        request=ImportInputSerializer,
        responses={200: JobSerializer, 202: JobSerializer, **ERRORS},
    )
    def post(self, request: Request, project_id: uuid.UUID) -> Response:
        project = get_object_or_404(Project, pk=project_id)
        key = operation_key(request)
        if request.content_type.split(";")[0] != "multipart/form-data":
            raise UnsupportedMediaType(request.content_type)
        if (
            set(request.data) != {"archive"}
            or bool(request._request.POST)
            or len(request.FILES.getlist("archive")) != 1
        ):
            raise ValidationError({"archive": ["仅接受一个 archive 文件字段。"]})
        payload = ImportInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            job, created, published = submit_import(
                project, key, payload.validated_data["archive"]
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
            from common.errors import error_body

            return Response(
                error_body(
                    "SERVICE_UNAVAILABLE",
                    "导入投递未确认，记录已保存，请查询任务状态。",
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


class SnapshotsView(APIView):
    @extend_schema(
        operation_id="snapshots_list",
        parameters=PAGES,
        responses={200: SnapshotPageSerializer, **ERRORS},
    )
    def get(self, request: Request, project_id: uuid.UUID) -> Response:
        get_object_or_404(Project, pk=project_id)
        return page_response(
            request, Snapshot.objects.filter(project_id=project_id), SnapshotSerializer
        )


class SnapshotDetailView(APIView):
    schema = ProjectSchema()

    @extend_schema(
        operation_id="snapshots_retrieve", responses={200: SnapshotSerializer, **ERRORS}
    )
    def get(self, request: Request, snapshot_id: uuid.UUID) -> Response:
        return Response(
            SnapshotSerializer(get_object_or_404(Snapshot, pk=snapshot_id)).data
        )

    @extend_schema(
        operation_id="snapshots_rename",
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("X-CSRFToken", "Origin")
        ],
        request=SnapshotNameInputSerializer,
        responses={200: SnapshotSerializer, **ERRORS},
    )
    def patch(self, request: Request, snapshot_id: uuid.UUID) -> Response:
        snapshot = get_object_or_404(Snapshot, pk=snapshot_id)
        if request.content_type != "application/json":
            raise UnsupportedMediaType(request.content_type)
        if not request.body.strip():
            raise ValidationError({"body": ["必须提供 JSON 对象。"]})
        payload = SnapshotNameInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        renamed = rename_snapshot(snapshot, payload.validated_data["name"])
        return Response(SnapshotSerializer(renamed).data)


class SourceFilesView(APIView):
    @extend_schema(
        operation_id="snapshot_files_list",
        parameters=PAGES,
        responses={200: SourceFilePageSerializer, **ERRORS},
    )
    def get(self, request: Request, snapshot_id: uuid.UUID) -> Response:
        get_object_or_404(Snapshot, pk=snapshot_id)
        return page_response(
            request,
            SourceFile.objects.filter(snapshot_id=snapshot_id),
            SourceFileSerializer,
        )


class SourceContentView(APIView):
    @extend_schema(
        operation_id="snapshot_file_content_retrieve",
        parameters=[
            OpenApiParameter("start_line", int),
            OpenApiParameter("end_line", int),
        ],
        responses={200: SourceContentSerializer, **ERRORS},
    )
    def get(
        self, request: Request, snapshot_id: uuid.UUID, file_id: uuid.UUID
    ) -> Response:
        source = get_object_or_404(
            SourceFile.objects.select_related("snapshot"),
            pk=file_id,
            snapshot_id=snapshot_id,
        )
        start = query_numbers(
            request,
            {
                "start_line": (1, source.line_count),
                "end_line": (min(source.line_count, 200), source.line_count),
            },
        )["start_line"]
        values = query_numbers(
            request,
            {
                "start_line": (1, source.line_count),
                "end_line": (min(source.line_count, start + 199), source.line_count),
            },
        )
        end = values["end_line"]
        if end < start or end - start + 1 > 500:
            raise ValidationError({"end_line": ["行范围必须有序且不超过 500 行。"]})
        try:
            content = source_content(source, start, end)
        except ImportRejected:
            raise ApiProblem(
                409, "SNAPSHOT_NOT_READY", "快照内容不可读取或完整性校验失败。"
            ) from None
        return Response(
            {
                **SourceFileSerializer(source).data,
                "start_line": start,
                "end_line": end,
                "content": content,
            }
        )
