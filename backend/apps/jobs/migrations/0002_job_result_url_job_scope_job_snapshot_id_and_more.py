from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="result_url",
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="scope",
            field=models.CharField(default="system_checks_create", max_length=80),
        ),
        migrations.AddField(
            model_name="job",
            name="snapshot_id",
            field=models.UUIDField(null=True),
        ),
        migrations.AlterField(
            model_name="job",
            name="idempotency_key",
            field=models.UUIDField(),
        ),
        migrations.AddConstraint(
            model_name="job",
            constraint=models.UniqueConstraint(
                fields=("scope", "idempotency_key"), name="job_scope_key_unique"
            ),
        ),
    ]
