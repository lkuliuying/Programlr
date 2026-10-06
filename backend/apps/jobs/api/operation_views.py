import uuid
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl

from django.db.models import Case, CharField, Count, Q, Value, When
from django.http import HttpResponse, QueryDict
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.api.operation_serializers import (
    OperationLogPageSerializer,
    OperationLogSerializer,
    OperationStatisticsSerializer,
    RelatedOperationLogPageSerializer,
    RelatedOperationLogSerializer,
)
from apps.jobs.api.serializers import ErrorSerializer
from apps.jobs.models import OperationLog
from apps.jobs.operation_export import export_operations
from apps.jobs.operation_queries import (
    ACTIVE_RESULTS,
    FILTER_NAMES,
    OPERATION_LABELS,
    read_operation_query,
)
from apps.jobs.operation_times import operation_log_queryset
from common.api import page_response, query_numbers

__all__ = ["OPERATION_LABELS"]
FILTER_PARAMETERS = [
    OpenApiParameter(name, str) for name in sorted(FILTER_NAMES - {"q"})
] + [OpenApiParameter("q", {"type": "string", "maxLength": 200})]
PAGE_PARAMETERS = [OpenApiParameter("page", int), OpenApiParameter("page_size", int)]
ERRORS = {400: ErrorSerializer, 404: ErrorSerializer, 503: ErrorSerializer}


class OperationQueryView(APIView):
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        if request.method == "GET":
            # 仅这些日志读取入口放宽字段数，仍限制查询长度、重复字段和字段白名单。
            request._request.GET = QueryDict()
            self.format_kwarg = self.get_format_suffix(**kwargs)
            raw = request.META.get("QUERY_STRING", "")
            if not isinstance(raw, str) or len(raw) > 4096:
                raise ValidationError({"query": ["查询文本不能超过 4096 字符。"]})
            try:
                entries = parse_qsl(
                    raw,
                    keep_blank_values=True,
                    strict_parsing=True,
                    errors="strict",
                    max_num_fields=12,
                )
            except ValueError:
                raise ValidationError(
                    {"query": ["查询文本格式无效或字段数量超过接口限制。"]}
                ) from None
            query = QueryDict(mutable=True)
            for name, value in entries:
                query.appendlist(name, value)
            query._mutable = False
            setattr(request._request, "GET", query)
        super().initial(request, *args, **kwargs)


