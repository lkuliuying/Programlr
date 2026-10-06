import uuid
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.models import Analysis
from apps.jobs.api.serializers import ErrorSerializer
from apps.labs.api.serializers import (
    LabInputSerializer,
    LabPageSerializer,
    LabRunPageSerializer,
    LabRunSerializer,
    LabSerializer,
)
from apps.labs.definition import definition
from apps.labs.models import LabRun
from common.api import page_response, resource_filters
from common.errors import ApiProblem
from common.resource_state import require_snapshot_available
from common.retirement import retired_feature

ERRORS = {
    status: ErrorSerializer for status in (400, 403, 404, 409, 410, 413, 415, 503)
}
WORKSPACE = [
    OpenApiParameter("analysis_id", uuid.UUID, required=True),
    OpenApiParameter("endpoint_index", int, required=True),
]
PAGES = [OpenApiParameter("page", int), OpenApiParameter("page_size", int)]


def lab_for(
    request: Request, lab_id: str = "request-validation"
) -> tuple[dict[str, str], dict[str, Any]]:
    if lab_id != "request-validation":
        raise ApiProblem(404, "RESOURCE_NOT_FOUND", "实验不存在。")
    filters = resource_filters(request, ("analysis_id", "endpoint_index"))
    if set(filters) != {"analysis_id", "endpoint_index"}:
        raise ValidationError({"query": ["必须指定分析与接口。"]})
    analysis = get_object_or_404(Analysis, pk=filters["analysis_id"])
    require_snapshot_available(analysis.snapshot)
    return filters, definition(analysis, int(filters["endpoint_index"]))


class LabsView(APIView):
    @extend_schema(
        operation_id="labs_list",
        parameters=[*WORKSPACE, *PAGES],
        responses={200: LabPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters, lab = lab_for(request)
        return page_response(request, [lab], LabSerializer, filters=filters)


class LabDetailView(APIView):
    @extend_schema(
        operation_id="labs_retrieve",
        parameters=WORKSPACE,
        responses={200: LabSerializer, **ERRORS},
    )
    def get(self, request: Request, lab_id: str) -> Response:
        if set(request.query_params) != {"analysis_id", "endpoint_index"}:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        return Response(LabSerializer(lab_for(request, lab_id)[1]).data)


class SubmitRunView(APIView):
    @extend_schema(
        operation_id="lab_runs_create",
        deprecated=True,
        request=LabInputSerializer,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
        ],
        responses=ERRORS,
    )
    def post(self, request: Request, lab_id: str) -> Response:
        retired_feature("lab")


class RunsView(APIView):
    @extend_schema(
        operation_id="lab_runs_list",
        parameters=[
            *PAGES,
            OpenApiParameter("analysis_id", uuid.UUID),
            OpenApiParameter("endpoint_index", int),
            OpenApiParameter("job_id", uuid.UUID),
        ],
        responses={200: LabRunPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = resource_filters(request, ("analysis_id", "endpoint_index", "job_id"))
        return page_response(
            request,
            LabRun.objects.select_related("job", "analysis").filter(
                analysis__snapshot__deletion_request_id__isnull=True,
                analysis__snapshot__project__deletion_request_id__isnull=True,
                **filters,
            ),
            LabRunSerializer,
            filters=filters,
        )


class RunDetailView(APIView):
    @extend_schema(
        operation_id="lab_runs_retrieve", responses={200: LabRunSerializer, **ERRORS}
    )
    def get(self, request: Request, run_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        run = get_object_or_404(
            LabRun.objects.select_related("job", "analysis__snapshot__project"),
            pk=run_id,
        )
        require_snapshot_available(run.analysis.snapshot)
        return Response(LabRunSerializer(run).data)
