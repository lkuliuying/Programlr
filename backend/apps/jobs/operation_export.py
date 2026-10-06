"""只导出有界日志摘要，避免原始事件或错误详情进入可下载文件。"""

import csv
import io
import re

from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils import timezone

from apps.jobs.models import OperationLog
from apps.jobs.operation_queries import OPERATION_LABELS, RESULT_LABELS
from common.errors import ApiProblem

MAX_EXPORT_ROWS = 10_000
MAX_EXPORT_BYTES = 10 * 1024 * 1024
FIELDS = (
    "display_id",
    "operation",
    "project_name",
    "object_name",
    "result",
    "source_kind",
    "created_at",
    "ended_at",
    "error_code",
    "job__result_deleted_at",
    "_target_deleted",
)


def csv_text(value: str) -> str:
    # 引号只能转义 CSV 结构，不能阻止表格软件把文本作为公式执行。
    if re.match(r"^[\s\x00-\x1f]*[=+@-]", value) or value.startswith(
        ("\t", "\r", "\n")
    ):
        return "'" + value
    return value


def export_operations(logs: QuerySet[OperationLog]) -> HttpResponse:
    rows = list(logs.values(*FIELDS)[: MAX_EXPORT_ROWS + 1])
    if len(rows) > MAX_EXPORT_ROWS:
        raise ApiProblem(
            413,
            "EXPORT_LIMIT_EXCEEDED",
            "匹配记录超过 10000 条，请缩小筛选范围后导出。",
        )
    output = bytearray(b"\xef\xbb\xbf")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n", quoting=csv.QUOTE_ALL)

    def append(values: list[str]) -> None:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow([csv_text(value) for value in values])
        encoded = buffer.getvalue().encode("utf-8")
        if len(output) + len(encoded) > MAX_EXPORT_BYTES:
            raise ApiProblem(
                413,
                "EXPORT_LIMIT_EXCEEDED",
                "导出内容超过 10 MiB，请缩小筛选范围后重试。",
            )
        output.extend(encoded)

    append(
        [
            "日志编号",
            "操作类型",
            "项目",
            "操作对象",
            "结果",
            "来源",
            "开始时间",
            "结束时间",
            "耗时（秒）",
            "错误码",
            "结果已删除",
        ]
    )
    for row in rows:
        start, end = row["created_at"], row["ended_at"]
        duration = (
            str(round((end - start).total_seconds(), 3)) if end and end >= start else ""
        )
        append(
            [
                str(row["display_id"]),
                OPERATION_LABELS.get(row["operation"], row["operation"]),
                row["project_name"],
                row["object_name"],
                RESULT_LABELS.get(row["result"], row["result"]),
                row["source_kind"],
                start.isoformat(),
                end.isoformat() if end else "",
                duration,
                row["error_code"],
                "是"
                if row["job__result_deleted_at"] or row["_target_deleted"]
                else "否",
            ]
        )
    response = HttpResponse(bytes(output), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="operation-logs-{timezone.now():%Y%m%dT%H%M%SZ}.csv"'
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response
