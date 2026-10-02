from typing import Any

from rest_framework import serializers

from apps.jobs.api.serializers import JobSerializer
from apps.labs.models import SystemLabRun
from common.serializers import StrictInputSerializer


class SystemPredictionsSerializer(StrictInputSerializer):
    first = serializers.BooleanField()
    second = serializers.BooleanField()


class SystemLabInputSerializer(StrictInputSerializer):
    snapshot_id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    endpoint_index = serializers.IntegerField(min_value=0, max_value=9999)
    lab_version = serializers.CharField(max_length=20, trim_whitespace=False)
    predictions = SystemPredictionsSerializer()


class SystemLabCaseSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    title = serializers.CharField()
    prediction_label = serializers.CharField()


class SystemLabSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    version = serializers.CharField()
    title = serializers.CharField()
    example_version = serializers.CharField()
    program_digest = serializers.CharField()
    description = serializers.CharField()
    cases = SystemLabCaseSerializer(many=True)
    applicable = serializers.BooleanField()
    applicability_reason = serializers.CharField()


class SystemLabPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = SystemLabSerializer(many=True)


class SystemObservationSerializer(serializers.Serializer[dict[str, Any]]):
    case_id = serializers.ChoiceField(choices=["first", "second"])
    status = serializers.ChoiceField(choices=["observed", "unavailable", "invalid"])
    hostname = serializers.CharField(allow_null=True)
    addresses = serializers.ListField(child=serializers.CharField(), max_length=8)
    connected = serializers.BooleanField(allow_null=True)
    pid = serializers.IntegerField(min_value=1, allow_null=True)
    return_code = serializers.IntegerField(allow_null=True)
    stdout = serializers.CharField(allow_blank=True, max_length=4096)
    timed_out = serializers.BooleanField()
    reaped = serializers.BooleanField(allow_null=True)
    error_code = serializers.CharField(allow_null=True)
    elapsed_ms = serializers.IntegerField(min_value=0)
    observed_at = serializers.DateTimeField()


class SystemCleanupSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.ChoiceField(
        choices=["pending", "completed", "unconfirmed"], default="pending"
    )
    error_code = serializers.CharField(allow_null=True, default=None)


class SystemLabRunSerializer(serializers.ModelSerializer[SystemLabRun]):
    job = JobSerializer()
    analysis_id = serializers.UUIDField()
    snapshot_id = serializers.UUIDField(source="analysis.snapshot_id")
    definition = SystemLabSerializer()
    predictions = SystemPredictionsSerializer()
    observations = SystemObservationSerializer(many=True)
    cleanup = SystemCleanupSerializer()

    class Meta:
        model = SystemLabRun
        fields = [
            "id",
            "job",
            "snapshot_id",
            "analysis_id",
            "endpoint_index",
            "lab_id",
            "definition",
            "predictions",
            "observations",
            "cleanup",
            "created_at",
        ]
        read_only_fields = fields


class SystemLabRunPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = SystemLabRunSerializer(many=True)
