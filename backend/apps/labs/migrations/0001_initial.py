import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("analysis", "0003_analysis_frontend"),
        ("jobs", "0003_job_previous_job"),
    ]

    operations = [
        migrations.CreateModel(
            name="LabRun",
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
