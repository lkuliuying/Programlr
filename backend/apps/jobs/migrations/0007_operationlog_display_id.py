from django.db import migrations, models
from django.db.models.expressions import RawSQL


class Migration(migrations.Migration):
    atomic = True
    dependencies = [("jobs", "0006_historical_operation_summaries")]
    operations = [
        migrations.RunSQL(
            "CREATE SEQUENCE jobs_operationlog_display_id_seq AS bigint "
            "MINVALUE 1 MAXVALUE 9007199254740991 START 1 NO CYCLE",
            "DROP SEQUENCE jobs_operationlog_display_id_seq",
        ),
        migrations.AddField(
            model_name="operationlog",
            name="display_id",
            field=models.PositiveBigIntegerField(editable=False, null=True),
        ),
        # 只回填新列；固定时间与 UUID 次序，不调用 save 修改历史时间或事件。
        migrations.RunSQL(
            "WITH numbered AS ("
            "SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS number "
            "FROM jobs_operationlog) "
            "UPDATE jobs_operationlog AS log SET display_id = numbered.number "
            "FROM numbered WHERE log.id = numbered.id",
            migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            "SELECT setval('jobs_operationlog_display_id_seq'::regclass, "
            "COALESCE(MAX(display_id), 0) + 1, false) FROM jobs_operationlog",
            migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="operationlog",
            name="display_id",
            field=models.PositiveBigIntegerField(
                unique=True,
                editable=False,
                db_default=RawSQL(
                    "nextval('jobs_operationlog_display_id_seq'::regclass)", []
                ),
            ),
        ),
        migrations.AddConstraint(
            model_name="operationlog",
            constraint=models.CheckConstraint(
                condition=models.Q(display_id__gte=1, display_id__lte=9007199254740991),
                name="operation_log_display_id_range",
            ),
        ),
        migrations.RunSQL(
            "ALTER SEQUENCE jobs_operationlog_display_id_seq "
            "OWNED BY jobs_operationlog.display_id",
            "ALTER SEQUENCE jobs_operationlog_display_id_seq OWNED BY NONE",
        ),
    ]
