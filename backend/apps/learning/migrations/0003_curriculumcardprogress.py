import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0002_exerciseattempt_previous_attempt_attemptreview_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CurriculumCardProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("completed", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "card",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="learning.knowledgecard",
                    ),
                ),
                (
                    "curriculum",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="learning.knowledgecurriculum",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("curriculum", "card"),
                        name="curriculum_card_progress_unique",
                    )
                ],
            },
        ),
    ]
