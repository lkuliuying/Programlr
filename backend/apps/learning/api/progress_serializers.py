from typing import Any

from rest_framework import serializers

from common.serializers import StrictInputSerializer


class CurriculumProgressCardSerializer(serializers.Serializer[dict[str, Any]]):
    card_id = serializers.UUIDField()
    slug = serializers.CharField()
    version = serializers.CharField()
    title = serializers.CharField()
    completed = serializers.BooleanField()


class CurriculumProgressSerializer(serializers.Serializer[dict[str, Any]]):
    curriculum_id = serializers.UUIDField()
    version = serializers.CharField()
    completed_count = serializers.IntegerField(min_value=0)
    total_count = serializers.IntegerField(min_value=0)
    cards = CurriculumProgressCardSerializer(many=True)


class CurriculumProgressInputSerializer(StrictInputSerializer):
    completed = serializers.BooleanField()
