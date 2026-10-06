from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import DatabaseError, transaction

from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.projects.archive import inspect_archive, prepare_archive
from apps.projects.exceptions import ImportRejected
from apps.projects.folder import (
    CODEC_VERSION,
    folder_limits,
    read_manifest,
    write_folder_archive,
)
from apps.projects.models import ImportRequest, Project, Snapshot, SourceFile
from apps.projects.storage import (
    file_lock,
    import_limits,
    publish_directory,
    read_bytes,
    remove_owned_directory,
    stage_lock,
    storage_root,
    sync_directory,
    write_bytes,
    write_manifest,
)
from apps.projects.types import ImportLimits
from common.errors import Conflict
from common.resource_state import lock_project, require_snapshot_available

logger = logging.getLogger(__name__)


def request_limits(record: ImportRequest) -> ImportLimits:
    if record.source_kind not in {"zip", "folder"}:
        raise ImportRejected("import_policy_invalid", storage=True)
    expected_codec = (
        CODEC_VERSION if record.source_kind == "folder" else "zip-original/1.0.0"
    )
    if record.codec_version != expected_codec:
        raise ImportRejected("import_policy_invalid", storage=True)
    if not record.effective_limits and record.source_kind == "zip":
        return import_limits()
    ceiling = asdict(
        folder_limits() if record.source_kind == "folder" else ImportLimits()
    )
    values = record.effective_limits
    if (
        not isinstance(values, dict)
        or set(values) != set(ceiling)
        or any(
            type(values[name]) is not int or not 0 < values[name] <= ceiling[name]
            for name in ceiling
        )
    ):
        raise ImportRejected("import_policy_invalid", storage=True)
    return ImportLimits(**values)


def create_project(key: uuid.UUID, name: str) -> tuple[Project, bool]:
    project, created = Project.objects.get_or_create(
        idempotency_key=key, defaults={"name": name}
    )
    if project.name != name:
        raise Conflict
    return project, created


def rename_snapshot(snapshot: Snapshot, name: str) -> Snapshot:
    from common.resource_state import lock_snapshot

    with transaction.atomic():
        snapshot = lock_snapshot(snapshot.pk)
        snapshot.name = name
        snapshot.save(update_fields=["name"])
    return snapshot


def submit_import(
    project: Project,
    key: uuid.UUID,
    upload: UploadedFile[Any] | None,
    *,
    previous: Job | None = None,
    folder_files: list[UploadedFile[Any]] | None = None,
    manifest: UploadedFile[Any] | None = None,
) -> tuple[Job, bool, bool]:
    source_kind = "folder" if folder_files is not None else "zip"
    limits = folder_limits() if source_kind == "folder" else import_limits()
    if previous is not None:
        prior = ImportRequest.objects.get(job=previous)
        if prior.source_kind != source_kind:
            raise Conflict
        limits = request_limits(prior)
    entries = (
        read_manifest(manifest, folder_files)
        if manifest is not None and folder_files is not None
        else None
    )
    if (source_kind == "folder" and entries is None) or (
        source_kind == "zip" and upload is None
    ):
        raise ImportRejected("import_input_missing")
    identifier = uuid.uuid4()
    try:
        with transaction.atomic():
            project = lock_project(project.pk)
            job, created = receive_import(
                project, key, upload, identifier, limits, source_kind, entries, previous
            )
        # 上传锁释放且请求提交后才投递，避免快速 Worker 看不到已接收输入。
        published = jobs.dispatch_import(job) if created else True
        if not published:
            with stage_lock(identifier) as failed_stage:
                if failed_stage is not None:
                    cleanup_stage(failed_stage)
        job.refresh_from_db()
        return job, created, published
    except OSError:
        raise ImportRejected("storage_io", storage=True) from None


