# Django 生成的增量迁移：系统实验记录与原请求实验分开保存。

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0005_snapshotcomparisonrequest_snapshotcomparison"),
        ("jobs", "0003_job_previous_job"),
        ("labs", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemLabRun",
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
                ("lab_id", models.CharField(max_length=40)),
                ("definition", models.JSONField()),
                ("predictions", models.JSONField()),
                ("observations", models.JSONField(default=list)),
                ("cleanup", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="analysis.analysis",
                    ),
                ),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT, to="jobs.job"
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
