from typing import Any

from rest_framework import serializers

from apps.projects.archive import SOURCE_EXTENSIONS
from apps.projects.models import Project, Snapshot, SourceFile
from common.serializers import StrictInputSerializer


class ProjectInputSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(min_length=1, max_length=200, trim_whitespace=True)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if (
            not isinstance(data, dict)
            or set(data) != {"name"}
            or not isinstance(data.get("name"), str)
        ):
            raise serializers.ValidationError({"name": ["仅接受必填字符串 name。"]})
        validated: dict[str, Any] = super().to_internal_value(data)
        return validated

    def validate_name(self, value: str) -> str:
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise serializers.ValidationError("名称不能包含控制字符。")
        return value


class ImportInputSerializer(serializers.Serializer[dict[str, Any]]):
    archive = serializers.FileField(allow_empty_file=False)


class SnapshotNameInputSerializer(StrictInputSerializer):
    name = serializers.CharField(min_length=1, max_length=200, trim_whitespace=True)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        name = data.get("name") if isinstance(data, dict) else None
        if isinstance(name, str) and any(
            ord(char) < 32 or 127 <= ord(char) <= 159 for char in name
        ):
            raise serializers.ValidationError({"name": ["名称不能包含控制字符。"]})
        return super().to_internal_value(data)


class ProjectSerializer(serializers.ModelSerializer[Project]):
    class Meta:
        model = Project
        fields = ["id", "name", "created_at"]
        read_only_fields = fields


class ImportSummarySerializer(serializers.Serializer[dict[str, Any]]):
    entries = serializers.IntegerField(min_value=0)
    accepted = serializers.IntegerField(min_value=0)
    excluded = serializers.IntegerField(min_value=0)
    skipped = serializers.IntegerField(min_value=0)
    rejected = serializers.IntegerField(min_value=0)
    declared_bytes = serializers.IntegerField(min_value=0)
    extracted_bytes = serializers.IntegerField(min_value=0)
    reasons = serializers.DictField(child=serializers.IntegerField(min_value=0))


class SnapshotSerializer(serializers.ModelSerializer[Snapshot]):
    project_id = serializers.UUIDField(read_only=True)
    job_id = serializers.UUIDField(read_only=True)
    summary = ImportSummarySerializer(read_only=True)
    source_extensions = serializers.SerializerMethodField()

    def get_source_extensions(self, obj: Snapshot) -> list[str]:
        return list(SOURCE_EXTENSIONS)

    class Meta:
        model = Snapshot
        fields = [
            "id",
            "name",
            "project_id",
            "job_id",
            "summary",
            "source_extensions",
            "created_at",
        ]
        read_only_fields = fields


class SourceFileSerializer(serializers.ModelSerializer[SourceFile]):
    snapshot_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = SourceFile
        fields = [
            "id",
            "snapshot_id",
            "file_path",
            "sha256",
            "size_bytes",
            "line_count",
            "encoding",
        ]
        read_only_fields = fields


class SourceContentSerializer(SourceFileSerializer):
    start_line = serializers.IntegerField(min_value=1)
    end_line = serializers.IntegerField(min_value=1)
    content = serializers.CharField(allow_blank=True, trim_whitespace=False)

    class Meta(SourceFileSerializer.Meta):
        fields = [
            *SourceFileSerializer.Meta.fields,
            "start_line",
            "end_line",
            "content",
        ]


class PageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)


class ProjectPageSerializer(PageSerializer):
    results = ProjectSerializer(many=True)


class SnapshotPageSerializer(PageSerializer):
    results = SnapshotSerializer(many=True)


class SourceFilePageSerializer(PageSerializer):
    results = SourceFileSerializer(many=True)