def receive_import(
    project: Project,
    key: uuid.UUID,
    upload: UploadedFile[Any] | None,
    identifier: uuid.UUID,
    limits: ImportLimits,
    source_kind: str,
    entries: list[tuple[str, UploadedFile[Any]]] | None,
    previous: Job | None,
) -> tuple[Job, bool]:
    try:
        with stage_lock(identifier, create=True) as stage:
            if stage is None:
                raise ImportRejected("stage_unavailable", storage=True)
            digest = hashlib.sha256()
            size = 0
            deadline = time.monotonic() + 10
            try:
                if entries is not None:
                    write_folder_archive(
                        stage / "archive.zip", entries, deadline=deadline
                    )
                    with (stage / "archive.zip").open("rb") as target:
                        os.fsync(target.fileno())
                else:
                    assert upload is not None
                    with (stage / "archive.zip").open("xb") as target:
                        for chunk in upload.chunks(64 * 1024):
                            size += len(chunk)
                            if (
                                size > limits.archive_bytes
                                or time.monotonic() > deadline
                            ):
                                raise ImportRejected(
                                    "archive_bytes_or_receive_timeout", limit=True
                                )
                            target.write(chunk)
                        target.flush()
                        os.fsync(target.fileno())
                with (stage / "archive.zip").open("rb") as received:
                    for chunk in iter(lambda: received.read(64 * 1024), b""):
                        if time.monotonic() > deadline:
                            raise ImportRejected("archive_receive_timeout", limit=True)
                        digest.update(chunk)
                inspect_archive(stage / "archive.zip", limits)
                sync_directory(stage)
                with transaction.atomic():
                    if previous is not None:
                        job, created = jobs.create_retry_job(
                            previous, key, digest.hexdigest()
                        )
                    else:
                        job, created = jobs.create_import_job(
                            f"{'folder_imports_create' if source_kind == 'folder' else 'imports_create'}:{project.pk}",
                            key,
                            digest.hexdigest(),
                            source_kind=source_kind,
                        )
                    if created:
                        ImportRequest.objects.create(
                            job=job,
                            project=project,
                            storage_id=identifier,
                            source_kind=source_kind,
                            effective_limits=asdict(limits),
                            codec_version=CODEC_VERSION
                            if source_kind == "folder"
                            else "zip-original/1.0.0",
                        )
            finally:
                # 数据库提交结果不确定时保留暂存，由后续扫描核对，不能误删已接收输入。
                cleanup_stage(stage)
        return job, created
    except OSError:
        raise ImportRejected("storage_io", storage=True) from None


def cleanup_stage(stage: Path) -> bool:
    record = (
        ImportRequest.objects.select_related("job")
        .filter(storage_id=uuid.UUID(stage.name))
        .first()
    )
    if record and record.job.status in (Job.Status.QUEUED, Job.Status.RUNNING):
        return False
    root = storage_root()
    if not Snapshot.objects.filter(pk=uuid.UUID(stage.name)).exists():
        remove_owned_directory(root / "snapshots" / stage.name, root / "snapshots")
    remove_owned_directory(stage, root / "staging")
    return True


def reconcile_import_storage() -> int:
    root = storage_root()
    count = 0
    with file_lock(root / ".guard"):
        for stage in (root / "staging").iterdir():
            try:
                uuid.UUID(stage.name)
            except ValueError:
                continue
            if stage.is_symlink() or not stage.is_dir():
                continue
            with file_lock(stage / ".lock", blocking=False) as acquired:
                if acquired and cleanup_stage(stage):
                    count += 1
    return count


