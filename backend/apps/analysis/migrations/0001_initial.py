import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("jobs", "0002_job_result_url_job_scope_job_snapshot_id_and_more"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Analysis",
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
                ("root_urlconf", models.CharField(max_length=1024)),
                ("rule_version", models.CharField(max_length=80)),
                ("coverage", models.JSONField()),
                ("endpoints", models.JSONField()),
                ("diagnostics", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT, to="jobs.job"
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
        ),
        migrations.CreateModel(
            name="AnalysisRequest",
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
                ("root_urlconf", models.CharField(max_length=1024)),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="projects.snapshot",
                    ),
                ),
            ],
        ),
    ]
