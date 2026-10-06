import uuid
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.api.serializers import (
    GraphQuerySerializer,
    GraphSerializer,
    SourceRefSerializer,
)
from apps.analysis.models import Analysis, SourceScan
from apps.analysis.scans import submit_source_scan
from apps.analysis.services import read_graph
from apps.analysis.shared_graph import select_shared_graph, shared_graph
from apps.analysis.types import GraphQuery
from apps.jobs.api.serializers import (
    EmptyCheckSerializer,
    ErrorSerializer,
    JobSerializer,
)
from apps.projects.models import Snapshot
from common.api import operation_key
from common.errors import ApiProblem, error_body
from common.resource_state import require_snapshot_available

ERRORS = {
    status: ErrorSerializer for status in (400, 403, 404, 409, 410, 413, 415, 503)
}
WRITE_HEADERS = [
    OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
    for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
]


class RootCandidateSerializer(serializers.Serializer[dict[str, Any]]):
    file_path = serializers.CharField()
    module = serializers.CharField()
    reason = serializers.CharField()
    source_refs = SourceRefSerializer(many=True)


class SourceScanSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    snapshot_id = serializers.UUIDField()
    job_id = serializers.UUIDField()
    scan_version = serializers.CharField()
    candidate_status = serializers.ChoiceField(
        choices=["selected", "needs_root", "no_root"]
    )
    selected_root = serializers.CharField(allow_null=True)
    root_candidates = RootCandidateSerializer(many=True)
    knowledge = serializers.JSONField()
    diagnostics = serializers.JSONField()
    created_at = serializers.DateTimeField()


class SourceScansView(APIView):
    @extend_schema(
        operation_id="source_scans_create",
        request=EmptyCheckSerializer,
        parameters=WRITE_HEADERS,
        responses={200: JobSerializer, 202: JobSerializer, **ERRORS},
    )
    def post(self, request: Request, snapshot_id: uuid.UUID) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不接受查询参数。"]})
        if request.content_type != "application/json":
            raise UnsupportedMediaType(request.content_type)
        if not request.body.strip():
            raise ValidationError({"body": ["必须提供空 JSON 对象。"]})
        payload = EmptyCheckSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        snapshot = get_object_or_404(
            Snapshot.objects.select_related("project"), pk=snapshot_id
        )
        job, created, published = submit_source_scan(snapshot, operation_key(request))
        location = f"/api/v1/jobs/{job.pk}/"
        if not published:
            return Response(
                error_body(
                    "SERVICE_UNAVAILABLE",
                    "扫描投递未确认，请查询已保存任务。",
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


class SourceScanDetailView(APIView):
    @extend_schema(
        operation_id="source_scans_retrieve",
        responses={200: SourceScanSerializer, **ERRORS},
    )
    def get(self, request: Request, scan_id: uuid.UUID) -> Response:
        scan = get_object_or_404(
            SourceScan.objects.select_related("snapshot", "snapshot__project"),
            pk=scan_id,
        )
        require_snapshot_available(scan.snapshot)
        roots = scan.result["roots"]
        return Response(
            SourceScanSerializer(
                {
                    "id": scan.pk,
                    "snapshot_id": scan.snapshot_id,
                    "job_id": scan.job_id,
                    "scan_version": scan.rule_version,
                    "candidate_status": roots["status"],
                    "selected_root": roots["selected_root"],
                    "root_candidates": roots["candidates"],
                    "knowledge": scan.result["knowledge"],
                    "diagnostics": roots["diagnostics"],
                    "created_at": scan.created_at,
                }
            ).data
        )


class SharedGraphSerializer(GraphSerializer):
    direction = serializers.ChoiceField(choices=["undirected"])
    scope = serializers.ChoiceField(
        choices=["connected_shared_symbols", "all_shared_symbols"]
    )


class EndpointRelationsView(APIView):
    @extend_schema(
        operation_id="endpoint_relations_retrieve",
        parameters=[GraphQuerySerializer],
        responses={200: SharedGraphSerializer, **ERRORS},
    )
    def get(self, request: Request, analysis_id: uuid.UUID) -> Response:
        payload = GraphQuerySerializer(data=request.query_params)
        payload.is_valid(raise_exception=True)
        values = payload.validated_data
        root = values.get("root_node_id")
        query = GraphQuery(
            root_node_id=str(root) if root is not None else None,
            algorithm=values["algorithm"],
            max_nodes=values["max_nodes"],
            max_edges=values["max_edges"],
            endpoint_index=values.get("endpoint_index"),
        )
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        original, _ = read_graph(analysis)
        try:
            selection = select_shared_graph(
                shared_graph(analysis.pk, analysis.endpoints, original), query
            )
        except KeyError:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "共享图中不存在该节点或接口。"
            ) from None
        return Response(
            SharedGraphSerializer(
                {
                    "analysis_id": analysis.pk,
                    "snapshot_id": analysis.snapshot_id,
                    "rule_version": analysis.rule_version,
                    "root_node_id": query.root_node_id,
                    "endpoint_index": query.endpoint_index,
                    "algorithm": query.algorithm,
                    "coverage": analysis.coverage,
                    "diagnostics_url": f"/api/v1/analyses/{analysis.pk}/diagnostics/",
                    "relation_reviews": [],
                    **selection,
                }
            ).data
        )
