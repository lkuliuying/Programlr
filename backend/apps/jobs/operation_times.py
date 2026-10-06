"""从已有审计事件派生操作时间，不修改日志或任务的持久记录。"""

from django.db.models import DateTimeField, Func, QuerySet

from apps.jobs.models import OperationLog


class OperationEndedAt(Func):
    # 首个有效终态固定结束时间；重放只描述本次响应，不借用原任务的完成时间。
    template = r"""(
        SELECT CASE WHEN log_time_source.result IN
            ('succeeded', 'failed', 'rejected', 'replayed') THEN (
            SELECT candidate.ended_at
            FROM (
                SELECT CASE WHEN
                    jsonb_typeof(entry.value) = 'object'
                    AND jsonb_typeof(entry.value -> 'at') = 'string'
                    AND entry.value ->> 'at' ~
                        '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|[+-][0-9]{2}:[0-9]{2})$'
                    AND pg_input_is_valid(
                        entry.value ->> 'at', 'timestamp with time zone'
                    )
                    THEN (entry.value ->> 'at')::timestamp with time zone
                    ELSE NULL END AS ended_at,
                    entry.event_order
                FROM jsonb_array_elements(
                    CASE WHEN jsonb_typeof(log_time_source.events) = 'array'
                        THEN log_time_source.events ELSE '[]'::jsonb END
                ) WITH ORDINALITY AS entry(value, event_order)
                WHERE CASE WHEN log_time_source.result = 'replayed'
                    THEN entry.value ->> 'result' =
                        CASE WHEN log_time_source.request_id <> ''
                            THEN 'response' ELSE 'replayed' END
                    ELSE entry.value ->> 'result' IN
                        ('succeeded', 'failed', 'rejected')
                    END
            ) AS candidate
            WHERE candidate.ended_at >=
                TIMESTAMP WITH TIME ZONE '0001-01-01T00:00:00Z'
                AND candidate.ended_at <=
                    TIMESTAMP WITH TIME ZONE '9999-12-31T23:59:59.999999Z'
            ORDER BY candidate.event_order
            LIMIT 1
        ) ELSE NULL END
        FROM (VALUES (%(expressions)s))
            AS log_time_source(result, request_id, events)
    )"""

    def __init__(self) -> None:
        super().__init__("result", "request_id", "events", output_field=DateTimeField())


def operation_log_queryset() -> QuerySet[OperationLog]:
    from apps.jobs.operation_capabilities import annotate_operation_capabilities

    return annotate_operation_capabilities(
        OperationLog.objects.select_related("job", "job__check_result").annotate(
            ended_at=OperationEndedAt()
        )
    )
