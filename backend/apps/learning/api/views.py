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
from apps.learning.api.serializers import (
    AttemptInputSerializer,
    ExerciseAttemptPageSerializer,
    ExerciseAttemptSerializer,
    ExercisePageSerializer,
    ExerciseSerializer,
    KnowledgeCardPageSerializer,
    KnowledgeCardSerializer,
)
from apps.learning.models import Exercise, ExerciseAttempt, KnowledgeCard
from apps.learning.services import submit_attempt
from common.api import json_input, operation_key, page_response, resource_filters

ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 409, 413, 415, 503)}
PAGES = [OpenApiParameter("page", int), OpenApiParameter("page_size", int)]
WORKSPACE = [
    OpenApiParameter("analysis_id", uuid.UUID, required=True),
    OpenApiParameter("endpoint_index", int, required=True),
]


def workspace(request: Request) -> tuple[dict[str, str], dict[str, Any]]:
    filters = resource_filters(request, ("analysis_id", "endpoint_index"))
    if set(filters) != {"analysis_id", "endpoint_index"}:
        raise ValidationError({"query": ["必须指定 analysis_id 和 endpoint_index。"]})
    analysis = get_object_or_404(Analysis, pk=filters["analysis_id"])
    index = int(filters["endpoint_index"])
    if index >= len(analysis.endpoints):
        raise ValidationError({"endpoint_index": ["接口序号越界。"]})
    return filters, {"analysis": analysis, "endpoint_index": index}


class KnowledgeCardsView(APIView):
    @extend_schema(
        operation_id="knowledge_cards_list",
        parameters=PAGES,
        responses={200: KnowledgeCardPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        return page_response(
            request, KnowledgeCard.objects.all(), KnowledgeCardSerializer
        )


class KnowledgeCardDetailView(APIView):
    @extend_schema(
        operation_id="knowledge_cards_retrieve",
        responses={200: KnowledgeCardSerializer, **ERRORS},
    )
    def get(self, request: Request, card_id: uuid.UUID) -> Response:
        return Response(
            KnowledgeCardSerializer(get_object_or_404(KnowledgeCard, pk=card_id)).data
        )


class ExercisesView(APIView):
    @extend_schema(
        operation_id="exercises_list",
        parameters=[*PAGES, *WORKSPACE],
        responses={200: ExercisePageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters, context = workspace(request)
        return page_response(
            request,
            Exercise.objects.select_related("example"),
            ExerciseSerializer,
            filters=filters,
            context=context,
        )


class ExerciseDetailView(APIView):
    @extend_schema(
        operation_id="exercises_retrieve",
        parameters=WORKSPACE,
        responses={200: ExerciseSerializer, **ERRORS},
    )
    def get(self, request: Request, exercise_id: uuid.UUID) -> Response:
        _, context = workspace(request)
        if set(request.query_params) != {"analysis_id", "endpoint_index"}:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        return Response(
            ExerciseSerializer(
                get_object_or_404(
                    Exercise.objects.select_related("example"), pk=exercise_id
                ),
                context=context,
            ).data
        )


class ExerciseAttemptsView(APIView):
    @extend_schema(
        operation_id="exercise_attempts_list",
        parameters=[
            *PAGES,
            OpenApiParameter("snapshot_id", uuid.UUID),
            OpenApiParameter("analysis_id", uuid.UUID),
            OpenApiParameter("endpoint_index", int),
        ],
        responses={200: ExerciseAttemptPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = resource_filters(
            request, ("snapshot_id", "analysis_id", "endpoint_index")
        )
        return page_response(
            request,
            ExerciseAttempt.objects.select_related("exercise").filter(**filters),
            ExerciseAttemptSerializer,
            filters=filters,
        )

    @extend_schema(
        operation_id="exercise_attempts_create",
        request=AttemptInputSerializer,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
        ],
        responses={
            200: ExerciseAttemptSerializer,
            201: ExerciseAttemptSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request) -> Response:
        values = json_input(request, AttemptInputSerializer).validated_data
        attempt, created = submit_attempt(operation_key(request), values)
        return Response(
            ExerciseAttemptSerializer(attempt).data, status=201 if created else 200
        )


class ExerciseAttemptDetailView(APIView):
    @extend_schema(
        operation_id="exercise_attempts_retrieve",
        responses={200: ExerciseAttemptSerializer, **ERRORS},
    )
    def get(self, request: Request, attempt_id: uuid.UUID) -> Response:
        return Response(
            ExerciseAttemptSerializer(
                get_object_or_404(
                    ExerciseAttempt.objects.select_related("exercise"), pk=attempt_id
                )
            ).data
        )
