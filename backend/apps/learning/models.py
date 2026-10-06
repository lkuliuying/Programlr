import uuid

from django.db import models


class KnowledgeCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=80)
    version = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    body = models.TextField()
    applicability = models.TextField()
    review_note = models.TextField()
    content_digest = models.CharField(max_length=64)

    class Meta:
        ordering = ["slug", "version", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "version"], name="knowledge_version_unique"
            )
        ]


class TeachingExample(models.Model):
    version = models.CharField(max_length=80, primary_key=True)
    files = models.JSONField()
    content_digest = models.CharField(max_length=64)


class Exercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=80)
    version = models.CharField(max_length=40)
    answer_version = models.CharField(max_length=40)
    example = models.ForeignKey(TeachingExample, on_delete=models.PROTECT)
    kind = models.CharField(max_length=32)
    question = models.TextField()
    hint = models.TextField()
    options = models.JSONField()
    answer = models.JSONField()
    explanation = models.TextField()
    source_refs = models.JSONField()
    review_note = models.TextField()
    content_digest = models.CharField(max_length=64)

    class Meta:
        ordering = ["slug", "version", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "version"], name="exercise_version_unique"
            )
        ]


class ExerciseAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT)
    snapshot = models.ForeignKey("projects.Snapshot", on_delete=models.PROTECT)
    analysis = models.ForeignKey("analysis.Analysis", on_delete=models.PROTECT)
    endpoint_index = models.PositiveIntegerField()
    idempotency_key = models.UUIDField(unique=True)
    request_digest = models.CharField(max_length=64)
    answer = models.JSONField()
    hint_used = models.BooleanField()
    correct = models.BooleanField()
    feedback = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    previous_attempt = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, related_name="reattempts"
    )

    class Meta:
        ordering = ["-created_at", "-id"]


class KnowledgeCurriculum(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=80)
    version = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    definition = models.JSONField()
    content_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["slug", "version", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "version"], name="curriculum_version_unique"
            )
        ]


class AttemptReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(ExerciseAttempt, on_delete=models.PROTECT)
    idempotency_key = models.UUIDField(unique=True)
    request_digest = models.CharField(max_length=64)
    judgement = models.CharField(max_length=20)
    note = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class CurriculumCardProgress(models.Model):
    curriculum = models.ForeignKey(KnowledgeCurriculum, on_delete=models.CASCADE)
    card = models.ForeignKey(KnowledgeCard, on_delete=models.PROTECT)
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["curriculum", "card"], name="curriculum_card_progress_unique"
            )
        ]
