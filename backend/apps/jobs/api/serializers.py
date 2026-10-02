from typing import Any

from rest_framework import serializers

from apps.jobs.models import Job, SystemCheck


class ErrorSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField()
    request_id = serializers.CharField()


class CsrfSerializer(serializers.Serializer[dict[str, Any]]):
    csrf_token = serializers.CharField()


class EmptyCheckSerializer(serializers.Serializer[dict[str, Any]]):
    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or data:
            raise serializers.ValidationError(
                {"body": ["固定检查只接受空 JSON 对象。"]}
            )
        return {}


class SystemCheckSerializer(serializers.ModelSerializer[SystemCheck]):
    job_id = serializers.UUIDField()

    class Meta:
        model = SystemCheck
        fields = [
            "id",
            "job_id",
            "check_version",
            "database",
            "queue",
            "worker",
            "completed_at",
        ]
        read_only_fields = fields


class JobSerializer(serializers.ModelSerializer[Job]):
    snapshot_id = serializers.SerializerMethodField()
    previous_job_id = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    result_url = serializers.SerializerMethodField()
    error = ErrorSerializer(allow_null=True)

    def get_snapshot_id(self, obj: Job) -> str | None:
        return str(obj.snapshot_id) if obj.snapshot_id else None

    def get_previous_job_id(self, obj: Job) -> str | None:
        return str(obj.previous_job_id) if obj.previous_job_id else None

    def get_progress(self, obj: Job) -> dict[str, int | None] | None:
        return None

    def get_result_url(self, obj: Job) -> str | None:
        if obj.status == Job.Status.SUCCEEDED:
            if obj.kind in {
                "import",
                "analysis",
                "explanation",
                "lab",
                "snapshot_comparison",
            }:
                return obj.result_url
            return f"/api/v1/system-checks/{obj.check_result.pk}/"
        return None

    class Meta:
        model = Job
        fields = [
            "id",
            "kind",
            "snapshot_id",
            "status",
            "stage",
            "progress",
            "previous_job_id",
            "result_url",
            "error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class JobPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = JobSerializer(many=True)
