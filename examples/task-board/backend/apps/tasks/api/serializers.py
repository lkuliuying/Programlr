from typing import Any

from rest_framework import serializers

from apps.tasks.models import Task


class TaskSerializer(serializers.ModelSerializer[Task]):
    title = serializers.CharField(
        required=True,
        allow_blank=False,
        allow_null=False,
        max_length=200,
        trim_whitespace=True,
    )

    class Meta:
        model = Task
        fields = ["id", "title", "created_at"]
        read_only_fields = ["id", "created_at"]

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise serializers.ValidationError({"body": ["必须为 JSON 对象。"]})
        if set(data) - {"title"}:
            raise serializers.ValidationError({"body": ["只允许 title 字段。"]})
        if "title" in data and not isinstance(data["title"], str):
            raise serializers.ValidationError({"title": ["标题必须为字符串。"]})
        values: dict[str, Any] = super().to_internal_value(data)
        return values


class TaskPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = TaskSerializer(many=True)


class CsrfSerializer(serializers.Serializer[dict[str, Any]]):
    csrf_token = serializers.CharField()


class ErrorSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField()
    request_id = serializers.CharField()
