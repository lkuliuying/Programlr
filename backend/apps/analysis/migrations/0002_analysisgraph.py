import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analysis", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalysisGraph",
            fields=[
                (
                    "analysis",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        primary_key=True,
                        serialize=False,
                        to="analysis.analysis",
                    ),
                ),
                ("graph_version", models.CharField(max_length=80)),
                ("nodes", models.JSONField()),
                ("edges", models.JSONField()),
            ],
        ),
    ]
