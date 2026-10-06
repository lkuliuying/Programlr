"""保留既有通知历史查询，已读写入入口已经退役。"""

from datetime import datetime
from typing import Any

from django.db.models import Exists, OuterRef, QuerySet

from apps.jobs.models import Job, NotificationRead, NotificationReadState
from common.retirement import retired_feature


def read_through() -> datetime | None:
    return (
        NotificationReadState.objects.filter(pk=1)
        .values_list("read_through", flat=True)
        .first()
    )


def notification_jobs(as_of: datetime) -> QuerySet[Job]:
    return (
        Job.objects.filter(
            status__in=[Job.Status.SUCCEEDED, Job.Status.FAILED], updated_at__lte=as_of
        )
        .select_related("check_result")
        .annotate(
            notification_read=Exists(
                NotificationRead.objects.filter(job_id=OuterRef("pk"))
            )
        )
        .order_by("-updated_at", "-id")
    )


def unread_count(as_of: datetime, watermark: datetime | None) -> int:
    unread = notification_jobs(as_of).filter(notificationread__isnull=True)
    if watermark is not None:
        unread = unread.filter(updated_at__gt=watermark)
    return unread.count()


def notification(job: Job, watermark: datetime | None) -> dict[str, Any]:
    return {
        "job": job,
        "read": bool(getattr(job, "notification_read", False))
        or (watermark is not None and job.updated_at <= watermark),
    }


def mark_notification(job_id: Any) -> dict[str, Any]:
    retired_feature("notification")


def advance_read_through(value: datetime) -> dict[str, Any]:
    retired_feature("notification")
