import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("analysis", "0003_analysis_frontend"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Exercise",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("slug", models.CharField(max_length=80)),
                ("version", models.CharField(max_length=40)),
                ("answer_version", models.CharField(max_length=40)),
                ("kind", models.CharField(max_length=32)),
                ("question", models.TextField()),
                ("hint", models.TextField()),
                ("options", models.JSONField()),
                ("answer", models.JSONField()),
                ("explanation", models.TextField()),
                ("source_refs", models.JSONField()),
                ("review_note", models.TextField()),
                ("content_digest", models.CharField(max_length=64)),
            ],
            options={
                "ordering": ["slug", "version", "id"],
            },
        ),
        migrations.CreateModel(
            name="TeachingExample",
            fields=[
                (
                    "version",
                    models.CharField(max_length=80, primary_key=True, serialize=False),
                ),
                ("files", models.JSONField()),
                ("content_digest", models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name="ExerciseAttempt",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("endpoint_index", models.PositiveIntegerField()),
                ("idempotency_key", models.UUIDField(unique=True)),
                ("request_digest", models.CharField(max_length=64)),
                ("answer", models.JSONField()),
                ("hint_used", models.BooleanField()),
                ("correct", models.BooleanField()),
                ("feedback", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="analysis.analysis",
                    ),
                ),
                (
                    "exercise",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="learning.exercise",
                    ),
                ),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="projects.snapshot",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="KnowledgeCard",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("slug", models.CharField(max_length=80)),
                ("version", models.CharField(max_length=40)),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField()),
                ("applicability", models.TextField()),
                ("review_note", models.TextField()),
                ("content_digest", models.CharField(max_length=64)),
            ],
            options={
                "ordering": ["slug", "version", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("slug", "version"), name="knowledge_version_unique"
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="exercise",
            name="example",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="learning.teachingexample",
            ),
        ),
        migrations.AddConstraint(
            model_name="exercise",
            constraint=models.UniqueConstraint(
                fields=("slug", "version"), name="exercise_version_unique"
            ),
        ),
    ]
