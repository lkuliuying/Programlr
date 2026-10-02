from typing import Any

from rest_framework import serializers

from apps.analysis.models import RelationReview
from common.serializers import StrictInputSerializer


class RelationReviewInputSerializer(StrictInputSerializer):
    request_id = serializers.UUIDField()
    target_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=RelationReview.Action.choices)
    expected_revision = serializers.IntegerField(min_value=0, max_value=2147483646)


class RelationReviewStateSerializer(serializers.Serializer[dict[str, Any]]):
    analysis_id = serializers.UUIDField()
    request_id = serializers.UUIDField()
    revision = serializers.IntegerField(min_value=0)
    confirmed_target_id = serializers.UUIDField(allow_null=True)
    excluded_target_ids = serializers.ListField(
        child=serializers.UUIDField(), max_length=10000
    )


class RelationDecisionSerializer(serializers.Serializer[dict[str, Any]]):
    request_id = serializers.UUIDField()
    target_id = serializers.UUIDField()
    revision = serializers.IntegerField(min_value=0)
    decision = serializers.ChoiceField(choices=["confirmed", "excluded", "undecided"])


class RelationReviewSerializer(serializers.ModelSerializer[RelationReview]):
    analysis_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = RelationReview
        fields = [
            "id",
            "analysis_id",
            "request_id",
            "target_id",
            "action",
            "revision",
            "created_at",
        ]
        read_only_fields = fields


class RelationReviewResultSerializer(serializers.Serializer[dict[str, Any]]):
    record = RelationReviewSerializer()
    state = RelationReviewStateSerializer()


class RelationReviewPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = RelationReviewSerializer(many=True)
    state = RelationReviewStateSerializer()
