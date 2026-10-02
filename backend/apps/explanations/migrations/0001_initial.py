import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("analysis", "0003_analysis_frontend"),
        ("jobs", "0003_job_previous_job"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContextPreview",
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
                ("payload", models.JSONField()),
                ("payload_digest", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="analysis.analysis",
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
            name="ContextConsent",
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
                ("idempotency_key", models.UUIDField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "preview",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="explanations.contextpreview",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Explanation",
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
                ("content", models.JSONField()),
                ("model", models.CharField(max_length=200)),
                ("usage", models.JSONField(null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT, to="jobs.job"
                    ),
                ),
                (
                    "preview",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="explanations.contextpreview",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ExplanationRequest",
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
                    "consent",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="explanations.contextconsent",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="contextconsent",
            constraint=models.UniqueConstraint(
                fields=("preview", "idempotency_key"), name="consent_preview_key_unique"
            ),
        ),
    ]
