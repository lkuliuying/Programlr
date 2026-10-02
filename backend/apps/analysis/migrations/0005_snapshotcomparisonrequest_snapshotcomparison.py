# Django 5.2.17 生成：仅新增快照对比请求和结果表。

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0004_relationreview_relationreviewstate"),
        ("jobs", "0003_job_previous_job"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SnapshotComparisonRequest",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "base_analysis",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="base_comparisons",
                        to="analysis.analysis",
                    ),
                ),
                (
                    "base_snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="base_comparisons",
                        to="projects.snapshot",
                    ),
                ),
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
                (
                    "target_analysis",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="target_comparisons",
                        to="analysis.analysis",
                    ),
                ),
                (
                    "target_snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="target_comparisons",
                        to="projects.snapshot",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="SnapshotComparison",
            fields=[
                (
                    "request",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        primary_key=True,
                        related_name="result",
                        serialize=False,
                        to="analysis.snapshotcomparisonrequest",
                    ),
                ),
                ("comparison_version", models.CharField(max_length=80)),
                ("summary", models.JSONField()),
                ("data", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
