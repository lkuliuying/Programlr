import uuid

from django.db import models


class ContextPreview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey("analysis.Analysis", on_delete=models.PROTECT)
    snapshot = models.ForeignKey("projects.Snapshot", on_delete=models.PROTECT)
    endpoint_index = models.PositiveIntegerField()
    idempotency_key = models.UUIDField(unique=True)
    request_digest = models.CharField(max_length=64)
    payload = models.JSONField()
    payload_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class ContextConsent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    preview = models.ForeignKey(ContextPreview, on_delete=models.PROTECT)
    idempotency_key = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["preview", "idempotency_key"], name="consent_preview_key_unique"
            )
        ]


class ExplanationRequest(models.Model):
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT, primary_key=True)
    consent = models.OneToOneField(ContextConsent, on_delete=models.PROTECT)


class Explanation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT)
    preview = models.ForeignKey(ContextPreview, on_delete=models.PROTECT)
    content = models.JSONField()
    model = models.CharField(max_length=200)
    usage = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
