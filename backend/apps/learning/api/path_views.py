import uuid

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.models import Analysis
from apps.learning.api.path_serializers import (
    AttemptReviewPageSerializer,
    AttemptReviewSerializer,
    CurriculumPageSerializer,
    KnowledgeCurriculumSerializer,
    LearningPathSerializer,
    ReviewInputSerializer,
)
from apps.learning.api.views import ERRORS, PAGES
from apps.learning.models import AttemptReview, ExerciseAttempt, KnowledgeCurriculum
from apps.learning.paths.services import learning_path
from apps.learning.reviews import submit_review
from common.api import json_input, operation_key, page_response, resource_filters


class CurriculaView(APIView):
    @extend_schema(
        operation_id="knowledge_curricula_list",
        parameters=PAGES,
        responses={200: CurriculumPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        return page_response(
            request, KnowledgeCurriculum.objects.all(), KnowledgeCurriculumSerializer
        )


class CurriculumDetailView(APIView):
    @extend_schema(
        operation_id="knowledge_curricula_retrieve",
        responses={200: KnowledgeCurriculumSerializer, **ERRORS},
    )
    def get(self, request: Request, curriculum_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        return Response(
            KnowledgeCurriculumSerializer(
                get_object_or_404(KnowledgeCurriculum, pk=curriculum_id)
            ).data
        )


class LearningPathView(APIView):
    @extend_schema(
        operation_id="learning_paths_retrieve",
        parameters=[
            OpenApiParameter("analysis_id", uuid.UUID, required=True),
            OpenApiParameter("endpoint_index", int, required=True),
            OpenApiParameter("curriculum_id", uuid.UUID, required=True),
            OpenApiParameter("goal", str),
        ],
        responses={200: LearningPathSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = resource_filters(
            request, ("analysis_id", "endpoint_index", "curriculum_id")
        )
        if (
            set(filters) != {"analysis_id", "endpoint_index", "curriculum_id"}
            or set(request.query_params) - {*filters, "goal"}
            or len(request.query_params.getlist("goal")) > 1
        ):
            raise ValidationError(
                {"query": ["必须指定分析、接口及课程；不支持未知或重复参数。"]}
            )
        curriculum = get_object_or_404(KnowledgeCurriculum, pk=filters["curriculum_id"])
        analysis = get_object_or_404(Analysis, pk=filters["analysis_id"])
        result = learning_path(
            curriculum,
            analysis,
            int(filters["endpoint_index"]),
            request.query_params.get("goal", "create-task"),
        )
        return Response(LearningPathSerializer(result).data)


class AttemptReviewsView(APIView):
    @extend_schema(
        operation_id="attempt_reviews_list",
        parameters=[*PAGES, OpenApiParameter("attempt_id", uuid.UUID, required=True)],
        responses={200: AttemptReviewPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = resource_filters(request, ("attempt_id",))
        if not filters:
            raise ValidationError({"attempt_id": ["必须指定原作答。"]})
        get_object_or_404(ExerciseAttempt, pk=filters["attempt_id"])
        return page_response(
            request,
            AttemptReview.objects.filter(**filters),
            AttemptReviewSerializer,
            filters=filters,
        )

    @extend_schema(
        operation_id="attempt_reviews_create",
        request=ReviewInputSerializer,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
        ],
        responses={
            200: AttemptReviewSerializer,
            201: AttemptReviewSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request) -> Response:
        record, created = submit_review(
            operation_key(request),
            json_input(request, ReviewInputSerializer).validated_data,
        )
        return Response(
            AttemptReviewSerializer(record).data, status=201 if created else 200
        )
