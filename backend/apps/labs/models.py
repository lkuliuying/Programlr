import uuid

from django.db import models

from apps.analysis.models import Analysis
from apps.jobs.models import Job


class LabRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField(Job, on_delete=models.PROTECT)
    analysis = models.ForeignKey(Analysis, on_delete=models.PROTECT)
    endpoint_index = models.PositiveIntegerField()
    definition = models.JSONField()
    predictions = models.JSONField()
    observations = models.JSONField(default=list)
    cleanup = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class SystemLabRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField(Job, on_delete=models.PROTECT)
    analysis = models.ForeignKey(Analysis, on_delete=models.PROTECT)
    endpoint_index = models.PositiveIntegerField()
    lab_id = models.CharField(max_length=40)
    definition = models.JSONField()
    predictions = models.JSONField()
    observations = models.JSONField(default=list)
    cleanup = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
