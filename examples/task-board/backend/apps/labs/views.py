import uuid
from typing import Any

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.labs.models import LabSession
from apps.labs.services import CASES, close_run, observation, open_run, task_key
from apps.tasks.api.serializers import ErrorSerializer, TaskSerializer
from apps.tasks.services import create_task
from common.errors import error_body

ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 409, 413, 415, 503)}


class ObservationSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    example_version = serializers.CharField()
    closed = serializers.BooleanField()
    record_count = serializers.IntegerField(min_value=0, max_value=4)
    deleted_count = serializers.IntegerField(min_value=0, max_value=4)
    expires_at = serializers.DateTimeField()


def require_body(request: Request, expected: dict[str, str]) -> None:
    if request.query_params:
        raise ValidationError({"query": ["不支持查询参数。"]})
    if request.content_type != "application/json":
        raise UnsupportedMediaType(request.content_type)
    if not request.body.strip() or request.data != expected:
        raise ValidationError({"body": ["仅接受该固定实验用例的输入。"]})


class RunView(APIView):
    @extend_schema(
        operation_id="lab_board_runs_retrieve",
        responses={200: ObservationSerializer, **ERRORS},
    )
    def get(self, request: Request, run_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持查询参数。"]})
        return Response(observation(get_object_or_404(LabSession, pk=run_id)))

    @extend_schema(
        operation_id="lab_board_runs_open",
        request={"application/json": {"type": "object", "additionalProperties": False}},
        responses={200: ObservationSerializer, **ERRORS},
    )
    def post(self, request: Request, run_id: uuid.UUID) -> Response:
        require_body(request, {})
        return Response(observation(open_run(run_id)))


class CaseView(APIView):
    @extend_schema(
        operation_id="lab_board_cases_create",
        request={
            "application/json": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string", "enum": ["实验任务", "", "   "]}
                },
            }
        },
        responses={
            200: TaskSerializer,
            201: TaskSerializer,
            400: ErrorSerializer,
            409: ErrorSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request, run_id: uuid.UUID, case: str) -> Response:
        if case not in CASES:
            raise ValidationError({"case": ["未知实验用例。"]})
        require_body(request, CASES[case])
        with transaction.atomic():
            run = get_object_or_404(LabSession.objects.select_for_update(), pk=run_id)
            if run.closed or run.expires_at <= timezone.now():
                return Response(
                    error_body(
                        "LAB_RUN_CLOSED",
                        "实验已关闭或过期。",
                        getattr(request, "request_id"),
                    ),
                    status=409,
                )
            serializer = TaskSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            task, created = create_task(
                serializer.validated_data["title"], task_key(run_id, case)
            )
            return Response(TaskSerializer(task).data, status=201 if created else 200)


class CloseView(APIView):
    @extend_schema(
        operation_id="lab_board_runs_close",
        request={"application/json": {"type": "object", "additionalProperties": False}},
        responses={200: ObservationSerializer, **ERRORS},
    )
    def post(self, request: Request, run_id: uuid.UUID) -> Response:
        require_body(request, {})
        get_object_or_404(LabSession, pk=run_id)
        return Response(close_run(run_id))


urlpatterns = [
    path("runs/<uuid:run_id>/", RunView.as_view()),
    path("runs/<uuid:run_id>/cases/<str:case>/", CaseView.as_view()),
    path("runs/<uuid:run_id>/close/", CloseView.as_view()),
]
