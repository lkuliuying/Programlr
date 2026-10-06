import uuid

from django.db import models
from django.db.models.expressions import RawSQL

MAX_DISPLAY_ID = 9007199254740991


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
    parent_job = models.ForeignKey(
        "self", null=True, on_delete=models.PROTECT, related_name="children"
    )
    source_kind = models.CharField(max_length=16, blank=True, default="")
    result_deleted_at = models.DateTimeField(null=True)
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


class NotificationRead(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, primary_key=True)
    read_at = models.DateTimeField(auto_now_add=True)


class NotificationReadState(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    read_through = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(id=1), name="notification_single_state"
            )
        ]


class OperationLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_id = models.PositiveBigIntegerField(
        unique=True,
        editable=False,
        db_default=RawSQL("nextval('jobs_operationlog_display_id_seq'::regclass)", []),
    )
    operation = models.CharField(max_length=32)
    result = models.CharField(max_length=16, default="submitted", db_index=True)
    request_id = models.CharField(max_length=64, blank=True)
    idempotency_key = models.UUIDField(null=True)
    project_id = models.UUIDField(null=True, db_index=True)
    project_name = models.CharField(max_length=200, blank=True)
    snapshot_id = models.UUIDField(null=True)
    object_name = models.CharField(max_length=200, blank=True)
    source_kind = models.CharField(max_length=16, blank=True)
    job = models.ForeignKey(Job, null=True, on_delete=models.PROTECT)
    error_code = models.CharField(max_length=80, blank=True)
    events = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(display_id__gte=1, display_id__lte=MAX_DISPLAY_ID),
                name="operation_log_display_id_range",
            )
        ]


class DeletionRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initial_job = models.OneToOneField(
        Job, on_delete=models.PROTECT, related_name="deletion_request"
    )
    current_job = models.OneToOneField(
        Job, on_delete=models.PROTECT, related_name="current_deletion_request"
    )
    target_type = models.CharField(max_length=16)
    target_id = models.UUIDField(db_index=True)
    project_id = models.UUIDField(db_index=True)
    object_name = models.CharField(max_length=200)
    project_name = models.CharField(max_length=200)
    plan_version = models.PositiveSmallIntegerField(default=1)
    inventory = models.JSONField(default=dict)
    phase = models.CharField(max_length=24, default="pending")
    completed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["target_type", "target_id"],
                condition=models.Q(completed_at__isnull=True),
                name="deletion_active_target_unique",
            )
        ]
