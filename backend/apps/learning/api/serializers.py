from typing import Any, cast

from rest_framework import serializers

from apps.analysis.api.serializers import SourceRefSerializer
from apps.learning.models import Exercise, ExerciseAttempt, KnowledgeCard
from apps.learning.services import applicability
from common.serializers import StrictInputSerializer


class KnowledgeCardSerializer(serializers.ModelSerializer[KnowledgeCard]):
    class Meta:
        model = KnowledgeCard
        fields = [
            "id",
            "slug",
            "version",
            "title",
            "body",
            "applicability",
            "review_note",
        ]
        read_only_fields = fields


class ExerciseOptionSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]


class ExerciseSerializer(serializers.ModelSerializer[Exercise]):
    example_version = serializers.CharField(source="example_id")
    kind = serializers.ChoiceField(
        choices=["flow_order", "error_prediction", "code_location"]
    )
    options = ExerciseOptionSerializer(many=True)
    applicable = serializers.SerializerMethodField()
    applicability_reason = serializers.SerializerMethodField()

    def suitability(self, obj: Exercise) -> tuple[bool, str]:
        cache = cast(dict[str, Any], self.context).setdefault("applicability_cache", {})
        if obj.pk not in cache:
            cache[obj.pk] = applicability(
                obj, self.context["analysis"], self.context["endpoint_index"]
            )
        value: tuple[bool, str] = cache[obj.pk]
        return value

    def get_applicable(self, obj: Exercise) -> bool:
        return self.suitability(obj)[0]

    def get_applicability_reason(self, obj: Exercise) -> str:
        return self.suitability(obj)[1]

    class Meta:
        model = Exercise
        fields = [
            "id",
            "slug",
            "version",
            "answer_version",
            "example_version",
            "kind",
            "question",
            "hint",
            "options",
            "review_note",
            "applicable",
            "applicability_reason",
        ]
        read_only_fields = fields


class AttemptInputSerializer(StrictInputSerializer):
    snapshot_id = serializers.UUIDField()
    exercise_id = serializers.UUIDField()
    exercise_version = serializers.CharField(max_length=40, trim_whitespace=False)
    analysis_id = serializers.UUIDField()
    endpoint_index = serializers.IntegerField(min_value=0, max_value=9999)
    answer = serializers.JSONField()
    hint_used = serializers.BooleanField()
    previous_attempt_id = serializers.UUIDField(required=False, allow_null=True)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        # 可空的新关联按旧请求的省略语义处理，保留旧幂等摘要。
        if isinstance(data, dict) and data.get("previous_attempt_id") is None:
            data = {
                key: value
                for key, value in data.items()
                if key != "previous_attempt_id"
            }
        return super().to_internal_value(data)


class AttemptFeedbackSerializer(serializers.Serializer[dict[str, Any]]):
    expected_answer = serializers.JSONField()
    explanation = serializers.CharField()
    source_refs = SourceRefSerializer(many=True)


class ExerciseAttemptSerializer(serializers.ModelSerializer[ExerciseAttempt]):
    exercise_id = serializers.UUIDField()
    exercise_version = serializers.CharField(source="exercise.version")
    answer_version = serializers.CharField(source="exercise.answer_version")
    example_version = serializers.CharField(source="exercise.example_id")
    question = serializers.CharField(source="exercise.question")
    kind = serializers.CharField(source="exercise.kind")
    snapshot_id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    feedback = AttemptFeedbackSerializer()
    previous_attempt_id = serializers.UUIDField(allow_null=True)

    class Meta:
        model = ExerciseAttempt
        fields = [
            "id",
            "exercise_id",
            "exercise_version",
            "answer_version",
            "example_version",
            "question",
            "kind",
            "snapshot_id",
            "analysis_id",
            "endpoint_index",
            "answer",
            "hint_used",
            "correct",
            "feedback",
            "created_at",
            "previous_attempt_id",
        ]
        read_only_fields = fields


class KnowledgeCardPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = KnowledgeCardSerializer(many=True)


class ExercisePageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ExerciseSerializer(many=True)


class ExerciseAttemptPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ExerciseAttemptSerializer(many=True)
