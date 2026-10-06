import uuid
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.api.serializers import SourceRefSerializer
from apps.analysis.models import Analysis, SourceScan
from apps.jobs.api.serializers import ErrorSerializer
from apps.projects.models import SourceFile
from apps.projects.source_evidence import file_evidence
from common.api import page_response, resource_filters
from common.resource_state import require_snapshot_available


class SourceEvidenceSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    kind = serializers.ChoiceField(
        choices=["interface", "frontend", "relation", "knowledge"]
    )
    # DRF 元类将声明转成输出字段；这里与基类的界面标签属性同名。
    label = serializers.CharField()  # type: ignore[assignment]
    source_ref = SourceRefSerializer()
    endpoint_index = serializers.IntegerField(allow_null=True)
    node_id = serializers.UUIDField(allow_null=True)
    concept_key = serializers.CharField(allow_null=True)


class SourceEvidencePageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = SourceEvidenceSerializer(many=True)
    snapshot_id = serializers.UUIDField()
    file_id = serializers.UUIDField()
    analysis_id = serializers.UUIDField(allow_null=True)
    scan_id = serializers.UUIDField(allow_null=True)
    scope = serializers.ChoiceField(choices=["persisted_source_evidence"])


class SourceEvidenceView(APIView):
    @extend_schema(
        operation_id="snapshot_file_evidence_list",
        parameters=[
            OpenApiParameter("analysis_id", uuid.UUID),
            OpenApiParameter("scan_id", uuid.UUID),
            OpenApiParameter("page", int),
            OpenApiParameter("page_size", int),
        ],
        responses={
            200: SourceEvidencePageSerializer,
            **{status: ErrorSerializer for status in (400, 403, 404, 409, 410)},
        },
    )
    def get(
        self, request: Request, snapshot_id: uuid.UUID, file_id: uuid.UUID
    ) -> Response:
        filters = resource_filters(request, ("analysis_id", "scan_id"))
        source = get_object_or_404(
            SourceFile.objects.select_related("snapshot", "snapshot__project"),
            pk=file_id,
            snapshot_id=snapshot_id,
        )
        require_snapshot_available(source.snapshot)
        analysis = (
            get_object_or_404(
                Analysis,
                pk=filters["analysis_id"],
                snapshot_id=snapshot_id,
                job__status="succeeded",
            )
            if "analysis_id" in filters
            else None
        )
        if analysis is not None:
            bound = str(analysis.source_scan_id) if analysis.source_scan_id else None
            if "scan_id" in filters and filters["scan_id"] != bound:
                raise ValidationError({"scan_id": ["分析与扫描版本不一致。"]})
            if bound:
                filters["scan_id"] = bound
        scan = (
            get_object_or_404(
                SourceScan,
                pk=filters["scan_id"],
                snapshot_id=snapshot_id,
                job__status="succeeded",
            )
            if "scan_id" in filters
            else None
        )
        response = page_response(
            request,
            file_evidence(source, analysis, scan),
            SourceEvidenceSerializer,
            filters=filters,
        )
        response.data.update(
            {
                "snapshot_id": str(snapshot_id),
                "file_id": str(file_id),
                "analysis_id": str(analysis.pk) if analysis else None,
                "scan_id": str(scan.pk) if scan else None,
                "scope": "persisted_source_evidence",
            }
        )
        return response
