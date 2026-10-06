import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0004_notificationread_notificationreadstate"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="parent_job",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="jobs.job",
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="result_deleted_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="source_kind",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.CreateModel(
            name="OperationLog",
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
                ("operation", models.CharField(max_length=32)),
                (
                    "result",
                    models.CharField(db_index=True, default="submitted", max_length=16),
                ),
                ("request_id", models.CharField(blank=True, max_length=64)),
                ("idempotency_key", models.UUIDField(null=True)),
                ("project_id", models.UUIDField(db_index=True, null=True)),
                ("project_name", models.CharField(blank=True, max_length=200)),
                ("snapshot_id", models.UUIDField(null=True)),
                ("object_name", models.CharField(blank=True, max_length=200)),
                ("source_kind", models.CharField(blank=True, max_length=16)),
                ("error_code", models.CharField(blank=True, max_length=80)),
                ("events", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="jobs.job",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="DeletionRequest",
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
                ("target_type", models.CharField(max_length=16)),
                ("target_id", models.UUIDField(db_index=True)),
                ("project_id", models.UUIDField(db_index=True)),
                ("object_name", models.CharField(max_length=200)),
                ("project_name", models.CharField(max_length=200)),
                ("plan_version", models.PositiveSmallIntegerField(default=1)),
                ("inventory", models.JSONField(default=dict)),
                ("phase", models.CharField(default="pending", max_length=24)),
                ("completed_at", models.DateTimeField(null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "current_job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="current_deletion_request",
                        to="jobs.job",
                    ),
                ),
                (
                    "initial_job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="deletion_request",
                        to="jobs.job",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("completed_at__isnull", True)),
                        fields=("target_type", "target_id"),
                        name="deletion_active_target_unique",
                    )
                ],
            },
        ),
    ]
