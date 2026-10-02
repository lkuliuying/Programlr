import uuid

from django.db import models


class AnalysisRequest(models.Model):
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT, primary_key=True)
    snapshot = models.ForeignKey("projects.Snapshot", on_delete=models.PROTECT)
    root_urlconf = models.CharField(max_length=1024)


class Analysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT)
    snapshot = models.ForeignKey("projects.Snapshot", on_delete=models.PROTECT)
    root_urlconf = models.CharField(max_length=1024)
    rule_version = models.CharField(max_length=80)
    coverage = models.JSONField()
    endpoints = models.JSONField()
    diagnostics = models.JSONField()
    frontend = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AnalysisGraph(models.Model):
    analysis = models.OneToOneField(
        Analysis, on_delete=models.PROTECT, primary_key=True
    )
    graph_version = models.CharField(max_length=80)
    nodes = models.JSONField()
    edges = models.JSONField()


class RelationReviewState(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(Analysis, on_delete=models.PROTECT)
    request_id = models.UUIDField()
    revision = models.PositiveIntegerField(default=0)
    confirmed_target_id = models.UUIDField(null=True)
    excluded_target_ids = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "request_id"], name="unique_relation_review_state"
            )
        ]


class RelationReview(models.Model):
    class Action(models.TextChoices):
        CONFIRM = "confirm", "确认"
        EXCLUDE = "exclude", "排除"
        RESET = "reset", "撤销"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(Analysis, on_delete=models.PROTECT)
    request_id = models.UUIDField()
    target_id = models.UUIDField()
    action = models.CharField(max_length=12, choices=Action.choices)
    revision = models.PositiveIntegerField()
    idempotency_key = models.UUIDField()
    request_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "idempotency_key"],
                name="unique_relation_review_key",
            ),
            models.UniqueConstraint(
                fields=["analysis", "request_id", "revision"],
                name="unique_relation_review_revision",
            ),
        ]


class SnapshotComparisonRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT)
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT)
    base_snapshot = models.ForeignKey(
        "projects.Snapshot", on_delete=models.PROTECT, related_name="base_comparisons"
    )
    target_snapshot = models.ForeignKey(
        "projects.Snapshot", on_delete=models.PROTECT, related_name="target_comparisons"
    )
    base_analysis = models.ForeignKey(
        Analysis, null=True, on_delete=models.PROTECT, related_name="base_comparisons"
    )
    target_analysis = models.ForeignKey(
        Analysis, null=True, on_delete=models.PROTECT, related_name="target_comparisons"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class SnapshotComparison(models.Model):
    request = models.OneToOneField(
        SnapshotComparisonRequest,
        primary_key=True,
        on_delete=models.PROTECT,
        related_name="result",
    )
    comparison_version = models.CharField(max_length=80)
    summary = models.JSONField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
