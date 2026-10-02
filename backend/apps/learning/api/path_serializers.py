from typing import Any

from rest_framework import serializers

from apps.learning.api.serializers import KnowledgeCardSerializer
from apps.learning.models import AttemptReview, KnowledgeCurriculum
from common.serializers import StrictInputSerializer


class CurriculumNodeSerializer(serializers.Serializer[dict[str, Any]]):
    slug = serializers.CharField()
    card_version = serializers.CharField()


class PrerequisiteEdgeSerializer(serializers.Serializer[dict[str, Any]]):
    prerequisite = serializers.CharField()
    dependent = serializers.CharField()


class CurriculumDefinitionSerializer(serializers.Serializer[dict[str, Any]]):
    slug = serializers.CharField()
    version = serializers.CharField()
    title = serializers.CharField()
    example_version = serializers.CharField()
    review_note = serializers.CharField()
    nodes = CurriculumNodeSerializer(many=True)
    edges = PrerequisiteEdgeSerializer(many=True)
    goals = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )


class KnowledgeCurriculumSerializer(serializers.ModelSerializer[KnowledgeCurriculum]):
    definition = CurriculumDefinitionSerializer()

    class Meta:
        model = KnowledgeCurriculum
        fields = ["id", "slug", "version", "title", "definition", "content_digest"]
        read_only_fields = fields


class CurriculumPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = KnowledgeCurriculumSerializer(many=True)


class LearningPathSerializer(serializers.Serializer[dict[str, Any]]):
    snapshot_id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    endpoint_index = serializers.IntegerField(min_value=0)
    curriculum = KnowledgeCurriculumSerializer()
    goal = serializers.CharField()
    targets = serializers.ListField(child=serializers.CharField())
    order = serializers.ListField(child=serializers.CharField())
    steps = KnowledgeCardSerializer(many=True)
    applicable = serializers.BooleanField()
    applicability_reason = serializers.CharField()


class ReviewInputSerializer(StrictInputSerializer):
    attempt_id = serializers.UUIDField()
    judgement = serializers.ChoiceField(choices=["revisit", "practicing", "understood"])
    note = serializers.CharField(
        max_length=1000, allow_blank=True, trim_whitespace=False, default=""
    )


class AttemptReviewSerializer(serializers.ModelSerializer[AttemptReview]):
    attempt_id = serializers.UUIDField()
    judgement = serializers.ChoiceField(choices=["revisit", "practicing", "understood"])

    class Meta:
        model = AttemptReview
        fields = ["id", "attempt_id", "judgement", "note", "created_at"]
        read_only_fields = fields


class AttemptReviewPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = AttemptReviewSerializer(many=True)
