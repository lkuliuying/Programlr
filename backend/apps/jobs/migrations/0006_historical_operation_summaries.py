import uuid

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def backfill_summaries(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """只回填任务摘要，不读取或复制源码和业务结果正文。"""
    Job = apps.get_model("jobs", "Job")
    OperationLog = apps.get_model("jobs", "OperationLog")
    Snapshot = apps.get_model("projects", "Snapshot")
    Project = apps.get_model("projects", "Project")
    ImportRequest = apps.get_model("projects", "ImportRequest")
    LabRun = apps.get_model("labs", "LabRun")
    SystemLabRun = apps.get_model("labs", "SystemLabRun")
    alias = schema_editor.connection.alias
    projects = dict(Project.objects.using(alias).values_list("pk", "name"))
    snapshots = {
        row[0]: (row[1], row[2])
        for row in Snapshot.objects.using(alias).values_list("pk", "project_id", "name")
    }
    imports = {
        row[0]: (row[1], row[2])
        for row in ImportRequest.objects.using(alias).values_list(
            "job_id", "project_id", "source_kind"
        )
    }
    labs = {
        row[0]: row[1]
        for model in (LabRun, SystemLabRun)
        for row in model.objects.using(alias).values_list(
            "job_id", "analysis__snapshot_id"
        )
    }
    for job in Job.objects.using(alias).iterator(chunk_size=200):
        if OperationLog.objects.using(alias).filter(job_id=job.pk).exists():
            continue
        owner_id, object_name, source_kind = None, "", job.source_kind
        snapshot_id = job.snapshot_id or labs.get(job.pk)
        if snapshot_id in snapshots:
            owner_id, object_name = snapshots[snapshot_id]
        elif job.pk in imports:
            owner_id, source_kind = imports[job.pk]
            object_name = projects.get(owner_id, "")
        elif job.scope.startswith("imports_create:"):
            try:
                owner_id = uuid.UUID(job.scope.split(":", 1)[1])
                object_name = projects.get(owner_id, "")
            except ValueError:
                owner_id = None
        result = "accepted" if job.status == "queued" else job.status
        error_code = (
            str(job.error.get("code", ""))[:80] if isinstance(job.error, dict) else ""
        )
        log = OperationLog.objects.using(alias).create(
            operation=job.kind,
            result=result,
            idempotency_key=job.idempotency_key,
            project_id=owner_id,
            project_name=projects.get(owner_id, "") if owner_id is not None else "",
            snapshot_id=snapshot_id,
            object_name=object_name,
            source_kind=source_kind,
            job_id=job.pk,
            error_code=error_code,
            events=[
                {
                    "result": result,
                    "at": job.updated_at.isoformat(),
                    "stage": job.stage,
                    "legacy": True,
                }
            ],
        )
        OperationLog.objects.using(alias).filter(pk=log.pk).update(
            created_at=job.created_at, updated_at=job.updated_at
        )


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0005_job_parent_job_job_result_deleted_at_job_source_kind_and_more"),
        ("projects", "0003_import_sources_and_deletion_state"),
        ("analysis", "0006_source_scans"),
        ("labs", "0002_systemlabrun"),
    ]
    operations = [migrations.RunPython(backfill_summaries, migrations.RunPython.noop)]
