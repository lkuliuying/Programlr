import uuid

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.explanations.api.serializers import (
    ConsentInputSerializer,
    ContextConsentSerializer,
    ContextPreviewSerializer,
    ExplanationInputSerializer,
    ExplanationPageSerializer,
    ExplanationSerializer,
    PreviewInputSerializer,
)
from apps.explanations.models import ContextPreview, Explanation
from apps.explanations.services import (
    create_consent,
    create_preview,
    preview_data,
    submit_explanation,
)
from apps.jobs.api.serializers import ErrorSerializer, JobSerializer
from common.api import json_input, operation_key, page_response, resource_filters
from common.errors import error_body
from common.resource_state import require_snapshot_available

ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 409, 413, 415, 503)}
POST_HEADERS = [
    OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
    for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
]
PAGES = [OpenApiParameter("page", int), OpenApiParameter("page_size", int)]


class ContextPreviewsView(APIView):
    @extend_schema(
        operation_id="context_previews_create",
        request=PreviewInputSerializer,
        parameters=POST_HEADERS,
        responses={
            200: ContextPreviewSerializer,
            201: ContextPreviewSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request) -> Response:
        values = json_input(request, PreviewInputSerializer).validated_data
        nodes = values.get("node_ids")
        preview, created = create_preview(
            operation_key(request),
            values["analysis_id"],
            values["endpoint_index"],
            [str(n) for n in nodes] if nodes is not None else None,
            values.get("excluded_snippets"),
        )
        return Response(
            ContextPreviewSerializer(preview_data(preview)).data,
            status=201 if created else 200,
        )


class ContextPreviewDetailView(APIView):
    @extend_schema(
        operation_id="context_previews_retrieve",
        responses={200: ContextPreviewSerializer, **ERRORS},
    )
    def get(self, request: Request, preview_id: uuid.UUID) -> Response:
        return Response(
            ContextPreviewSerializer(
                preview_data(get_object_or_404(ContextPreview, pk=preview_id))
            ).data
        )


class ContextConsentsView(APIView):
    @extend_schema(
        operation_id="context_consents_create",
        request=ConsentInputSerializer,
        parameters=POST_HEADERS,
        responses={
            200: ContextConsentSerializer,
            201: ContextConsentSerializer,
            **ERRORS,
        },
    )
    def post(self, request: Request, preview_id: uuid.UUID) -> Response:
        json_input(request, ConsentInputSerializer)
        consent, created = create_consent(
            get_object_or_404(ContextPreview, pk=preview_id), operation_key(request)
        )
        return Response(
            ContextConsentSerializer(consent).data, status=201 if created else 200
        )


class ExplanationsView(APIView):
    @extend_schema(
        operation_id="explanations_list",
        parameters=[
            *PAGES,
            OpenApiParameter("snapshot_id", uuid.UUID),
            OpenApiParameter("analysis_id", uuid.UUID),
            OpenApiParameter("endpoint_index", int),
        ],
        responses={200: ExplanationPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = resource_filters(
            request, ("snapshot_id", "analysis_id", "endpoint_index")
        )
        results = Explanation.objects.select_related("preview").filter(
            preview__snapshot__deletion_request_id__isnull=True,
            preview__snapshot__project__deletion_request_id__isnull=True,
            **{"preview__" + k: v for k, v in filters.items()},
        )
        return page_response(request, results, ExplanationSerializer, filters=filters)

    @extend_schema(
        operation_id="explanations_create",
        request=ExplanationInputSerializer,
        parameters=[
            *POST_HEADERS,
            OpenApiParameter(
                "Location", str, OpenApiParameter.HEADER, response=[200, 202, 503]
            ),
        ],
        responses={200: JobSerializer, 202: JobSerializer, **ERRORS},
    )
    def post(self, request: Request) -> Response:
        values = json_input(request, ExplanationInputSerializer).validated_data
        job, created, published = submit_explanation(
            operation_key(request), values["consent_id"]
        )
        location = f"/api/v1/jobs/{job.pk}/"
        if not published:
            return Response(
                error_body(
                    "SERVICE_UNAVAILABLE",
                    "讲解投递未确认，请查询保存的任务，不要自动重发。",
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


class ExplanationDetailView(APIView):
    @extend_schema(
        operation_id="explanations_retrieve",
        responses={200: ExplanationSerializer, **ERRORS},
    )
    def get(self, request: Request, explanation_id: uuid.UUID) -> Response:
        explanation = get_object_or_404(
            Explanation.objects.select_related("preview__snapshot__project"),
            pk=explanation_id,
        )
        require_snapshot_available(explanation.preview.snapshot)
        return Response(ExplanationSerializer(explanation).data)
