# 由已锁定的 Django 生成，仅新增人工决定与修订状态，不修改旧分析数据。

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0003_analysis_frontend"),
    ]

    operations = [
        migrations.CreateModel(
            name="RelationReview",
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
                ("request_id", models.UUIDField()),
                ("target_id", models.UUIDField()),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("confirm", "确认"),
                            ("exclude", "排除"),
                            ("reset", "撤销"),
                        ],
                        max_length=12,
                    ),
                ),
                ("revision", models.PositiveIntegerField()),
                ("idempotency_key", models.UUIDField()),
                ("request_digest", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="analysis.analysis",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("analysis", "idempotency_key"),
                        name="unique_relation_review_key",
                    ),
                    models.UniqueConstraint(
                        fields=("analysis", "request_id", "revision"),
                        name="unique_relation_review_revision",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="RelationReviewState",
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
                ("request_id", models.UUIDField()),
                ("revision", models.PositiveIntegerField(default=0)),
                ("confirmed_target_id", models.UUIDField(null=True)),
                ("excluded_target_ids", models.JSONField(default=list)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="analysis.analysis",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("analysis", "request_id"),
                        name="unique_relation_review_state",
                    )
                ],
            },
        ),
    ]
