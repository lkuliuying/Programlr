import uuid

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.api.review_serializers import (
    RelationReviewInputSerializer,
    RelationReviewPageSerializer,
    RelationReviewResultSerializer,
    RelationReviewSerializer,
    RelationReviewStateSerializer,
)
from apps.analysis.models import Analysis, RelationReview
from apps.analysis.reviews import current_review, request_candidates, submit_review
from apps.jobs.api.serializers import ErrorSerializer
from common.api import json_input, operation_key, page_response, resource_filters

ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 409, 413, 415, 503)}


class RelationReviewsView(APIView):
    @extend_schema(
        operation_id="relation_reviews_list",
        parameters=[
            OpenApiParameter("request_id", uuid.UUID, required=True),
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={200: RelationReviewPageSerializer, **ERRORS},
    )
    def get(self, request: Request, analysis_id: uuid.UUID) -> Response:
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        filters = resource_filters(request, ("request_id",))
        if "request_id" not in filters:
            raise ValidationError({"request_id": ["必须指定当前分析的前端请求。"]})
        request_id = uuid.UUID(filters["request_id"])
        request_candidates(analysis, request_id)
        state = current_review(analysis, request_id)
        # 截止修订固定本页视图，新增历史不会与已读取状态混用。
        records = RelationReview.objects.filter(
            analysis=analysis, request_id=request_id, revision__lte=state["revision"]
        ).order_by("-revision", "-id")
        response = page_response(
            request, records, RelationReviewSerializer, filters=filters
        )
        response.data["state"] = RelationReviewStateSerializer(dict(state)).data
        return response

    @extend_schema(
        operation_id="relation_reviews_create",
        request=RelationReviewInputSerializer,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
        ],
        responses={
            200: RelationReviewResultSerializer,
            201: RelationReviewResultSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request, analysis_id: uuid.UUID) -> Response:
        payload = json_input(request, RelationReviewInputSerializer).validated_data
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        record, state, created = submit_review(
            analysis,
            operation_key(request),
            payload["request_id"],
            payload["target_id"],
            payload["action"],
            payload["expected_revision"],
        )
        return Response(
            RelationReviewResultSerializer({"record": record, "state": state}).data,
            status=201 if created else 200,
        )
