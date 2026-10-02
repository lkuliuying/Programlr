import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0002_job_result_url_job_scope_job_snapshot_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="previous_job",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="retries",
                to="jobs.job",
            ),
        ),
    ]
