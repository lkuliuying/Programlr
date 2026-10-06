import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0003_job_previous_job"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationRead",
            fields=[
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        to="jobs.job",
                    ),
                ),
                ("read_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="NotificationReadState",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("read_through", models.DateTimeField(null=True)),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("id", 1)), name="notification_single_state"
                    )
                ],
            },
        ),
    ]
