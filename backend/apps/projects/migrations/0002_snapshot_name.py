from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="snapshot",
            name="name",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
    ]
