from pathlib import PurePosixPath
from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.analysis.api.review_serializers import RelationDecisionSerializer
from apps.analysis.models import Analysis
from apps.analysis.types import (
    DEFAULT_GRAPH_EDGES,
    DEFAULT_GRAPH_NODES,
    MAX_QUERY_EDGES,
    MAX_QUERY_NODES,
)


class AnalysisInputSerializer(serializers.Serializer[dict[str, Any]]):
    root_urlconf = serializers.CharField(max_length=1024, trim_whitespace=False)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if (
            not isinstance(data, dict)
            or set(data) != {"root_urlconf"}
            or not isinstance(data.get("root_urlconf"), str)
        ):
            raise serializers.ValidationError(
                {"root_urlconf": ["仅接受必填字符串 root_urlconf。"]}
            )
        value: dict[str, Any] = super().to_internal_value(data)
        return value

    def validate_root_urlconf(self, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or path.as_posix() != value
            or ".." in path.parts
            or "\\" in value
            or ":" in value
            or not value.endswith(".py")
            or any(ord(c) < 32 for c in value)
        ):
            raise serializers.ValidationError("必须是快照内规范的 Python 相对路径。")
        return value


class SourceRefSerializer(serializers.Serializer[dict[str, Any]]):
    snapshot_id = serializers.UUIDField()
    file_path = serializers.CharField()
    start_line = serializers.IntegerField(min_value=1)
    end_line = serializers.IntegerField(min_value=1)


class SymbolSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField()
    source_ref = SourceRefSerializer()


class EvidenceSerializer(serializers.Serializer[dict[str, Any]]):
    kind = serializers.ChoiceField(
        choices=["source_fact", "static_inference", "framework_rule"]
    )
    rule = serializers.CharField()
    source_ref = SourceRefSerializer(allow_null=True)


class FrontendLinkSerializer(serializers.Serializer[dict[str, Any]]):
    request_id = serializers.UUIDField()
    method = serializers.CharField(allow_null=True)
    path = serializers.CharField(allow_null=True, allow_blank=True)
    status = serializers.ChoiceField(choices=["confirmed", "candidate", "unmatched"])
    reason = serializers.CharField()
    source_ref = SourceRefSerializer()
    relation_review = RelationDecisionSerializer(allow_null=True, read_only=True)


class FrontendCoverageSerializer(serializers.Serializer[dict[str, Any]]):
    source_files = serializers.IntegerField(min_value=0)
    parsed_files = serializers.IntegerField(min_value=0)
    syntax_failed_files = serializers.IntegerField(min_value=0)
    function_count = serializers.IntegerField(min_value=0)
    request_count = serializers.IntegerField(min_value=0)
    complete = serializers.BooleanField()
    limitations = serializers.ListField(child=serializers.CharField())


class FrontendSummarySerializer(serializers.Serializer[dict[str, Any]]):
    protocol_version = serializers.CharField()
    rule_version = serializers.CharField()
    association_rule_version = serializers.CharField()
    coverage = FrontendCoverageSerializer()
    confirmed = serializers.IntegerField(min_value=0)
    candidate = serializers.IntegerField(min_value=0)
    unmatched = serializers.IntegerField(min_value=0)


class EndpointSerializer(serializers.Serializer[dict[str, Any]]):
    index = serializers.IntegerField(min_value=0, read_only=True)
    frontend_available = serializers.BooleanField(read_only=True)
    frontend_links = FrontendLinkSerializer(many=True, read_only=True)
    method = serializers.ChoiceField(
        choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"]
    )
    path = serializers.CharField()
    path_kind = serializers.ChoiceField(choices=["django_path", "router_regex"])
    action = serializers.CharField()
    view = SymbolSerializer(allow_null=True)
    serializer = SymbolSerializer(allow_null=True)
    model = SymbolSerializer(allow_null=True)
    evidence = EvidenceSerializer(many=True)


class DiagnosticSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    message = serializers.CharField()
    severity = serializers.ChoiceField(choices=["warning"])
    source_ref = SourceRefSerializer(allow_null=True)


class CoverageSerializer(serializers.Serializer[dict[str, Any]]):
    python_files = serializers.IntegerField(min_value=0)
    parsed_files = serializers.IntegerField(min_value=0)
    syntax_failed_files = serializers.IntegerField(min_value=0)
    skipped_files = serializers.IntegerField(min_value=0)
    endpoint_count = serializers.IntegerField(min_value=0)
    diagnostic_count = serializers.IntegerField(min_value=0)
    complete = serializers.BooleanField()
    limitations = serializers.ListField(child=serializers.CharField())