def execute_import(job_id: str) -> None:
    record = ImportRequest.objects.get(job_id=job_id)
    try:
        with stage_lock(record.storage_id) as stage:
            if stage is None:
                return
            claim = jobs.claim_import(job_id)
            if claim is None:
                return
            try:
                prepared = stage / "prepared"
                prepared.mkdir(mode=0o700)
                result = prepare_archive(
                    stage / "archive.zip",
                    prepared,
                    request_limits(record),
                    write_bytes,
                    deadline=time.monotonic() + settings.JOB_EXECUTION_TIMEOUT_SECONDS,
                )
                manifest: dict[str, Any] = {
                    "snapshot_id": str(record.storage_id),
                    "summary": result["summary"],
                    "files": [
                        {
                            key: value
                            for key, value in item.items()
                            if key != "line_offsets"
                        }
                        for item in result["files"]
                    ],
                }
                manifest_digest = write_manifest(prepared, manifest)

                def publish() -> uuid.UUID:
                    lock_project(record.project_id)
                    publish_directory(prepared, record.storage_id)
                    snapshot = Snapshot.objects.create(
                        id=record.storage_id,
                        project=record.project,
                        job_id=job_id,
                        summary=result["summary"],
                        manifest_digest=manifest_digest,
                    )
                    SourceFile.objects.bulk_create(
                        [
                            SourceFile(snapshot=snapshot, **item)
                            for item in result["files"]
                        ]
                    )
                    from apps.analysis.scans import create_import_scan

                    create_import_scan(snapshot, record.job)
                    return snapshot.pk

                jobs.complete_import(job_id, claim, publish)
            except ImportRejected as exc:
                jobs.fail_import(job_id, claim, exc.code, exc.message, exc.reason)
            except TimeoutError:
                jobs.fail_import(
                    job_id,
                    claim,
                    "EXECUTION_TIMEOUT",
                    "导入执行超时，结果未被接受。",
                    "execution_timeout",
                )
            except OSError:
                jobs.fail_import(
                    job_id,
                    claim,
                    "IMPORT_STORAGE_FAILED",
                    "快照写入失败，旧快照保持不变。",
                    "storage_io",
                )
            except Exception as exc:
                # Worker 边界仅记录类型；失败持久化也失败时让异常上抛，由期限核对收敛。
                logger.error("job_id=%s exception_type=%s", job_id, type(exc).__name__)
                jobs.fail_import(
                    job_id,
                    claim,
                    "IMPORT_FAILED",
                    "导入失败，未发布新的可见快照。",
                    "processing_failed",
                )
            finally:
                cleanup_stage(stage)
    except (OSError, DatabaseError) as exc:
        logger.error("job_id=%s recovery_pending=%s", job_id, type(exc).__name__)
        raise RuntimeError("导入处理需等待期限核对。") from None


def validate_snapshot(snapshot: Snapshot) -> None:
    """核验发布标记，空快照也不能绕过完整性检查。"""
    require_snapshot_available(snapshot)
    try:
        directory = storage_root() / "snapshots" / str(snapshot.pk)
        if directory.is_symlink() or not directory.is_dir():
            raise ImportRejected("snapshot_missing", storage=True)
        marker = read_bytes(directory / ".complete.json", 16 * 1024 * 1024)
        if hashlib.sha256(marker).hexdigest() != snapshot.manifest_digest:
            raise ImportRejected("manifest_mismatch", storage=True)
    except OSError:
        raise ImportRejected("snapshot_unavailable", storage=True) from None


def source_content(source: SourceFile, start: int, end: int) -> str:
    validate_snapshot(source.snapshot)
    return _read_source_content(source, start, end)


def snapshot_contents(
    snapshot: Snapshot, files: Iterable[SourceFile]
) -> Iterator[tuple[SourceFile, str]]:
    # 一次批量扫描只校验一次不可变快照标记；每个文件仍独立校验长度和摘要。
    validate_snapshot(snapshot)
    for source in files:
        if source.snapshot_id != snapshot.pk:
            raise ImportRejected("snapshot_source_mismatch", storage=True)
        yield source, _read_source_content(source, 1, source.line_count)


def _read_source_content(source: SourceFile, start: int, end: int) -> str:
    try:
        directory = storage_root() / "snapshots" / str(source.snapshot_id)
        data = read_bytes(directory / str(source.pk), source.size_bytes)
        if (
            len(data) != source.size_bytes
            or hashlib.sha256(data).hexdigest() != source.sha256
        ):
            raise ImportRejected("content_mismatch", storage=True)
        checkpoint = (start - 1) // 128
        offset = source.line_offsets[checkpoint]
        for _ in range(checkpoint * 128 + 1, start):
            offset = data.index(b"\n", offset) + 1
        finish = offset
        for _ in range(start, end + 1):
            position = data.find(b"\n", finish)
            finish = position + 1 if position >= 0 else len(data)
        return data[offset:finish].decode("utf-8")
    except (OSError, UnicodeError, IndexError, ValueError):
        raise ImportRejected("snapshot_unavailable", storage=True) from None
