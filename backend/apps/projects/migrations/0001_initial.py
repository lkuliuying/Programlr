import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("jobs", "0002_job_result_url_job_scope_job_snapshot_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
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
                ("name", models.CharField(max_length=200)),
                ("idempotency_key", models.UUIDField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("name", ""), _negated=True),
                        name="project_name_nonempty",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ImportRequest",
            fields=[
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        primary_key=True,
                        serialize=False,
                        to="jobs.job",
                    ),
                ),
                ("storage_id", models.UUIDField(unique=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="projects.project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Snapshot",
            fields=[
                (
                    "id",
                    models.UUIDField(editable=False, primary_key=True, serialize=False),
                ),
                ("summary", models.JSONField()),
                ("manifest_digest", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT, to="jobs.job"
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SourceFile",
            fields=[
                (
                    "id",
                    models.UUIDField(editable=False, primary_key=True, serialize=False),
                ),
                ("file_path", models.CharField(max_length=1024)),
                ("sha256", models.CharField(max_length=64)),
                ("size_bytes", models.PositiveIntegerField()),
                ("line_count", models.PositiveIntegerField()),
                ("line_offsets", models.JSONField()),
                ("encoding", models.CharField(default="utf-8", max_length=16)),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="files",
                        to="projects.snapshot",
                    ),
                ),
            ],
            options={
                "ordering": ["file_path", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("snapshot", "file_path"), name="snapshot_unique_path"
                    )
                ],
            },
        ),
    ]