class OperationLogsView(OperationQueryView):
    @extend_schema(
        operation_id="operation_logs_list",
        parameters=[*PAGE_PARAMETERS, *FILTER_PARAMETERS],
        responses={200: OperationLogPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        query = read_operation_query(request)
        return page_response(
            request, query.logs, OperationLogSerializer, filters=query.filters
        )


class OperationStatisticsView(OperationQueryView):
    @extend_schema(
        operation_id="operation_logs_statistics",
        parameters=[*PAGE_PARAMETERS, *FILTER_PARAMETERS],
        responses={200: OperationStatisticsSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        query = read_operation_query(request)
        query_numbers(
            request,
            {"page": (1, 2147483647), "page_size": (20, 100)},
            extra=set(query.filters),
        )
        as_of = timezone.now()
        recent_start, previous_start = (
            as_of - timedelta(days=7),
            as_of - timedelta(days=14),
        )
        recent = Q(ended_at__gte=recent_start, ended_at__lt=as_of)
        previous = Q(ended_at__gte=previous_start, ended_at__lt=recent_start)
        aggregations: dict[str, Any] = {
            "count": Count("id"),
            "failed_count": Count("id", filter=Q(result="failed")),
            "active_count": Count("id", filter=Q(result__in=ACTIVE_RESULTS)),
            "retryable_count": Count("id", filter=~Q(retry_action="none")),
            "recent_success": Count("id", filter=recent & Q(result="succeeded")),
            "recent_finished": Count(
                "id", filter=recent & Q(result__in=["succeeded", "failed"])
            ),
            "previous_success": Count("id", filter=previous & Q(result="succeeded")),
            "previous_finished": Count(
                "id", filter=previous & Q(result__in=["succeeded", "failed"])
            ),
        }
        buckets = []
        for day in range(7):
            start, end = (
                recent_start + timedelta(days=day),
                recent_start + timedelta(days=day + 1),
            )
            buckets.append((start, end))
            aggregations[f"day_{day}"] = Count(
                "id", filter=Q(created_at__gte=start, created_at__lt=end)
            )
            aggregations[f"failed_{day}"] = Count(
                "id", filter=Q(result="failed", ended_at__gte=start, ended_at__lt=end)
            )
        # 同一个聚合语句取得计数与趋势，所有卡片使用相同数据库快照和时钟。
        values = query.base.order_by().aggregate(**aggregations)

        def rate(prefix: str) -> float | None:
            return (
                round(
                    values[f"{prefix}_success"] * 100 / values[f"{prefix}_finished"], 2
                )
                if values[f"{prefix}_finished"]
                else None
            )

        recent_rate, previous_rate = rate("recent"), rate("previous")
        payload: dict[str, Any] = {
            key: values[key]
            for key in ("count", "failed_count", "active_count", "retryable_count")
        }
        payload.update(
            as_of=as_of,
            recent_success_rate=recent_rate,
            previous_success_rate=previous_rate,
            success_rate_change_pp=round(recent_rate - previous_rate, 2)
            if recent_rate is not None and previous_rate is not None
            else None,
            recent_window={"start": recent_start, "end": as_of},
            previous_window={"start": previous_start, "end": recent_start},
            trend=[
                {
                    "start": start,
                    "end": end,
                    "count": values[f"day_{day}"],
                    "failed_count": values[f"failed_{day}"],
                }
                for day, (start, end) in enumerate(buckets)
            ],
        )
        return Response(OperationStatisticsSerializer(payload).data)


class OperationExportView(OperationQueryView):
    @extend_schema(
        operation_id="operation_logs_export",
        parameters=FILTER_PARAMETERS,
        responses={
            (200, "text/csv"): OpenApiTypes.BINARY,
            413: ErrorSerializer,
            **ERRORS,
        },
    )
    def get(self, request: Request) -> HttpResponse:
        query = read_operation_query(request, export=True)
        return export_operations(query.logs)


class OperationLogDetailView(APIView):
    @extend_schema(
        operation_id="operation_logs_retrieve",
        responses={200: OperationLogSerializer, **ERRORS},
    )
    def get(self, request: Request, log_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["详情不接受查询参数。"]})
        return Response(
            OperationLogSerializer(
                get_object_or_404(operation_log_queryset(), pk=log_id)
            ).data
        )


class RelatedOperationLogsView(APIView):
    @extend_schema(
        operation_id="operation_logs_related",
        parameters=PAGE_PARAMETERS,
        responses={200: RelatedOperationLogPageSerializer, **ERRORS},
    )
    def get(self, request: Request, log_id: uuid.UUID) -> Response:
        log = get_object_or_404(OperationLog.objects.select_related("job"), pk=log_id)
        logs = operation_log_queryset().none()
        if log.job:
            job = log.job
            relation = (
                (
                    Q(job_id=job.parent_job_id)
                    if job.parent_job_id
                    else Q(pk__isnull=True)
                )
                | Q(job__parent_job_id=job.pk)
                | Q(job__previous_job_id=job.pk)
            )
            if job.previous_job_id:
                relation |= Q(job_id=job.previous_job_id)
            logs = (
                operation_log_queryset()
                .filter(relation)
                .exclude(pk=log.pk)
                .annotate(
                    relation=Case(
                        When(job_id=job.parent_job_id, then=Value("parent")),
                        When(job_id=job.previous_job_id, then=Value("previous")),
                        When(job__previous_job_id=job.pk, then=Value("retry")),
                        default=Value("child"),
                        output_field=CharField(),
                    )
                )
                .order_by("-created_at", "-display_id")
            )
        return page_response(request, logs, RelatedOperationLogSerializer)


class HistoricalOperationLogsView(APIView):
    @extend_schema(
        operation_id="operation_logs_history",
        parameters=PAGE_PARAMETERS,
        responses={200: OperationLogPageSerializer, **ERRORS},
    )
    def get(self, request: Request, log_id: uuid.UUID) -> Response:
        log = get_object_or_404(OperationLog, pk=log_id)
        logs = (
            operation_log_queryset()
            .filter(operation=log.operation)
            .filter(
                Q(created_at__lt=log.created_at)
                | Q(created_at=log.created_at, display_id__lt=log.display_id)
            )
        )
        if log.snapshot_id:
            logs = logs.filter(snapshot_id=log.snapshot_id)
        elif log.project_id:
            logs = logs.filter(project_id=log.project_id)
        else:
            logs = logs.none()
        return page_response(
            request, logs.order_by("-created_at", "-display_id"), OperationLogSerializer
        )
