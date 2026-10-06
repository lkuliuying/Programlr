import uuid

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.api.operation_serializers import (
    DeletionInputSerializer,
    DeletionPreviewSerializer,
)
from apps.jobs.api.serializers import ErrorSerializer, JobSerializer
from apps.jobs.cleanup import preview, submit_deletion, target_object
from common.api import json_input, operation_key
from common.errors import error_body


def delete_target(request: Request, target_type: str, target_id: uuid.UUID) -> Response:
    if request.query_params:
        raise ValidationError({"query": ["不支持此查询参数。"]})
    values = json_input(request, DeletionInputSerializer).validated_data
    job, created, published = submit_deletion(
        target_type, target_id, operation_key(request), values["confirmation_digest"]
    )
    location = f"/api/v1/jobs/{job.pk}/"
    if not published:
        return Response(
            error_body(
                "SERVICE_UNAVAILABLE",
                "清理任务投递未确认，目标保持隔离，请查询原任务。",
                getattr(request, "request_id", ""),
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


class ProjectDeletionPreviewView(APIView):
    @extend_schema(
        operation_id="project_deletion_preview",
        responses={
            200: DeletionPreviewSerializer,
            404: ErrorSerializer,
            503: ErrorSerializer,
        },
    )
    def get(self, request: Request, project_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        return Response(
            DeletionPreviewSerializer(
                preview("project", target_object("project", project_id))
            ).data
        )


class SnapshotDeletionPreviewView(APIView):
    @extend_schema(
        operation_id="snapshot_deletion_preview",
        responses={
            200: DeletionPreviewSerializer,
            404: ErrorSerializer,
            503: ErrorSerializer,
        },
    )
    def get(self, request: Request, snapshot_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        return Response(
            DeletionPreviewSerializer(
                preview("snapshot", target_object("snapshot", snapshot_id))
            ).data
        )
