from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0002_snapshot_name")]
    operations = [
        migrations.AddField(
            model_name="project",
            name="deletion_request_id",
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name="snapshot",
            name="deletion_request_id",
            field=models.UUIDField(null=True),
        ),
        migrations.AddField(
            model_name="importrequest",
            name="source_kind",
            field=models.CharField(default="zip", max_length=12),
        ),
        migrations.AddField(
            model_name="importrequest",
            name="effective_limits",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="importrequest",
            name="codec_version",
            field=models.CharField(default="zip-original/1.0.0", max_length=40),
        ),
    ]
