"""用户自我判断追加保存，不改标准答案或自动认定掌握程度。"""

import uuid
from typing import Any

from django.shortcuts import get_object_or_404

from apps.learning.content import content_digest
from apps.learning.models import AttemptReview, ExerciseAttempt
from common.errors import Conflict


def submit_review(key: uuid.UUID, values: dict[str, Any]) -> tuple[AttemptReview, bool]:
    digest = content_digest({**values, "attempt_id": str(values["attempt_id"])})
    existing = AttemptReview.objects.filter(idempotency_key=key).first()
    if existing is not None:
        if existing.request_digest != digest:
            raise Conflict
        return existing, False
    attempt = get_object_or_404(ExerciseAttempt, pk=values["attempt_id"])
    record, created = AttemptReview.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "attempt": attempt,
            "request_digest": digest,
            "judgement": values["judgement"],
            "note": values["note"],
        },
    )
    if record.request_digest != digest:
        raise Conflict
    return record, created
