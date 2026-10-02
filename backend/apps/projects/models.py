import uuid

from django.db import models


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    idempotency_key = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""), name="project_name_nonempty"
            )
        ]


class ImportRequest(models.Model):
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT, primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    storage_id = models.UUIDField(unique=True)


class Snapshot(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=200, blank=True, default="")
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT)
    summary = models.JSONField()
    manifest_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class SourceFile(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    snapshot = models.ForeignKey(
        Snapshot, on_delete=models.PROTECT, related_name="files"
    )
    file_path = models.CharField(max_length=1024)
    sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    line_count = models.PositiveIntegerField()
    line_offsets = models.JSONField()
    encoding = models.CharField(max_length=16, default="utf-8")

    class Meta:
        ordering = ["file_path", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "file_path"], name="snapshot_unique_path"
            )
        ]
