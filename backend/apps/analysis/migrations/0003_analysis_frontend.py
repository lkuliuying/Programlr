from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analysis", "0002_analysisgraph")]

    operations = [
        migrations.AddField(
            model_name="analysis",
            name="frontend",
            field=models.JSONField(null=True),
        ),
    ]
