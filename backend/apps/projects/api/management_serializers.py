from typing import Any

from rest_framework import serializers

from apps.jobs.api.serializers import JobSerializer
from apps.projects.api.serializers import (
    PageSerializer,
    ProjectSerializer,
    SnapshotSerializer,
)


class ProjectTechnologySerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField()
    evidence_kind = serializers.ChoiceField(
        choices=["language", "declaration", "usage"]
    )


class ProjectSummarySerializer(serializers.Serializer[dict[str, Any]]):
    project = ProjectSerializer()
    snapshot_count = serializers.IntegerField(min_value=0)
    latest_snapshot = SnapshotSerializer(allow_null=True)
    last_imported_at = serializers.DateTimeField(allow_null=True)
    technologies = ProjectTechnologySerializer(many=True)
    root_count = serializers.IntegerField(min_value=0, allow_null=True)
    root_path = serializers.CharField(allow_null=True)


class ProjectManagementPageSerializer(PageSerializer):
    results = ProjectSummarySerializer(many=True)
    technologies = serializers.ListField(child=serializers.CharField())


class ProjectActivityEventSerializer(serializers.Serializer[dict[str, Any]]):
    at = serializers.DateTimeField()
    result = serializers.CharField()
    stage = serializers.CharField(allow_blank=True)
    error_code = serializers.CharField(allow_blank=True)


class ProjectActivityStageSerializer(serializers.Serializer[dict[str, Any]]):
    kind = serializers.ChoiceField(choices=["import", "source_scan", "analysis"])
    job = JobSerializer()
    events = ProjectActivityEventSerializer(many=True)


class ProjectActivityItemSerializer(serializers.Serializer[dict[str, Any]]):
    project = ProjectSerializer()
    snapshot = SnapshotSerializer(allow_null=True)
    status = serializers.ChoiceField(
        choices=[
            "importing",
            "scanning",
            "needs_root",
            "no_root",
            "analyzing",
            "ready",
            "failed",
            "pending",
        ]
    )
    root_count = serializers.IntegerField(min_value=0, allow_null=True)
    endpoint_count = serializers.IntegerField(min_value=0, allow_null=True)
    stages = ProjectActivityStageSerializer(many=True)


class ProjectActivitySerializer(serializers.Serializer[dict[str, Any]]):
    active = ProjectActivityItemSerializer(many=True)
    recent = ProjectActivityItemSerializer(many=True)


class SnapshotSearchResultSerializer(serializers.Serializer[dict[str, Any]]):
    snapshot = SnapshotSerializer()
    project = ProjectSerializer()


class SnapshotSearchPageSerializer(PageSerializer):
    results = SnapshotSearchResultSerializer(many=True)
