# Django 生成的增量迁移：保留旧作答并增加课程与复习记录。

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="exerciseattempt",
            name="previous_attempt",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reattempts",
                to="learning.exerciseattempt",
            ),
        ),
        migrations.CreateModel(
            name="AttemptReview",
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
                ("idempotency_key", models.UUIDField(unique=True)),
                ("request_digest", models.CharField(max_length=64)),
                ("judgement", models.CharField(max_length=20)),
                ("note", models.CharField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="learning.exerciseattempt",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="KnowledgeCurriculum",
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
                ("definition", models.JSONField()),
                ("content_digest", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["slug", "version", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("slug", "version"), name="curriculum_version_unique"
                    )
                ],
            },
        ),
    ]
