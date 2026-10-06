import uuid

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.learning.api.progress_serializers import (
    CurriculumProgressInputSerializer,
    CurriculumProgressSerializer,
)
from apps.learning.api.views import ERRORS
from apps.learning.models import KnowledgeCurriculum
from apps.learning.progress import curriculum_progress
from common.retirement import retired_feature
from common.schema import RequiredPatchSchema


class CurriculumProgressView(APIView):
    @extend_schema(
        operation_id="curriculum_progress_retrieve",
        responses={200: CurriculumProgressSerializer, **ERRORS},
    )
    def get(self, request: Request, curriculum_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        curriculum = get_object_or_404(KnowledgeCurriculum, pk=curriculum_id)
        return Response(
            CurriculumProgressSerializer(curriculum_progress(curriculum)).data
        )


class CurriculumCardProgressView(APIView):
    schema = RequiredPatchSchema()

    @extend_schema(
        operation_id="curriculum_card_progress_update",
        deprecated=True,
        parameters=[
            OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
            for name in ("Origin", "X-CSRFToken")
        ],
        request=CurriculumProgressInputSerializer,
        responses=ERRORS,
    )
    def patch(
        self, request: Request, curriculum_id: uuid.UUID, card_id: uuid.UUID
    ) -> Response:
        retired_feature("course_progress")
