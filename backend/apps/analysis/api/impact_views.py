import uuid
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.api.comparison_views import ready_comparison
from apps.analysis.api.review_serializers import RelationDecisionSerializer
from apps.analysis.api.serializers import (
    DiagnosticSerializer,
    GraphEdgeSerializer,
    GraphNodeSerializer,
)
from apps.analysis.impact_services import analysis_impact, comparison_impact
from apps.analysis.models import Analysis
from apps.analysis.types import (
    DEFAULT_GRAPH_EDGES,
    DEFAULT_GRAPH_NODES,
    MAX_QUERY_EDGES,
    MAX_QUERY_NODES,
)
from apps.jobs.api.serializers import ErrorSerializer


class ImpactQuerySerializer(serializers.Serializer[dict[str, Any]]):
    node_id = serializers.UUIDField(required=False)
    change_id = serializers.UUIDField(required=False)
    include_candidates = serializers.BooleanField(default=False)
    max_nodes = serializers.IntegerField(
        min_value=1, max_value=MAX_QUERY_NODES, default=DEFAULT_GRAPH_NODES
    )
    max_edges = serializers.IntegerField(
        min_value=1, max_value=MAX_QUERY_EDGES, default=DEFAULT_GRAPH_EDGES
    )

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        allowed = {
            "include_candidates",
            "max_nodes",
            "max_edges",
            "change_id" if self.context["comparison"] else "node_id",
        }
        if set(data) - allowed or any(len(data.getlist(key)) != 1 for key in data):
            raise serializers.ValidationError(
                {"query": ["不支持未知或重复的查询参数。"]}
            )
        for key in ("max_nodes", "max_edges"):
            if key in data and (
                len(data[key]) > 10
                or not data[key].isascii()
                or not data[key].isdecimal()
            ):
                raise serializers.ValidationError(
                    {"query": ["图预算必须为范围内的 ASCII 正整数。"]}
                )
        if "include_candidates" in data and data["include_candidates"] not in {
            "true",
            "false",
        }:
            raise serializers.ValidationError(
                {"query": ["候选开关必须为 true 或 false。"]}
            )
        if not self.context["comparison"] and "node_id" not in data:
            raise serializers.ValidationError({"query": ["必须指定本图节点 node_id。"]})
        value: dict[str, Any] = super().to_internal_value(data)
        return value


class ImpactResultSerializer(serializers.Serializer[dict[str, Any]]):
    node = GraphNodeSerializer()
    path_node_ids = serializers.ListField(child=serializers.UUIDField())
    path_edge_ids = serializers.ListField(child=serializers.UUIDField())
    via_candidate = serializers.BooleanField()


class ImpactSerializer(serializers.Serializer[dict[str, Any]]):
    analysis_id = serializers.UUIDField()
    snapshot_id = serializers.UUIDField()
    graph_version = serializers.CharField()
    rule_version = serializers.CharField()
    include_candidates = serializers.BooleanField()
    max_nodes = serializers.IntegerField()
    max_edges = serializers.IntegerField()
    starts = serializers.ListField(child=serializers.UUIDField())
    nodes = GraphNodeSerializer(many=True)
    edges = GraphEdgeSerializer(many=True)
    results = ImpactResultSerializer(many=True)
    relation_reviews = RelationDecisionSerializer(many=True)
    visited_nodes = serializers.IntegerField()
    visited_edges = serializers.IntegerField()
    truncated = serializers.BooleanField()
    truncation_reasons = serializers.ListField(child=serializers.CharField())
    unmapped_files = serializers.ListField(child=serializers.CharField())
    uncovered_files = serializers.ListField(child=serializers.CharField())
    limitations = serializers.ListField(child=serializers.CharField())
    diagnostics = DiagnosticSerializer(many=True)
    diagnostics_url = serializers.CharField()


class ImpactSideSerializer(serializers.Serializer[dict[str, Any]]):
    snapshot_id = serializers.UUIDField()
    analysis_id = serializers.UUIDField(allow_null=True)
    available = serializers.BooleanField()
    reason = serializers.CharField(allow_null=True)
    changed_files = serializers.ListField(child=serializers.CharField())
    impact = ImpactSerializer(allow_null=True)


class ComparisonImpactSerializer(serializers.Serializer[dict[str, Any]]):
    comparison_id = serializers.UUIDField()
    change_id = serializers.UUIDField(allow_null=True)
    include_candidates = serializers.BooleanField()
    base = ImpactSideSerializer()
    target = ImpactSideSerializer()
    limitations = serializers.ListField(child=serializers.CharField())


PARAMETERS = [
    OpenApiParameter("include_candidates", bool),
    OpenApiParameter("max_nodes", int),
    OpenApiParameter("max_edges", int),
]
ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 409, 500)}


class AnalysisImpactView(APIView):
    @extend_schema(
        operation_id="analysis_impact_retrieve",
        parameters=[OpenApiParameter("node_id", uuid.UUID, required=True), *PARAMETERS],
        responses={200: ImpactSerializer, **ERRORS},
    )
    def get(self, request: Request, analysis_id: uuid.UUID) -> Response:
        query = ImpactQuerySerializer(
            data=request.query_params, context={"comparison": False}
        )
        query.is_valid(raise_exception=True)
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        values = query.validated_data
        result = analysis_impact(
            analysis,
            node_id=str(values["node_id"]),
            include_candidates=values["include_candidates"],
            max_nodes=values["max_nodes"],
            max_edges=values["max_edges"],
        )
        return Response(ImpactSerializer(result).data)


class ComparisonImpactView(APIView):
    @extend_schema(
        operation_id="comparison_impact_retrieve",
        parameters=[OpenApiParameter("change_id", uuid.UUID), *PARAMETERS],
        responses={200: ComparisonImpactSerializer, **ERRORS},
    )
    def get(self, request: Request, comparison_id: uuid.UUID) -> Response:
        query = ImpactQuerySerializer(
            data=request.query_params, context={"comparison": True}
        )
        query.is_valid(raise_exception=True)
        result, data = ready_comparison(comparison_id)
        values = query.validated_data
        impact = comparison_impact(
            result,
            dict(data),
            include_candidates=values["include_candidates"],
            max_nodes=values["max_nodes"],
            max_edges=values["max_edges"],
            change_id=values.get("change_id"),
        )
        return Response(ComparisonImpactSerializer(impact).data)
