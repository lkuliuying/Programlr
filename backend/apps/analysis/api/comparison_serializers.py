from typing import Any

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.analysis.api.serializers import EvidenceSerializer, SourceRefSerializer
from apps.analysis.diffs.types import FILE_CHANGE_TYPES, SEMANTIC_CHANGE_TYPES
from apps.analysis.models import SnapshotComparison, SnapshotComparisonRequest
from apps.jobs.models import Job
from common.errors import ApiProblem
from common.serializers import StrictInputSerializer


class ComparisonInputSerializer(StrictInputSerializer):
    base_snapshot_id = serializers.UUIDField()
    target_snapshot_id = serializers.UUIDField()
    base_analysis_id = serializers.UUIDField(
        required=False, allow_null=True, default=None
    )
    target_analysis_id = serializers.UUIDField(
        required=False, allow_null=True, default=None
    )

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if (data["base_analysis_id"] is None) != (data["target_analysis_id"] is None):
            raise serializers.ValidationError("两侧分析必须同时提供或同时省略。")
        return data


class FileSummarySerializer(serializers.Serializer[dict[str, Any]]):
    added = serializers.IntegerField(min_value=0)
    deleted = serializers.IntegerField(min_value=0)
    modified = serializers.IntegerField(min_value=0)
    unchanged = serializers.IntegerField(min_value=0)


class ComparisonFileSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    file_path = serializers.CharField()
    change_type = serializers.ChoiceField(choices=FILE_CHANGE_TYPES)
    base_ref = SourceRefSerializer(allow_null=True)
    target_ref = SourceRefSerializer(allow_null=True)
    base_sha256 = serializers.CharField(allow_null=True)
    target_sha256 = serializers.CharField(allow_null=True)


class ComparisonFileDetailSerializer(ComparisonFileSerializer):
    diff = serializers.CharField(allow_blank=True)
    base_ranges = SourceRefSerializer(many=True)
    target_ranges = SourceRefSerializer(many=True)


class ComparisonFilePageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ComparisonFileSerializer(many=True)


class AnalysisVersionSerializer(serializers.Serializer[dict[str, Any]]):
    analysis_id = serializers.UUIDField()
    snapshot_id = serializers.UUIDField()
    root_urlconf = serializers.CharField()
    rule_version = serializers.CharField()
    graph_version = serializers.CharField(allow_null=True)
    frontend_rule_version = serializers.CharField(allow_null=True)
    association_rule_version = serializers.CharField(allow_null=True)


class EndpointChangeSerializer(serializers.Serializer[dict[str, Any]]):
    method = serializers.CharField()
    path = serializers.CharField()
    path_kind = serializers.ChoiceField(choices=["django_path", "router_regex"])
    change_type = serializers.ChoiceField(choices=SEMANTIC_CHANGE_TYPES)
    base_indices = serializers.ListField(child=serializers.IntegerField(min_value=0))
    target_indices = serializers.ListField(child=serializers.IntegerField(min_value=0))
    changed_fields = serializers.ListField(
        child=serializers.ChoiceField(
            choices=["action", "view", "serializer", "model", "relations"]
        )
    )
    base_evidence = EvidenceSerializer(many=True)
    target_evidence = EvidenceSerializer(many=True)


class RelationChangeSerializer(serializers.Serializer[dict[str, Any]]):
    relation = serializers.CharField()
    source_name = serializers.CharField()
    target_name = serializers.CharField()
    change_type = serializers.ChoiceField(choices=SEMANTIC_CHANGE_TYPES)
    base_edge_ids = serializers.ListField(child=serializers.UUIDField())
    target_edge_ids = serializers.ListField(child=serializers.UUIDField())
    base_evidence = EvidenceSerializer(many=True)
    target_evidence = EvidenceSerializer(many=True)


class ReferenceApplicabilitySerializer(serializers.Serializer[dict[str, Any]]):
    source_ref = SourceRefSerializer()
    target_ref = SourceRefSerializer(allow_null=True)
    applicability = serializers.ChoiceField(
        choices=["unchanged", "review", "deleted", "unknown"]
    )


class ExplanationApplicabilitySerializer(serializers.Serializer[dict[str, Any]]):
    explanation_id = serializers.UUIDField()
    preview_id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    endpoint_index = serializers.IntegerField(min_value=0)
    references = ReferenceApplicabilitySerializer(many=True)
    warning = serializers.CharField(allow_null=True)


class SnapshotComparisonSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    job_id = serializers.UUIDField()
    base_snapshot_id = serializers.UUIDField()
    target_snapshot_id = serializers.UUIDField()
    base_analysis_id = serializers.UUIDField(allow_null=True)
    target_analysis_id = serializers.UUIDField(allow_null=True)
    comparison_version = serializers.CharField()
    created_at = serializers.DateTimeField()
    summary = FileSummarySerializer()
    comparability = serializers.ChoiceField(
        choices=["comparable", "files_only", "incomparable"]
    )
    comparison_notes = serializers.ListField(child=serializers.CharField())
    base_version = AnalysisVersionSerializer(allow_null=True)
    target_version = AnalysisVersionSerializer(allow_null=True)
    interfaces = EndpointChangeSerializer(many=True)
    relations = RelationChangeSerializer(many=True)
    evidence = ExplanationApplicabilitySerializer(many=True)


class ComparisonHistorySerializer(
    serializers.ModelSerializer[SnapshotComparisonRequest]
):
    project_id = serializers.UUIDField(read_only=True)
    job_id = serializers.UUIDField(read_only=True)
    base_snapshot_id = serializers.UUIDField(read_only=True)
    target_snapshot_id = serializers.UUIDField(read_only=True)
    base_analysis_id = serializers.UUIDField(read_only=True, allow_null=True)
    target_analysis_id = serializers.UUIDField(read_only=True, allow_null=True)
    job_status = serializers.ChoiceField(
        source="job.status", choices=Job.Status.choices, read_only=True
    )
    summary = serializers.SerializerMethodField()

    @extend_schema_field(FileSummarySerializer(allow_null=True))
    def get_summary(self, obj: SnapshotComparisonRequest) -> dict[str, int] | None:
        try:
            value = obj.result.summary
        except SnapshotComparison.DoesNotExist:
            return None
        if (
            not isinstance(value, dict)
            or set(value) != set(FILE_CHANGE_TYPES)
            or any(type(v) is not int or v < 0 for v in value.values())
        ):
            raise ApiProblem(
                500, "INTERNAL_ERROR", "保存的对比摘要无法通过完整性校验。"
            )
        return value

    class Meta:
        model = SnapshotComparisonRequest
        fields = [
            "id",
            "project_id",
            "job_id",
            "job_status",
            "base_snapshot_id",
            "target_snapshot_id",
            "base_analysis_id",
            "target_analysis_id",
            "summary",
            "created_at",
        ]
        read_only_fields = fields


class ComparisonHistoryPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ComparisonHistorySerializer(many=True)
