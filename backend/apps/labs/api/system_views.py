import uuid

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.models import Analysis
from apps.jobs.api.serializers import JobSerializer
from apps.labs.api.system_serializers import (
    SystemLabInputSerializer,
    SystemLabPageSerializer,
    SystemLabRunPageSerializer,
    SystemLabRunSerializer,
    SystemLabSerializer,
)
from apps.labs.api.views import ERRORS, PAGES, WORKSPACE
from apps.labs.models import SystemLabRun
from apps.labs.system_definition import LAB_IDS, system_definition
from apps.labs.system_services import submit_system_run
from common.api import json_input, operation_key, page_response, resource_filters
from common.errors import error_body


class SystemLabsView(APIView):
    @extend_schema(
        operation_id="system_labs_list",
        parameters=[*WORKSPACE, *PAGES],
        responses={200: SystemLabPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = resource_filters(request, ("analysis_id", "endpoint_index"))
        if set(filters) != {"analysis_id", "endpoint_index"}:
            raise ValidationError({"query": ["必须指定分析与接口。"]})
        analysis = get_object_or_404(Analysis, pk=filters["analysis_id"])
        definitions = [
            system_definition(lab, analysis, int(filters["endpoint_index"]))
            for lab in LAB_IDS
        ]
        return page_response(request, definitions, SystemLabSerializer, filters=filters)


class SystemLabDetailView(APIView):
    @extend_schema(
        operation_id="system_labs_retrieve",
        parameters=WORKSPACE,
        responses={200: SystemLabSerializer, **ERRORS},
    )
    def get(self, request: Request, lab_id: str) -> Response:
        filters = resource_filters(request, ("analysis_id", "endpoint_index"))
        if set(filters) != {"analysis_id", "endpoint_index"} or set(
            request.query_params
        ) != set(filters):
            raise ValidationError({"query": ["必须且只能指定分析与接口。"]})
        analysis = get_object_or_404(Analysis, pk=filters["analysis_id"])
        return Response(
            SystemLabSerializer(
                system_definition(lab_id, analysis, int(filters["endpoint_index"]))
            ).data
        )


class SubmitSystemRunView(APIView):
    @extend_schema(
        operation_id="system_lab_runs_create",
        request=SystemLabInputSerializer,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
        ],
        responses={200: JobSerializer, 202: JobSerializer, **ERRORS},
    )
    def post(self, request: Request, lab_id: str) -> Response:
        values = json_input(request, SystemLabInputSerializer).validated_data
        job, created, published = submit_system_run(
            lab_id, operation_key(request), values
        )
        location = f"/api/v1/jobs/{job.pk}/"
        if not published:
            return Response(
                error_body(
                    "SERVICE_UNAVAILABLE",
                    "实验投递未确认，请查询已保存任务。",
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


class SystemRunsView(APIView):
    @extend_schema(
        operation_id="system_lab_runs_list",
        parameters=[
            *PAGES,
            OpenApiParameter("analysis_id", uuid.UUID),
            OpenApiParameter("endpoint_index", int),
            OpenApiParameter("job_id", uuid.UUID),
        ],
        responses={200: SystemLabRunPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = resource_filters(request, ("analysis_id", "endpoint_index", "job_id"))
        return page_response(
            request,
            SystemLabRun.objects.select_related("job", "analysis").filter(**filters),
            SystemLabRunSerializer,
            filters=filters,
        )


class SystemRunDetailView(APIView):
    @extend_schema(
        operation_id="system_lab_runs_retrieve",
        responses={200: SystemLabRunSerializer, **ERRORS},
    )
    def get(self, request: Request, run_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        run = get_object_or_404(
            SystemLabRun.objects.select_related("job", "analysis"), pk=run_id
        )
        return Response(SystemLabRunSerializer(run).data)
