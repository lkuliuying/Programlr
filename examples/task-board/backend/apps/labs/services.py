import uuid
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.labs.models import LabSession
from apps.tasks.models import Task

CASES: dict[str, dict[str, str]] = {
    "normal": {"title": "实验任务"},
    "missing": {},
    "empty": {"title": ""},
    "whitespace": {"title": "   "},
}
VERSION = "task-board/1.0.0+request-validation/1"


def task_key(run_id: uuid.UUID, case: str) -> uuid.UUID:
    return uuid.uuid5(run_id, f"request-validation/1:{case}")


def count_tasks(run_id: uuid.UUID) -> int:
    return Task.objects.filter(
        idempotency_key__in=[task_key(run_id, case) for case in CASES]
    ).count()


def observation(run: LabSession) -> dict[str, Any]:
    return {
        "id": str(run.pk),
        "example_version": VERSION,
        "closed": run.closed,
        "record_count": count_tasks(run.pk),
        "deleted_count": run.deleted_count,
        "expires_at": run.expires_at.isoformat(),
    }


def open_run(run_id: uuid.UUID) -> LabSession:
    run, _ = LabSession.objects.get_or_create(
        pk=run_id, defaults={"expires_at": timezone.now() + timedelta(seconds=120)}
    )
    return run


def close_run(run_id: uuid.UUID) -> dict[str, Any]:
    with transaction.atomic():
        run = LabSession.objects.select_for_update().get(pk=run_id)
        if not run.closed:
            # 保留关闭记录，阻止迟到请求在清理后重新创建数据。
            deleted, _ = Task.objects.filter(
                idempotency_key__in=[task_key(run_id, case) for case in CASES]
            ).delete()
            run.closed, run.deleted_count = True, deleted
            run.save(update_fields=["closed", "deleted_count"])
        return observation(run)


def reconcile_runs() -> int:
    ids = list(
        LabSession.objects.filter(closed=False, expires_at__lte=timezone.now())
        .order_by("expires_at", "id")
        .values_list("id", flat=True)[:100]
    )
    for run_id in ids:
        close_run(run_id)
    return len(ids)
