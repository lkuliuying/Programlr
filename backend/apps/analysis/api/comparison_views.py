import uuid

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.api.comparison_serializers import (
    ComparisonFileDetailSerializer,
    ComparisonFilePageSerializer,
    ComparisonFileSerializer,
    ComparisonHistoryPageSerializer,
    ComparisonHistorySerializer,
    ComparisonInputSerializer,
    SnapshotComparisonSerializer,
)
from apps.analysis.diffs.services import read_comparison, submit_comparison
from apps.analysis.diffs.types import ComparisonData
from apps.analysis.models import Analysis, SnapshotComparison, SnapshotComparisonRequest
from apps.jobs.api.serializers import ErrorSerializer, JobSerializer
from apps.jobs.models import Job
from apps.projects.models import Project, Snapshot
from common.api import json_input, operation_key, page_response
from common.errors import ApiProblem, error_body

ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 409, 413, 415, 503)}
PAGES = [OpenApiParameter("page", int), OpenApiParameter("page_size", int)]


def ready_comparison(
    comparison_id: uuid.UUID,
) -> tuple[SnapshotComparison, ComparisonData]:
    record = get_object_or_404(
        SnapshotComparisonRequest.objects.select_related("job"), pk=comparison_id
    )
    if record.job.status != Job.Status.SUCCEEDED:
        raise ApiProblem(
            409,
            "COMPARISON_NOT_READY",
            "对比结果尚未成功发布，请查看任务状态。",
            {"job_url": f"/api/v1/jobs/{record.job_id}/"},
        )
    result = (
        SnapshotComparison.objects.select_related(
            "request", "request__base_analysis", "request__target_analysis"
        )
        .filter(request=record)
        .first()
    )
    if result is None:
        raise ApiProblem(500, "INTERNAL_ERROR", "成功任务缺少对应对比结果。")
    return result, read_comparison(result)


class ProjectComparisonsView(APIView):
    @extend_schema(
        operation_id="project_snapshot_comparisons_list",
        parameters=PAGES,
        responses={200: ComparisonHistoryPageSerializer, **ERRORS},
    )
    def get(self, request: Request, project_id: uuid.UUID) -> Response:
        project = get_object_or_404(Project, pk=project_id)
        records = (
            SnapshotComparisonRequest.objects.filter(project=project)
            .select_related("job", "result")
            .defer("result__data")
        )
        return page_response(request, records, ComparisonHistorySerializer)

    @extend_schema(
        operation_id="project_snapshot_comparisons_create",
        request=ComparisonInputSerializer,
        parameters=[
            *[
                OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
                for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
            ],
            OpenApiParameter(
                "Location", str, OpenApiParameter.HEADER, response=[200, 202, 503]
            ),
        ],
        responses={200: JobSerializer, 202: JobSerializer, **ERRORS},
    )
    def post(self, request: Request, project_id: uuid.UUID) -> Response:
        fields = json_input(request, ComparisonInputSerializer).validated_data
        project = get_object_or_404(Project, pk=project_id)
        base, target = [
            get_object_or_404(Snapshot, pk=fields[key])
            for key in ("base_snapshot_id", "target_snapshot_id")
        ]
        base_analysis, target_analysis = [
            get_object_or_404(Analysis, pk=fields[key]) if fields[key] else None
            for key in ("base_analysis_id", "target_analysis_id")
        ]
        job, created, published = submit_comparison(
            project,
            operation_key(request),
            base,
            target,
            base_analysis,
            target_analysis,
        )
        location = f"/api/v1/jobs/{job.pk}/"
        if not published:
            return Response(
                error_body(
                    "SERVICE_UNAVAILABLE",
                    "对比投递未确认，记录已保存，请查询任务状态。",
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


class ComparisonDetailView(APIView):
    @extend_schema(
        operation_id="snapshot_comparisons_retrieve",
        responses={200: SnapshotComparisonSerializer, **ERRORS},
    )
    def get(self, request: Request, comparison_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ApiProblem(400, "VALIDATION_ERROR", "不支持此查询参数。")
        result, data = ready_comparison(comparison_id)
        record = result.request
        return Response(
            SnapshotComparisonSerializer(
                {
                    **data,
                    "id": record.pk,
                    "job_id": record.job_id,
                    "project_id": record.project_id,
                    "base_snapshot_id": record.base_snapshot_id,
                    "target_snapshot_id": record.target_snapshot_id,
                    "base_analysis_id": record.base_analysis_id,
                    "target_analysis_id": record.target_analysis_id,
                    "created_at": result.created_at,
                }
            ).data
        )


class ComparisonFilesView(APIView):
    @extend_schema(
        operation_id="comparison_files_list",
        parameters=PAGES,
        responses={200: ComparisonFilePageSerializer, **ERRORS},
    )
    def get(self, request: Request, comparison_id: uuid.UUID) -> Response:
        _, data = ready_comparison(comparison_id)
        return page_response(
            request, [dict(item) for item in data["files"]], ComparisonFileSerializer
        )


class ComparisonFileDetailView(APIView):
    @extend_schema(
        operation_id="comparison_files_retrieve",
        responses={200: ComparisonFileDetailSerializer, **ERRORS},
    )
    def get(
        self, request: Request, comparison_id: uuid.UUID, change_id: uuid.UUID
    ) -> Response:
        if request.query_params:
            raise ApiProblem(400, "VALIDATION_ERROR", "不支持此查询参数。")
        _, data = ready_comparison(comparison_id)
        file = next(
            (item for item in data["files"] if item["id"] == str(change_id)), None
        )
        if file is None:
            raise ApiProblem(404, "RESOURCE_NOT_FOUND", "当前对比不存在该文件变化。")
        return Response(ComparisonFileDetailSerializer(dict(file)).data)
