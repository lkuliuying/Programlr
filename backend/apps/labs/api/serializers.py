from typing import Any

from rest_framework import serializers

from apps.jobs.api.serializers import JobSerializer
from apps.labs.models import LabRun
from common.serializers import StrictInputSerializer


class PredictionSerializer(StrictInputSerializer):
    status = serializers.IntegerField(min_value=100, max_value=599)
    writes = serializers.IntegerField(min_value=0, max_value=1)


class PredictionsSerializer(StrictInputSerializer):
    normal = PredictionSerializer()
    missing = PredictionSerializer()
    empty = PredictionSerializer()
    whitespace = PredictionSerializer()


class LabInputSerializer(StrictInputSerializer):
    snapshot_id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    endpoint_index = serializers.IntegerField(min_value=0, max_value=9999)
    lab_version = serializers.CharField(max_length=20)
    predictions = PredictionsSerializer()


class LabCaseSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    title = serializers.CharField()
    input = serializers.DictField(child=serializers.CharField(allow_blank=True))


class LabSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    version = serializers.CharField()
    title = serializers.CharField()
    example_version = serializers.CharField()
    description = serializers.CharField()
    cases = LabCaseSerializer(many=True)
    applicable = serializers.BooleanField()
    applicability_reason = serializers.CharField()


class LabPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = LabSerializer(many=True)


class LabResponseSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.IntegerField(min_value=100, max_value=599)
    body = serializers.DictField()


class LabObservationSerializer(serializers.Serializer[dict[str, Any]]):
    case_id = serializers.CharField()
    input = serializers.DictField(child=serializers.CharField(allow_blank=True))
    request_path = serializers.CharField()
    response = LabResponseSerializer()
    before_count = serializers.IntegerField(min_value=0, max_value=4)
    after_count = serializers.IntegerField(min_value=0, max_value=4, allow_null=True)
    elapsed_ms = serializers.IntegerField(min_value=0)
    observed_at = serializers.DateTimeField()


class LabCleanupSerializer(serializers.Serializer[dict[str, Any]]):
    status = serializers.CharField(default="pending")
    observation = serializers.DictField(allow_null=True, default=None)
    error_code = serializers.CharField(allow_null=True, default=None)


class LabRunSerializer(serializers.ModelSerializer[LabRun]):
    job = JobSerializer()
    analysis_id = serializers.UUIDField()
    snapshot_id = serializers.UUIDField(source="analysis.snapshot_id")
    definition = LabSerializer()
    predictions = PredictionsSerializer()
    observations = LabObservationSerializer(many=True)
    cleanup = LabCleanupSerializer()

    class Meta:
        model = LabRun
        fields = [
            "id",
            "job",
            "snapshot_id",
            "analysis_id",
            "endpoint_index",
            "definition",
            "predictions",
            "observations",
            "cleanup",
            "created_at",
        ]
        read_only_fields = fields


class LabRunPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = LabRunSerializer(many=True)
