import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0005_snapshotcomparisonrequest_snapshotcomparison"),
        ("projects", "0003_import_sources_and_deletion_state"),
        ("jobs", "0004_notificationread_notificationreadstate"),
    ]
    operations = [
        migrations.CreateModel(
            name="SourceScanRequest",
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
            name="SourceScan",
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
                ("rule_version", models.CharField(max_length=80)),
                ("result", models.JSONField()),
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
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddField(
            model_name="analysisrequest",
            name="source_scan",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="analysis.sourcescan",
            ),
        ),
        migrations.AddField(
            model_name="analysis",
            name="source_scan",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="analysis.sourcescan",
            ),
        ),
        migrations.CreateModel(
            name="SnapshotPreparation",
            fields=[
                (
                    "snapshot",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        primary_key=True,
                        related_name="preparation",
                        serialize=False,
                        to="projects.snapshot",
                    ),
                ),
                ("status", models.CharField(default="pending", max_length=20)),
                (
                    "scan_job",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scan_preparations",
                        to="jobs.job",
                    ),
                ),
                (
                    "analysis_job",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="analysis_preparations",
                        to="jobs.job",
                    ),
                ),
                (
                    "analysis",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="analysis.analysis",
                    ),
                ),
                (
                    "source_scan",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="analysis.sourcescan",
                    ),
                ),
            ],
        ),
    ]
