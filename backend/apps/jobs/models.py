import uuid

from django.db import models


class Job(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=32, default="system_check")
    idempotency_key = models.UUIDField()
    scope = models.CharField(max_length=80, default="system_checks_create")
    snapshot_id = models.UUIDField(null=True)
    previous_job = models.ForeignKey(
        "self", null=True, on_delete=models.PROTECT, related_name="retries"
    )
    result_url = models.CharField(max_length=200, null=True)
    request_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status, default=Status.QUEUED)
    stage = models.CharField(max_length=32, default="queued")
    claim_id = models.UUIDField(null=True)
    expires_at = models.DateTimeField(db_index=True)
    error = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "idempotency_key"], name="job_scope_key_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["queued", "running", "succeeded", "failed"]
                ),
                name="job_valid_status",
            ),
        ]


class SystemCheck(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField(
        Job, on_delete=models.PROTECT, related_name="check_result"
    )
    check_version = models.CharField(max_length=16, default="1")
    database = models.CharField(max_length=16, default="passed")
    queue = models.CharField(max_length=16, default="passed")
    worker = models.CharField(max_length=16, default="passed")
    completed_at = models.DateTimeField(auto_now_add=True)
