"""列表、统计和导出共享筛选及排序，避免不同入口计算不同记录范围。"""

import uuid
from dataclasses import dataclass
from typing import Any

from django.db.models import F, Q, QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from apps.jobs.models import OperationLog
from apps.jobs.operation_times import operation_log_queryset

OPERATION_LABELS = {
    "import": "源码导入",
    "source_scan": "源码扫描",
    "analysis": "接口分析",
    "explanation": "模型讲解",
    "delete": "永久删除",
    "delete_project": "删除项目",
    "delete_snapshot": "删除快照",
    "retry": "任务重试",
    "lab": "历史实验",
    "snapshot_comparison": "历史对比",
    "system_check": "历史检查",
}
RESULT_LABELS = {
    "submitted": "已提交",
    "accepted": "已接收",
    "running": "处理中",
    "succeeded": "成功",
    "failed": "失败",
    "rejected": "前置拒绝",
    "replayed": "幂等重放",
}
ACTIVE_RESULTS = ("submitted", "accepted", "running")
FILTER_NAMES = {
    "project_id",
    "operation",
    "result",
    "started_after",
    "started_before",
    "ended_after",
    "ended_before",
    "q",
    "view",
    "ordering",
}


@dataclass(frozen=True)
class OperationQuery:
    logs: QuerySet[OperationLog]
    base: QuerySet[OperationLog]
    filters: dict[str, str]


def read_operation_query(request: Request, *, export: bool = False) -> OperationQuery:
    allowed = FILTER_NAMES | (set() if export else {"page", "page_size"})
    if set(request.query_params) - allowed:
        raise ValidationError({"query": ["不支持此查询参数。"]})
    filters: dict[str, str] = {}
    orm: dict[str, Any] = {}
    for name in FILTER_NAMES:
        if name not in request.query_params:
            continue
        value = request.query_params[name]
        if len(request.query_params.getlist(name)) != 1 or (not value and name != "q"):
            raise ValidationError({name: ["筛选值必须唯一且非空。"]})
        if name == "q":
            if len(value) > 200 or "\x00" in value:
                raise ValidationError({name: ["搜索文本不能超过 200 字符或包含 NUL。"]})
            value = value.strip()
        elif name == "project_id":
            try:
                if str(uuid.UUID(value)) != value:
                    raise ValueError
            except ValueError:
                raise ValidationError({name: ["项目标识必须为规范 UUID。"]}) from None
            orm[name] = value
        elif name.startswith(("started_", "ended_")):
            try:
                parsed = parse_datetime(value)
            except ValueError:
                parsed = None
            if parsed is None or timezone.is_naive(parsed):
                raise ValidationError({name: ["时间必须为带时区的 ISO 8601。"]})
            field = "created_at" if name.startswith("started_") else "ended_at"
            orm[f"{field}__{'gte' if name.endswith('_after') else 'lte'}"] = parsed
        elif name == "operation":
            if value not in OPERATION_LABELS:
                raise ValidationError({name: ["操作类型不受支持。"]})
            orm[name] = value
        elif name == "result" and value not in RESULT_LABELS:
            raise ValidationError({name: ["操作结果不受支持。"]})
        elif name == "view" and value not in {"all", "failed", "active", "retryable"}:
            raise ValidationError({name: ["日志视图不受支持。"]})
        elif name == "ordering" and value not in {
            "started_at",
            "-started_at",
            "ended_at",
            "-ended_at",
        }:
            raise ValidationError({name: ["日志排序不受支持。"]})
        filters[name] = value
    if filters.get("result") and filters.get("view", "all") != "all":
        raise ValidationError({"view": ["结果条件不能与快捷视图同时使用。"]})
    for field, parameter in (
        ("created_at", "started_before"),
        ("ended_at", "ended_before"),
    ):
        lower, upper = orm.get(f"{field}__gte"), orm.get(f"{field}__lte")
        if lower is not None and upper is not None and lower > upper:
            raise ValidationError({parameter: ["时间上界不能早于下界。"]})
    base = operation_log_queryset().filter(**orm)
    text = filters.get("q")
    if text:
        matching = [
            key
            for key, label in OPERATION_LABELS.items()
            if text.casefold() in label.casefold()
        ]
        base = base.filter(
            Q(project_name__icontains=text)
            | Q(object_name__icontains=text)
            | Q(operation__icontains=text)
            | Q(operation__in=matching)
        )
    logs = base
    if filters.get("result"):
        logs = logs.filter(result=filters["result"])
    view = filters.get("view", "all")
    if view == "failed":
        logs = logs.filter(result="failed")
    elif view == "active":
        logs = logs.filter(result__in=ACTIVE_RESULTS)
    elif view == "retryable":
        logs = logs.exclude(Q(retry_action="none"))
    order = filters.get("ordering", "-started_at")
    field = "created_at" if order.lstrip("-") == "started_at" else "ended_at"
    direction = (
        F(field).desc(nulls_last=True)
        if order.startswith("-")
        else F(field).asc(nulls_last=True)
    )
    logs = logs.order_by(
        direction, "-display_id" if order.startswith("-") else "display_id"
    )
    return OperationQuery(logs=logs, base=base, filters=filters)
