from typing import Any

from rest_framework import serializers

from apps.analysis.api.serializers import DiagnosticSerializer, SourceRefSerializer
from apps.learning.api.serializers import KnowledgeCardSerializer


class KnowledgeHitSerializer(serializers.Serializer[dict[str, Any]]):
    concept_key = serializers.CharField()
    card_slug = serializers.CharField(allow_null=True)
    card_version = serializers.CharField(allow_null=True)
    rule_id = serializers.CharField()
    source_ref = SourceRefSerializer()


class KnowledgeHitPreviewSerializer(serializers.Serializer[dict[str, Any]]):
    reason = serializers.CharField()
    source_ref = SourceRefSerializer()


class KnowledgePackageSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField()
    kind = serializers.ChoiceField(
        choices=["local", "stdlib", "third_party", "unknown"]
    )
    distribution = serializers.CharField(allow_null=True)


class MatchedKnowledgeCardSerializer(serializers.Serializer[dict[str, Any]]):
    concept_key = serializers.CharField()
    card = KnowledgeCardSerializer(allow_null=True)
    mapped = serializers.BooleanField()
    hit_count = serializers.IntegerField(min_value=1)
    hits = KnowledgeHitPreviewSerializer(many=True)
    package = KnowledgePackageSerializer(allow_null=True)


class KnowledgeCoverageSerializer(serializers.Serializer[dict[str, Any]]):
    python_files = serializers.IntegerField()
    parsed_files = serializers.IntegerField()
    syntax_failed_files = serializers.IntegerField()
    hit_count = serializers.IntegerField()
    package_count = serializers.IntegerField()
    complete = serializers.BooleanField()
    truncated = serializers.BooleanField()


class SnapshotKnowledgePageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    scan_id = serializers.UUIDField()
    rule_version = serializers.CharField()
    coverage = KnowledgeCoverageSerializer()
    diagnostics = DiagnosticSerializer(many=True)
    results = MatchedKnowledgeCardSerializer(many=True)


class KnowledgeHitPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    scan_id = serializers.UUIDField()
    rule_version = serializers.CharField()
    results = KnowledgeHitSerializer(many=True)
