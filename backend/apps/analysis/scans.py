"""持久化源码扫描及导入后的自动分析链路。"""

import logging
import uuid
from typing import Any

from django.db import DatabaseError, transaction

from apps.analysis.models import SnapshotPreparation, SourceScan, SourceScanRequest
from apps.analysis.root_discovery import SCAN_VERSION
from apps.analysis.scan_runner import run_source_scan
from apps.analysis.types import AnalysisFailed, Source
from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.projects.models import Snapshot, SourceFile
from apps.projects.services import snapshot_contents
from common.resource_state import lock_snapshot, require_snapshot_available

logger = logging.getLogger(__name__)


def dispatch_scan_after_commit(job: Job) -> None:
    try:
        jobs.dispatch_source_scan(job)
    except DatabaseError as exc:
        # 已提交的扫描请求保持可核对，不把投递失败改写为导入失败。
        logger.error("job_id=%s dispatch_type=%s", job.pk, type(exc).__name__)


def create_import_scan(snapshot: Snapshot, parent: Job) -> None:
    key = uuid.uuid5(snapshot.pk, "source-scan/initial")
    job, created = jobs.create_source_scan_job(
        snapshot.pk,
        key,
        jobs.EMPTY_DIGEST,
        parent=parent,
        source_kind=parent.source_kind,
    )
    if created:
        SourceScanRequest.objects.create(job=job, snapshot=snapshot)
        SnapshotPreparation.objects.create(snapshot=snapshot, scan_job=job)
        transaction.on_commit(lambda: dispatch_scan_after_commit(job))


def submit_source_scan(
    snapshot: Snapshot, key: uuid.UUID, *, previous: Job | None = None
) -> tuple[Job, bool, bool]:
    with transaction.atomic():
        snapshot = lock_snapshot(snapshot.pk)
        job, created = jobs.create_source_scan_job(
            snapshot.pk,
            key,
            jobs.EMPTY_DIGEST,
            previous=previous,
            source_kind=previous.source_kind if previous else snapshot.job.source_kind,
        )
        if created:
            SourceScanRequest.objects.create(job=job, snapshot=snapshot)
            preparation, _ = (
                SnapshotPreparation.objects.select_for_update().get_or_create(
                    snapshot=snapshot
                )
            )
            preparation.status = "pending"
            preparation.scan_job = job
            preparation.source_scan = None
            preparation.analysis_job = None
            preparation.analysis = None
            preparation.save(
                update_fields=[
                    "status",
                    "scan_job",
                    "source_scan",
                    "analysis_job",
                    "analysis",
                ]
            )
    published = jobs.dispatch_source_scan(job) if created else True
    job.refresh_from_db()
    return job, created, published


def execute_source_scan(job_id: str) -> None:
    claim = jobs.claim_source_scan(job_id)
    if claim is None:
        return
    record = SourceScanRequest.objects.select_related(
        "snapshot", "snapshot__project"
    ).get(job_id=job_id)
    try:
        require_snapshot_available(record.snapshot)
        SnapshotPreparation.objects.filter(
            snapshot=record.snapshot, scan_job_id=uuid.UUID(job_id)
        ).update(status="scanning")
        files = SourceFile.objects.filter(snapshot=record.snapshot).select_related(
            "snapshot", "snapshot__project"
        )
        sources = [
            Source(source.file_path, content)
            for source, content in snapshot_contents(record.snapshot, files)
        ]
        result = run_source_scan(str(record.snapshot_id), sources)

        def publish() -> str:
            lock_snapshot(record.snapshot_id)
            scan = SourceScan.objects.create(
                job_id=job_id,
                snapshot=record.snapshot,
                rule_version=SCAN_VERSION,
                result=result,
            )
            preparation = SnapshotPreparation.objects.select_for_update().get(
                snapshot=record.snapshot
            )
            if str(preparation.scan_job_id) == job_id:
                preparation.source_scan = scan
                preparation.status = (
                    result["roots"]["status"]
                    if result["roots"]["status"] != "selected"
                    else "analyzing"
                )
                preparation.analysis = None
                preparation.analysis_job = None
                preparation.save()
                if result["roots"]["selected_root"] is not None:
                    from apps.analysis.services import submit_analysis

                    submit_analysis(
                        record.snapshot,
                        uuid.uuid5(scan.pk, "initial-analysis"),
                        result["roots"]["selected_root"],
                        source_scan=scan,
                        parent=record.job,
                        defer_dispatch=True,
                    )
            return f"/api/v1/source-scans/{scan.pk}/"

        jobs.complete_source_scan(job_id, claim, publish)
    except Exception as exc:
        reason = (
            exc.reason if isinstance(exc, AnalysisFailed) else "scan_processing_failed"
        )
        if not isinstance(exc, AnalysisFailed):
            logger.error("job_id=%s scan_type=%s", job_id, type(exc).__name__)
        jobs.fail_source_scan(job_id, claim, "SOURCE_SCAN_FAILED", reason)
        SnapshotPreparation.objects.filter(
            snapshot_id=record.snapshot_id,
            scan_job_id=uuid.UUID(job_id),
            scan_job__status=Job.Status.FAILED,
        ).update(status="failed")


def preparation_fields(snapshot: Snapshot) -> dict[str, Any]:
    preparation = (
        SnapshotPreparation.objects.select_related("scan_job", "analysis_job")
        .filter(snapshot=snapshot)
        .first()
    )
    if preparation is None:
        return {
            "preparation_status": "pending",
            "source_scan_id": None,
            "scan_job_id": None,
            "analysis_job_id": None,
            "analysis_id": None,
        }
    status = preparation.status
    if (
        preparation.analysis_job is not None
        and preparation.analysis_job.status == "failed"
    ):
        status = "failed"
    elif preparation.scan_job is not None and preparation.scan_job.status == "failed":
        status = "failed"
    return {
        "preparation_status": status,
        "source_scan_id": str(preparation.source_scan_id)
        if preparation.source_scan_id
        else None,
        "scan_job_id": str(preparation.scan_job_id)
        if preparation.scan_job_id
        else None,
        "analysis_job_id": str(preparation.analysis_job_id)
        if preparation.analysis_job_id
        else None,
        "analysis_id": str(preparation.analysis_id)
        if preparation.analysis_id
        else None,
    }
