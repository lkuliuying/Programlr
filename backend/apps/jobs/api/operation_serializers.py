from typing import Any

from django.db.models import Q
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.jobs.api.serializers import JobSerializer
from apps.jobs.models import MAX_DISPLAY_ID, DeletionRequest, OperationLog
from apps.jobs.operation_capabilities import RETRY_ACTIONS
from common.serializers import StrictInputSerializer


class DeletionInputSerializer(StrictInputSerializer):
    confirmation_digest = serializers.RegexField(r"^[0-9a-f]{64}$")


class DeletionScopeSerializer(serializers.Serializer[dict[str, Any]]):
    snapshots = serializers.IntegerField(min_value=0)
    files = serializers.IntegerField(min_value=0)
    analyses = serializers.IntegerField(min_value=0)
    source_scans = serializers.IntegerField(min_value=0)
    explanations = serializers.IntegerField(min_value=0)
    attempts = serializers.IntegerField(min_value=0)
    lab_runs = serializers.IntegerField(min_value=0)
    comparisons = serializers.IntegerField(min_value=0)


class DeletionPreviewSerializer(serializers.Serializer[dict[str, Any]]):
    target_type = serializers.ChoiceField(choices=["project", "snapshot"])
    target_id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    object_name = serializers.CharField(allow_blank=True)
    scope = DeletionScopeSerializer()
    confirmation_digest = serializers.CharField()
    can_delete = serializers.BooleanField()
    receiving = serializers.BooleanField()
    busy_jobs = JobSerializer(many=True)


class OperationLogSerializer(serializers.ModelSerializer[OperationLog]):
    retry_action = serializers.ChoiceField(choices=RETRY_ACTIONS, read_only=True)
    retry_reason = serializers.SerializerMethodField()
    project_available = serializers.BooleanField(read_only=True)
    display_id = serializers.IntegerField(
        read_only=True, min_value=1, max_value=MAX_DISPLAY_ID
    )
    job = JobSerializer(allow_null=True)
    job_id = serializers.UUIDField(read_only=True, allow_null=True)
    result_deleted = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()
    started_at = serializers.DateTimeField(source="created_at", read_only=True)
    ended_at = serializers.DateTimeField(read_only=True, allow_null=True)

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_events(self, obj: OperationLog) -> list[dict[str, Any]]:
        # 损坏的历史事件不应阻断摘要读取；有效对象原样保留，不回写数据。
        if not isinstance(obj.events, list):
            return []
        return [item for item in obj.events if isinstance(item, dict)]

    def get_result_deleted(self, obj: OperationLog) -> bool:
        if obj.job is not None and obj.job.result_deleted_at is not None:
            return True
        if hasattr(obj, "_target_deleted"):
            return bool(obj._target_deleted)
        return DeletionRequest.objects.filter(
            Q(target_type="snapshot", target_id=obj.snapshot_id)
            | Q(target_type="project", target_id=obj.project_id),
            completed_at__isnull=False,
        ).exists()

    def get_retry_reason(self, obj: OperationLog) -> str:
        action = getattr(obj, "retry_action", "none")
        if action != "none":
            return {
                "direct": "可显式重新提交任务。",
                "upload_zip": "重试前需要重新选择原 ZIP 文件。",
                "select_folder": "重试前需要重新选择原目录。",
                "reconfirm_explanation": "请返回讲解预览，重新确认外发范围后提交。",
                "continue_cleanup": "可继续清理已隔离的内部副本。",
            }[action]
        if obj.job is None:
            return "此记录未创建任务，请返回原操作检查输入。"
        if obj.job.kind in {"system_check", "lab", "snapshot_comparison"}:
            return "此功能已退役，历史结果保持只读。"
        if self.get_result_deleted(obj):
            return "任务所属源码及结果已清理，不能重试。"
        if obj.result != "failed" or obj.job.status != "failed":
            return "仅当前失败的操作记录可恢复任务。"
        return "原输入或当前执行资格不可用，请返回项目检查状态。"

    class Meta:
        model = OperationLog
        fields = [
            "id",
            "display_id",
            "operation",
            "result",
            "request_id",
            "project_id",
            "project_name",
            "snapshot_id",
            "object_name",
            "source_kind",
            "job_id",
            "job",
            "error_code",
            "events",
            "result_deleted",
            "started_at",
            "ended_at",
            "created_at",
            "updated_at",
            "retry_action",
            "retry_reason",
            "project_available",
        ]
        read_only_fields = fields


class OperationLogPageSerializer(serializers.Serializer[dict[str, Any]]):
    count = serializers.IntegerField(min_value=0)
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = OperationLogSerializer(many=True)


class OperationWindowSerializer(serializers.Serializer[dict[str, Any]]):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class OperationTrendSerializer(serializers.Serializer[dict[str, Any]]):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    count = serializers.IntegerField(min_value=0)
    failed_count = serializers.IntegerField(min_value=0)


class OperationStatisticsSerializer(serializers.Serializer[dict[str, Any]]):
    as_of = serializers.DateTimeField()
    count = serializers.IntegerField(min_value=0)
    failed_count = serializers.IntegerField(min_value=0)
    active_count = serializers.IntegerField(min_value=0)
    retryable_count = serializers.IntegerField(min_value=0)
    recent_success_rate = serializers.FloatField(
        allow_null=True, min_value=0, max_value=100
    )
    previous_success_rate = serializers.FloatField(
        allow_null=True, min_value=0, max_value=100
    )
    success_rate_change_pp = serializers.FloatField(allow_null=True)
    recent_window = OperationWindowSerializer()
    previous_window = OperationWindowSerializer()
    trend = OperationTrendSerializer(many=True)


class RelatedOperationLogSerializer(OperationLogSerializer):
    relation = serializers.CharField(read_only=True)

    class Meta(OperationLogSerializer.Meta):
        fields = [*OperationLogSerializer.Meta.fields, "relation"]
        read_only_fields = fields


class RelatedOperationLogPageSerializer(OperationLogPageSerializer):
    results = RelatedOperationLogSerializer(many=True)
