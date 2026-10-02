# 由 Django 5.2.17 生成，建立基础任务及固定检查结果。

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Job",
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
                ("kind", models.CharField(default="system_check", max_length=32)),
                ("idempotency_key", models.UUIDField(unique=True)),
                ("request_digest", models.CharField(max_length=64)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("stage", models.CharField(default="queued", max_length=32)),
                ("claim_id", models.UUIDField(null=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("error", models.JSONField(null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("status__in", ["queued", "running", "succeeded", "failed"])
                        ),
                        name="job_valid_status",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SystemCheck",
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
                ("check_version", models.CharField(default="1", max_length=16)),
                ("database", models.CharField(default="passed", max_length=16)),
                ("queue", models.CharField(default="passed", max_length=16)),
                ("worker", models.CharField(default="passed", max_length=16)),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="check_result",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
    ]
