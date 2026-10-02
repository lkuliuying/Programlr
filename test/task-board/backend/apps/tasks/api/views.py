import uuid
from urllib.parse import urlencode

from django.core.paginator import EmptyPage, Paginator
from django.middleware.csrf import get_token
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tasks.api.schema import TaskSchema
from apps.tasks.api.serializers import (
    CsrfSerializer,
    ErrorSerializer,
    TaskPageSerializer,
    TaskSerializer,
)
from apps.tasks.models import Task
from apps.tasks.services import create_task
from common.errors import error_body

ERRORS = {400: ErrorSerializer, 403: ErrorSerializer, 503: ErrorSerializer}


class CsrfView(APIView):
    @extend_schema(
        operation_id="task_board_csrf_retrieve",
        responses={200: CsrfSerializer, 403: ErrorSerializer},
    )
    def get(self, request: Request) -> Response:
        return Response({"csrf_token": get_token(request._request)})


class TaskListCreateView(GenericAPIView[Task]):
    serializer_class = TaskSerializer
    schema = TaskSchema()

    @extend_schema(
        operation_id="task_board_tasks_create",
        request=TaskSerializer,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
        ],
        responses={
            200: TaskSerializer,
            201: TaskSerializer,
            409: ErrorSerializer,
            413: ErrorSerializer,
            415: ErrorSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request) -> Response:
        if request.content_type != "application/json":
            raise UnsupportedMediaType(request.content_type)
        if not request.body.strip():
            raise ValidationError({"body": ["必须提供 JSON 对象。"]})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            key = uuid.UUID(request.headers.get("Idempotency-Key", ""))
        except ValueError:
            raise ValidationError(
                {"idempotency_key": ["必须提供 UUID 形式的操作标识。"]}
            ) from None
        task, created = create_task(serializer.validated_data["title"], key)
        return Response(self.get_serializer(task).data, status=201 if created else 200)

    @extend_schema(
        operation_id="task_board_tasks_list",
        parameters=[OpenApiParameter("page", int), OpenApiParameter("page_size", int)],
        responses={200: TaskPageSerializer, 404: ErrorSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        if set(request.query_params) - {"page", "page_size"}:
            raise ValidationError({"query": ["不支持此查询参数。"]})
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
        paginator = Paginator(Task.objects.all(), values["page_size"])
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
            return "/api/v1/tasks/?" + urlencode(
                {"page": number, "page_size": values["page_size"]}
            )

        return Response(
            {
                "count": paginator.count,
                "next": link(page.next_page_number()) if page.has_next() else None,
                "previous": link(page.previous_page_number())
                if page.has_previous()
                else None,
                "results": self.get_serializer(list(page.object_list), many=True).data,
            }
        )
