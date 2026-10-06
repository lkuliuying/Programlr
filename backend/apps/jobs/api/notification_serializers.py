from datetime import datetime
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from apps.jobs.api.serializers import JobSerializer
from apps.jobs.models import Job
from apps.jobs.notifications import notification
from common.serializers import StrictInputSerializer


class NotificationSerializer(serializers.Serializer[dict[str, Any]]):
    job = JobSerializer()
    read = serializers.BooleanField()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        if isinstance(instance, Job):
            instance = notification(instance, self.context.get("read_through"))
        return super().to_representation(instance)


class NotificationPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = NotificationSerializer(many=True)
    unread_count = serializers.IntegerField(min_value=0)
    as_of = serializers.DateTimeField()
    read_through = serializers.DateTimeField(allow_null=True)


class NotificationReadInputSerializer(StrictInputSerializer):
    read = serializers.BooleanField()

    def validate_read(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("单条通知仅接受 read:true。")
        return value


class NotificationReadStateInputSerializer(StrictInputSerializer):
    read_through = serializers.CharField(max_length=64, trim_whitespace=False)

    def validate_read_through(self, value: str) -> datetime:
        try:
            parsed = parse_datetime(value)
        except ValueError:
            parsed = None
        if parsed is None or timezone.is_naive(parsed):
            raise serializers.ValidationError("必须为带时区的 ISO 8601 日期时间。")
        return parsed


class NotificationReadStateSerializer(serializers.Serializer[dict[str, Any]]):
    read_through = serializers.DateTimeField()
    unread_count = serializers.IntegerField(min_value=0)
    as_of = serializers.DateTimeField()