class AnalysisSerializer(serializers.ModelSerializer[Analysis]):
    source_scan_id = serializers.UUIDField(read_only=True, allow_null=True)
    job_id = serializers.UUIDField(read_only=True)
    snapshot_id = serializers.UUIDField(read_only=True)
    coverage = CoverageSerializer(read_only=True)
    frontend = serializers.SerializerMethodField()

    @extend_schema_field(FrontendSummarySerializer(allow_null=True))
    def get_frontend(self, analysis: Analysis) -> dict[str, Any] | None:
        from apps.analysis.services import read_frontend

        result = read_frontend(analysis)
        if result is None:
            return None
        parser = result["parser"]
        return {
            "protocol_version": parser["protocol_version"],
            "rule_version": parser["rule_version"],
            "association_rule_version": result["association_rule_version"],
            "coverage": parser["coverage"],
            **{
                status: sum(m["status"] == status for m in result["matches"])
                for status in ("confirmed", "candidate", "unmatched")
            },
        }

    class Meta:
        model = Analysis
        fields = [
            "id",
            "job_id",
            "snapshot_id",
            "root_urlconf",
            "rule_version",
            "coverage",
            "frontend",
            "created_at",
            "source_scan_id",
        ]
        read_only_fields = fields


class EndpointPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = EndpointSerializer(many=True)


class DiagnosticPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = DiagnosticSerializer(many=True)


class GraphQuerySerializer(serializers.Serializer[dict[str, Any]]):
    root_node_id = serializers.UUIDField(required=False)
    endpoint_index = serializers.IntegerField(
        required=False, min_value=0, max_value=9999
    )
    algorithm = serializers.ChoiceField(choices=["bfs", "dfs"], default="bfs")
    max_nodes = serializers.IntegerField(
        min_value=1, max_value=MAX_QUERY_NODES, default=DEFAULT_GRAPH_NODES
    )
    max_edges = serializers.IntegerField(
        min_value=1, max_value=MAX_QUERY_EDGES, default=DEFAULT_GRAPH_EDGES
    )

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if set(data) - self.fields.keys() or any(
            len(data.getlist(key)) != 1 for key in data
        ):
            raise serializers.ValidationError(
                {"query": ["不支持未知或重复的查询参数。"]}
            )
        for key in ("root_node_id", "algorithm"):
            if key in data and not data[key]:
                raise serializers.ValidationError({key: ["查询参数不能为空。"]})
        for key in ("max_nodes", "max_edges", "endpoint_index"):
            if key in data:
                raw = data[key]
                if len(raw) > 10 or not raw.isascii() or not raw.isdecimal():
                    raise serializers.ValidationError(
                        {key: ["必须为有效范围内的 ASCII 十进制正整数。"]}
                    )
        value: dict[str, Any] = super().to_internal_value(data)
        if "endpoint_index" in value and "root_node_id" in value:
            raise serializers.ValidationError(
                {"query": ["接口视角与根节点不能同时指定。"]}
            )
        return value


class GraphEndpointSerializer(serializers.Serializer[dict[str, Any]]):
    index = serializers.IntegerField(min_value=0)
    method = EndpointSerializer().fields["method"]
    path = serializers.CharField()
    path_kind = serializers.ChoiceField(choices=["django_path", "router_regex"])
    action = serializers.CharField()
    is_candidate = serializers.BooleanField()


class GraphRequestSerializer(serializers.Serializer[dict[str, Any]]):
    method = serializers.CharField(allow_null=True)
    original_path = serializers.CharField(allow_null=True, allow_blank=True)
    path = serializers.CharField(allow_null=True, allow_blank=True)
    status = serializers.ChoiceField(choices=["confirmed", "candidate", "unmatched"])
    reason = serializers.CharField()


class GraphNodeSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(
        choices=[
            "endpoint",
            "view",
            "serializer",
            "model",
            "frontend_function",
            "frontend_request",
        ]
    )
    name = serializers.CharField()
    source_ref = SourceRefSerializer(allow_null=True)
    evidence = EvidenceSerializer(many=True)
    endpoint = GraphEndpointSerializer(allow_null=True)
    request = GraphRequestSerializer(allow_null=True, default=None)


class GraphEdgeSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    source_id = serializers.UUIDField()
    target_id = serializers.UUIDField()
    relation = serializers.ChoiceField(
        choices=[
            "route_view",
            "serializer_class",
            "meta_model",
            "direct_call",
            "contains_function",
            "contains_request",
            "callback_binding",
            "method_path_match",
            "candidate_match",
        ]
    )
    evidence = EvidenceSerializer(many=True)


class GraphSerializer(serializers.Serializer[dict[str, Any]]):
    analysis_id = serializers.UUIDField()
    snapshot_id = serializers.UUIDField()
    rule_version = serializers.CharField()
    graph_version = serializers.CharField()
    root_node_id = serializers.UUIDField(allow_null=True)
    endpoint_index = serializers.IntegerField(allow_null=True, min_value=0)
    algorithm = serializers.ChoiceField(choices=["bfs", "dfs"])
    nodes = GraphNodeSerializer(many=True)
    edges = GraphEdgeSerializer(many=True)
    relation_reviews = RelationDecisionSerializer(many=True, read_only=True)
    coverage = CoverageSerializer()
    diagnostics_url = serializers.CharField()
    total_nodes = serializers.IntegerField(min_value=0)
    total_edges = serializers.IntegerField(min_value=0)
    returned_nodes = serializers.IntegerField(min_value=0)
    returned_edges = serializers.IntegerField(min_value=0)
    truncated = serializers.BooleanField()
    truncation_reasons = serializers.ListField(
        child=serializers.ChoiceField(choices=["max_nodes", "max_edges"])
    )
