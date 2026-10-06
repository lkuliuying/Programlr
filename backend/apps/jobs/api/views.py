import uuid
from urllib.parse import urlencode

from django.core.paginator import EmptyPage, Paginator
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.api.schema import SystemCheckSchema
from apps.jobs.api.serializers import (
    CsrfSerializer,
    ErrorSerializer,
    JobPageSerializer,
    JobSerializer,
    SystemCheckSerializer,
)
from apps.jobs.models import Job, SystemCheck
from apps.jobs.retries import submit_retry
from apps.jobs.services import require_retryable
from apps.projects.api.serializers import ImportInputSerializer
from apps.projects.exceptions import ImportRejected
from common.api import operation_key
from common.errors import ApiProblem, error_body
from common.retirement import retired_feature

ERRORS = {
    400: ErrorSerializer,
    403: ErrorSerializer,
    404: ErrorSerializer,
    410: ErrorSerializer,
    503: ErrorSerializer,
}


class CsrfView(APIView):
    @extend_schema(
        operation_id="csrf_retrieve",
        responses={200: CsrfSerializer, 403: ErrorSerializer},
    )
    def get(self, request: Request) -> Response:
        return Response({"csrf_token": get_token(request._request)})


class SystemChecksView(APIView):
    schema = SystemCheckSchema()

    @extend_schema(
        operation_id="system_checks_create",
        deprecated=True,
        request={"application/json": {"type": "object", "additionalProperties": False}},
        parameters=[
            OpenApiParameter(
                "Idempotency-Key", str, OpenApiParameter.HEADER, required=True
            ),
            OpenApiParameter(
                "X-CSRFToken", str, OpenApiParameter.HEADER, required=True
            ),
            OpenApiParameter("Origin", str, OpenApiParameter.HEADER, required=True),
            OpenApiParameter(
                "Location", str, OpenApiParameter.HEADER, response=[200, 202, 503]
            ),
        ],
        responses={
            409: ErrorSerializer,
            415: ErrorSerializer,
            413: ErrorSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request) -> Response:
        retired_feature("system_check")


class SystemCheckDetailView(APIView):
    @extend_schema(
        operation_id="system_checks_retrieve",
        responses={200: SystemCheckSerializer, **ERRORS},
    )
    def get(self, request: Request, check_id: uuid.UUID) -> Response:
        return Response(
            SystemCheckSerializer(get_object_or_404(SystemCheck, pk=check_id)).data
        )


class JobDetailView(APIView):
    @extend_schema(
        operation_id="jobs_retrieve", responses={200: JobSerializer, **ERRORS}
    )
    def get(self, request: Request, job_id: uuid.UUID) -> Response:
        return Response(
            JobSerializer(
                get_object_or_404(Job.objects.select_related("check_result"), pk=job_id)
            ).data
        )


class JobRetriesView(APIView):
    schema = SystemCheckSchema()
    parser_classes = [JSONParser, MultiPartParser]

    @extend_schema(
        operation_id="jobs_retry",
        description="仅显式重试失败任务。分析、源码扫描、清理提交空 JSON；ZIP 导入重传原文件，文件夹使用专用入口；讲解提交新的 consent_id 并确认可能重复计费。退役类型与已清理结果返回 410。",
        request={
            "application/json": {
                "oneOf": [
                    {"type": "object", "additionalProperties": False},
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["consent_id"],
                        "properties": {
                            "consent_id": {"type": "string", "format": "uuid"}
                        },
                    },
                ]
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {"archive": {"type": "string", "format": "binary"}},
                "required": ["archive"],
                "additionalProperties": False,
            },
        },
        parameters=[
            *[
                OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
                for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
            ],
            OpenApiParameter(
                "Location", str, OpenApiParameter.HEADER, response=[200, 202, 503]
            ),
        ],
        responses={
            200: JobSerializer,
            202: JobSerializer,
            409: ErrorSerializer,
            413: ErrorSerializer,
            415: ErrorSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request, job_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        previous = get_object_or_404(Job, pk=job_id)
        key = operation_key(request)
        require_retryable(previous, key)
        if previous.kind == "import" and previous.source_kind == "folder":
            raise ApiProblem(
                422,
                "FOLDER_RETRY_REQUIRED",
                "文件夹任务请重新选择原文件夹并使用文件夹恢复入口。",
            )
        upload = None
        consent_id = None
        if previous.kind == "import":
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
            upload = payload.validated_data["archive"]
        elif previous.kind == "explanation":
            from apps.explanations.api.serializers import ExplanationInputSerializer

            if request.content_type != "application/json":
                raise UnsupportedMediaType(request.content_type)
            explanation_input = ExplanationInputSerializer(data=request.data)
            explanation_input.is_valid(raise_exception=True)
            consent_id = explanation_input.validated_data["consent_id"]
        else:
            if request.content_type != "application/json":
                raise UnsupportedMediaType(request.content_type)
            if (
                not request.body.strip()
                or not isinstance(request.data, dict)
                or request.data
            ):
                raise ValidationError({"body": ["重试只接受空 JSON 对象。"]})
        try:
            job, created, published = submit_retry(
                previous, key, upload, consent_id=consent_id
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
                    "重试投递未确认，请查询已保存的任务。",
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


class JobsView(APIView):
    @extend_schema(
        operation_id="jobs_list",
        parameters=[
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
            OpenApiParameter(
                "kind",
                str,
                enum=[
                    "system_check",
                    "import",
                    "analysis",
                    "explanation",
                    "lab",
                    "snapshot_comparison",
                    "source_scan",
                    "delete",
                ],
            ),
            OpenApiParameter("snapshot_id", str, pattern=r"^[0-9a-f-]{36}$"),
        ],
        responses={200: JobPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        if set(request.query_params) - {"page", "page_size", "kind", "snapshot_id"}:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        filters: dict[str, str] = {}
        for name in ("kind", "snapshot_id"):
            if name not in request.query_params:
                continue
            value = request.query_params[name]
            if len(request.query_params.getlist(name)) != 1 or not value:
                raise ValidationError({name: ["筛选值必须唯一且非空。"]})
            if name == "kind" and value not in {
                "system_check",
                "import",
                "analysis",
                "explanation",
                "lab",
                "snapshot_comparison",
                "source_scan",
                "delete",
            }:
                raise ValidationError({name: ["任务类型不受支持。"]})
            if name == "snapshot_id":
                try:
                    if str(uuid.UUID(value)) != value:
                        raise ValueError
                except ValueError:
                    raise ValidationError(
                        {name: ["快照标识必须为规范 UUID。"]}
                    ) from None
            filters[name] = value
        values = {}
        for name, default, maximum in (
            ("page", "1", 2147483647),
            ("page_size", "20", 100),
        ):
            raw = request.query_params.get(name, default)
            if (
                len(raw) > 10
                or len(request.query_params.getlist(name)) > 1
                or not raw.isascii()
                or not raw.isdecimal()
                or not 1 <= int(raw) <= maximum
            ):
                raise ValidationError({name: ["必须为有效范围内的正整数。"]})
            values[name] = int(raw)
        paginator = Paginator(
            Job.objects.select_related("check_result").filter(**filters),
            values["page_size"],
        )
        try:
            page = paginator.page(values["page"])
        except EmptyPage:
            return Response(
                error_body(
                    "PAGE_NOT_FOUND",
                    "请求的页码不存在。",
                    getattr(request, "request_id"),
                ),
                status=404,
            )

        def link(number: int) -> str:
            return "/api/v1/jobs/?" + urlencode(
                {"page": number, "page_size": values["page_size"], **filters}
            )

        return Response(
            {
                "count": paginator.count,
                "next": link(page.next_page_number()) if page.has_next() else None,
                "previous": link(page.previous_page_number())
                if page.has_previous()
                else None,
                "results": JobSerializer(list(page.object_list), many=True).data,
            }
        )
