import hashlib
import multiprocessing
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, close_old_connections, connections
from django.test import override_settings
from django.utils import timezone
from kombu.exceptions import OperationalError
from rest_framework.test import APIClient

from apps.jobs.models import Job
from apps.jobs.services import reconcile_expired
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from apps.projects.models import ImportRequest, Project, Snapshot, SourceFile
from apps.projects.services import (
    create_project,
    execute_import,
    reconcile_import_storage,
    source_content,
    submit_import,
)
from apps.projects.storage import stage_lock, storage_root
from apps.projects.tests.test_archive import zip_bytes
from common.errors import Conflict

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def project() -> Project:
    return create_project(uuid.uuid4(), "合成测试项目")[0]


def upload(data: bytes | None = None) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        "sample.zip",
        data if data is not None else zip_bytes({"a.py": b"one\r\ntwo\n"}),
        content_type="application/octet-stream",
    )


def submitted(owner: Project | None = None, data: bytes | None = None) -> Job:
    with patch("apps.jobs.services.app.send_task"):
        return submit_import(owner or project(), uuid.uuid4(), upload(data))[0]


def test_project_input_idempotency_and_contract() -> None:
    client = client_with_token()
    key = str(uuid.uuid4())
    schema = contract_schema()
    first = client.post(
        "/api/v1/projects/", {"name": " 项目 "}, format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert first.status_code == 201
    assert_response(first, schema, "/api/v1/projects/", "post")
    replay = client.post(
        "/api/v1/projects/", {"name": "项目"}, format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert replay.status_code == 200 and replay.json() == first.json()
    conflict = client.post(
        "/api/v1/projects/", {"name": "另一个"}, format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert conflict.status_code == 409
    for payload in (
        {},
        {"name": None},
        {"name": 123},
        {"name": " "},
        {"name": "a\x00b"},
        {"name": "a", "extra": 1},
        {"name": "a" * 201},
    ):
        assert (
            client.post(
                "/api/v1/projects/",
                payload,
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            ).status_code
            == 400
        )
    assert Project.objects.count() == 1
    assert_response(client.get("/api/v1/projects/"), schema, "/api/v1/projects/")
    assert_response(
        client.get(f"/api/v1/projects/{first.json()['id']}/"),
        schema,
        "/api/v1/projects/{project_id}/",
    )


def test_standard_sample_reimport_and_old_references() -> None:
    owner = project()
    base = Path(__file__).resolve().parents[4] / "examples/task-board"
    entries = {
        path.relative_to(base).as_posix(): path.read_bytes()
        for directory in (base / "backend/apps/tasks", base / "frontend/src")
        for path in directory.rglob("*")
        if path.suffix in {".py", ".ts", ".tsx"}
    }
    assert entries
    data = zip_bytes(entries)
    first, second = submitted(owner, data), submitted(owner, data)
    execute_import(str(first.pk))
    execute_import(str(second.pk))
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status == second.status == "succeeded"
    assert first.snapshot_id != second.snapshot_id
    assert first.snapshot_id is not None
    assert Snapshot.objects.filter(project=owner).count() == 2
    for source in SourceFile.objects.filter(
        snapshot_id=first.snapshot_id
    ).select_related("snapshot"):
        content = source_content(source, 1, source.line_count)
        assert hashlib.sha256(content.encode()).hexdigest() == source.sha256
    assert not list((storage_root() / "staging").iterdir())


def test_import_api_and_all_published_responses_match_schema() -> None:
    client = client_with_token()
    owner = project()
    path = f"/api/v1/projects/{owner.pk}/imports/"
    schema = contract_schema()
    key = str(uuid.uuid4())
    with patch("apps.jobs.services.app.send_task") as send:
        first = client.post(
            path, {"archive": upload()}, format="multipart", HTTP_IDEMPOTENCY_KEY=key
        )
        replay = client.post(
            path, {"archive": upload()}, format="multipart", HTTP_IDEMPOTENCY_KEY=key
        )
        assert first.status_code == 202
        assert replay.status_code == 200 and replay.json()["id"] == first.json()["id"]
        assert send.call_count == 1
    assert_response(first, schema, "/api/v1/projects/{project_id}/imports/", "post")
    execute_import(first.json()["id"])
    job = client.get(first["Location"])
    assert job.json()["status"] == "succeeded"
    assert_response(job, schema, "/api/v1/jobs/{job_id}/")
    snapshot_url = job.json()["result_url"]
    snapshot = client.get(snapshot_url)
    assert_response(snapshot, schema, "/api/v1/snapshots/{snapshot_id}/")
    assert_response(
        client.get(f"/api/v1/projects/{owner.pk}/snapshots/"),
        schema,
        "/api/v1/projects/{project_id}/snapshots/",
    )
    files = client.get(snapshot_url + "files/")
    assert_response(files, schema, "/api/v1/snapshots/{snapshot_id}/files/")
    file_id = files.json()["results"][0]["id"]
    content = client.get(
        snapshot_url + f"files/{file_id}/content/?start_line=2&end_line=2"
    )
    assert content.json()["content"] == "two\n"
    assert_response(
        content, schema, "/api/v1/snapshots/{snapshot_id}/files/{file_id}/content/"
    )


@pytest.mark.parametrize(
    "case", ["missing", "extra", "multiple", "text", "empty", "bad", "json"]
)
def test_invalid_upload_never_creates_task(case: str) -> None:
    client = client_with_token()
    owner = project()
    body: dict[str, Any] = {"archive": upload()}
    if case == "missing":
        body = {}
    elif case == "extra":
        body["path"] = "/host/source"
    elif case == "multiple":
        body["archive"] = [upload(), upload()]
    elif case == "text":
        body["archive"] = "not-file"
    elif case == "empty":
        body["archive"] = upload(b"")
    elif case == "bad":
        body["archive"] = upload(b"broken")
    elif case == "json":
        body = {"archive": "not-file"}
    response = client.post(
        f"/api/v1/projects/{owner.pk}/imports/",
        body,
        format="json" if case == "json" else "multipart",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code in (400, 413, 415)
    assert_response(response, contract_schema())
    assert not Job.objects.exists() and not Snapshot.objects.exists()
    assert not list((storage_root() / "staging").iterdir())


def test_upload_security_and_stream_limits() -> None:
    owner = project()
    path = f"/api/v1/projects/{owner.pk}/imports/"
    client = APIClient(enforce_csrf_checks=True)
    assert (
        client.post(
            path,
            {"archive": upload()},
            format="multipart",
            HTTP_HOST="127.0.0.1:5173",
            HTTP_ORIGIN="http://127.0.0.1:5173",
        ).status_code
        == 403
    )
    client = client_with_token()
    with override_settings(IMPORT_LIMITS={"archive_bytes": 10}):
        response = client.post(
            path,
            {"archive": upload()},
            format="multipart",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        assert response.status_code == 413
        assert response.json()["code"] == "ARCHIVE_LIMIT_EXCEEDED"
        response = client.post(
            path, {"archive": upload()}, format="multipart", CONTENT_LENGTH="999999"
        )
        assert response.status_code == 413
    assert not Job.objects.exists()


def test_import_idempotency_scope_conflict_and_queue_failure() -> None:
    owner, other = project(), project()
    key = uuid.uuid4()
    with patch("apps.jobs.services.app.send_task") as send:
        first = submit_import(owner, key, upload())[0]
        assert submit_import(owner, key, upload())[0].pk == first.pk
        with pytest.raises(Conflict):
            submit_import(owner, key, upload(zip_bytes({"a.py": b"different"})))
        assert submit_import(other, key, upload())[0].pk != first.pk
        folder = submit_import(
            owner,
            key,
            None,
            folder_files=[SimpleUploadedFile("a.py", b"one\ntwo\n")],
            manifest=SimpleUploadedFile(
                "manifest.json", b'{"files":[{"path":"a.py","index":0}]}'
            ),
        )[0]
        assert folder.pk != first.pk and folder.source_kind == "folder"
        assert send.call_count == 3
    with patch(
        "apps.jobs.services.app.send_task", side_effect=OperationalError("synthetic")
    ):
        job, created, published = submit_import(owner, uuid.uuid4(), upload())
    assert created and not published
    job.refresh_from_db()
    assert job.status == "failed" and job.error is not None
    assert job.error["code"] == "QUEUE_UNAVAILABLE"
    record = ImportRequest.objects.get(job=job)
    assert not (storage_root() / "staging" / str(record.storage_id)).exists()


def test_concurrent_submission_and_duplicate_delivery() -> None:
    owner, key = project(), uuid.uuid4()

    def submit(_: int) -> uuid.UUID:
        close_old_connections()
        try:
            return submit_import(owner, key, upload())[0].pk
        finally:
            connections.close_all()

    with (
        patch("apps.jobs.services.app.send_task") as sender,
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        identifiers = list(executor.map(submit, range(2)))
    assert len(set(identifiers)) == 1 and sender.call_count == 1
    execute_import(str(identifiers[0]))
    execute_import(str(identifiers[0]))
    assert Snapshot.objects.count() == 1


def test_immediate_delivery_does_not_race_upload_lock() -> None:
    def deliver(name: str, args: list[str], **kwargs: Any) -> None:
        execute_import(args[0])

    with patch("apps.jobs.services.app.send_task", side_effect=deliver):
        job, created, published = submit_import(project(), uuid.uuid4(), upload())
    assert created and published and job.status == "succeeded"
    assert Snapshot.objects.count() == 1


@pytest.mark.parametrize(
    "point", ["write_bytes", "publish_directory", "snapshot_insert"]
)
def test_disk_or_database_failure_preserves_old_snapshot(point: str) -> None:
    old = submitted()
    execute_import(str(old.pk))
    previous = SourceFile.objects.select_related("snapshot").get()
    new = submitted()
    target = (
        "apps.projects.services.Snapshot.objects.create"
        if point == "snapshot_insert"
        else f"apps.projects.services.{point}"
    )
    with patch(target, side_effect=OSError("synthetic-disk-failure")):
        execute_import(str(new.pk))
    new.refresh_from_db()
    assert new.status == "failed" and new.snapshot_id is None
    assert Snapshot.objects.count() == 1
    assert source_content(previous, 1, 2) == "one\ntwo\n"
    assert not list((storage_root() / "staging").iterdir())
    assert len(list((storage_root() / "snapshots").iterdir())) == 1


def interrupted_import(job_id: str, point: str) -> None:
    from apps.projects import services

    original = getattr(services, point)

    def stop(*args: Any, **kwargs: Any) -> Any:
        original(*args, **kwargs)
        os._exit(23)

    with patch(f"apps.projects.services.{point}", stop):
        execute_import(job_id)


@pytest.mark.parametrize("point", ["write_bytes", "publish_directory"])
def test_actual_process_interruption_recovers_without_partial_snapshot(
    point: str,
) -> None:
    old = submitted()
    execute_import(str(old.pk))
    new = submitted()
    connections.close_all()
    process = multiprocessing.get_context("fork").Process(
        target=interrupted_import, args=(str(new.pk), point)
    )
    process.start()
    process.join(10)
    try:
        assert process.exitcode == 23
    finally:
        if process.is_alive():
            process.kill()
            process.join(5)
        process.close()
    assert Snapshot.objects.count() == 1
    Job.objects.filter(pk=new.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert reconcile_expired() == 1
    assert reconcile_import_storage() == 1
    execute_import(str(new.pk))
    new.refresh_from_db()
    assert new.status == "failed" and new.snapshot_id is None
    assert Snapshot.objects.count() == 1
    assert len(list((storage_root() / "snapshots").iterdir())) == 1
    assert (
        source_content(SourceFile.objects.select_related("snapshot").get(), 1, 2)
        == "one\ntwo\n"
    )


def test_scanner_preserves_active_upload_and_cleans_abandoned_stage() -> None:
    identifier = uuid.uuid4()
    with stage_lock(identifier, create=True) as stage:
        assert stage is not None
        (stage / "archive.zip").write_bytes(b"partial")
        assert reconcile_import_storage() == 0
        assert stage.exists()
    assert reconcile_import_storage() == 1
    assert reconcile_import_storage() == 0


def test_commit_acknowledgment_failure_cannot_delete_success() -> None:
    from apps.jobs.services import complete_import

    job = submitted()

    def uncertain(*args: Any, **kwargs: Any) -> bool:
        complete_import(*args, **kwargs)
        raise DatabaseError("synthetic-ack-failure")

    with patch("apps.projects.services.jobs.complete_import", side_effect=uncertain):
        execute_import(str(job.pk))
    job.refresh_from_db()
    assert job.status == "succeeded"
    assert (
        source_content(SourceFile.objects.select_related("snapshot").get(), 1, 2)
        == "one\ntwo\n"
    )


def test_expiration_during_publish_rejects_late_result() -> None:
    from apps.projects.storage import publish_directory

    job = submitted()
    now = timezone.now()
    published = False

    def slow(*args: Any, **kwargs: Any) -> Path:
        nonlocal published
        result = publish_directory(*args, **kwargs)
        published = True
        return result

    with (
        patch("apps.projects.services.publish_directory", side_effect=slow),
        patch(
            "apps.jobs.services.timezone.now",
            side_effect=lambda: now + timedelta(seconds=1000 if published else 0),
        ),
    ):
        execute_import(str(job.pk))
    job.refresh_from_db()
    assert job.status == "failed" and not Snapshot.objects.exists()
    assert job.error is not None and job.error["code"] == "EXECUTION_TIMEOUT"
    assert not list((storage_root() / "snapshots").iterdir())


def test_filtered_files_never_enter_manifest_or_read_api() -> None:
    job = submitted(
        data=zip_bytes(
            {
                "a.py": b"allowed",
                ".env": b"synthetic-excluded",
                "node_modules/a.py": b"synthetic-excluded",
                "binary.py": b"\x00",
            }
        )
    )
    execute_import(str(job.pk))
    snapshot = Snapshot.objects.get()
    assert snapshot.summary["excluded"] == 2 and snapshot.summary["skipped"] == 1
    assert list(snapshot.files.values_list("file_path", flat=True)) == ["a.py"]
    for path in (storage_root() / "snapshots").rglob("*"):
        if path.is_file():
            assert b"synthetic-excluded" not in path.read_bytes()


def test_controlled_read_rejects_wrong_snapshot_lines_missing_and_tampered() -> None:
    first, second = submitted(), submitted()
    execute_import(str(first.pk))
    execute_import(str(second.pk))
    source = SourceFile.objects.select_related("snapshot").first()
    assert source is not None
    other = Snapshot.objects.exclude(pk=source.snapshot_id).get()
    client = client_with_token()
    path = f"/api/v1/snapshots/{source.snapshot_id}/files/{source.pk}/content/"
    assert (
        client.get(
            f"/api/v1/snapshots/{other.pk}/files/{source.pk}/content/"
        ).status_code
        == 404
    )
    for query in (
        "start_line=0",
        "start_line=3",
        "start_line=2&end_line=1",
        "start_line=1&start_line=2",
        "path=/etc/passwd",
        "end_line=1.0",
    ):
        assert client.get(path + "?" + query).status_code == 400
    stored = storage_root() / "snapshots" / str(source.snapshot_id) / str(source.pk)
    stored.write_bytes(b"changed")
    assert client.get(path).status_code == 409
    stored.unlink()
    assert client.get(path).status_code == 409
    stored.symlink_to("/etc/hosts")
    assert client.get(path).status_code == 409


def test_sparse_line_read_and_maximum_range() -> None:
    job = submitted(
        data=zip_bytes({"a.py": "".join(f"行{i}\n" for i in range(1, 1001)).encode()})
    )
    execute_import(str(job.pk))
    source = SourceFile.objects.select_related("snapshot").get()
    assert source_content(source, 257, 259) == "行257\n行258\n行259\n"
    client = client_with_token()
    path = f"/api/v1/snapshots/{source.snapshot_id}/files/{source.pk}/content/"
    response = client.get(path + "?start_line=801")
    assert response.status_code == 200 and response.json()["end_line"] == 1000
    assert client.get(path + "?end_line=501").status_code == 400


def test_actual_celery_redis_delivery() -> None:
    from celery.contrib.testing.worker import start_worker

    import apps.projects.tasks  # noqa: F401
    from config.celery import app

    queue = "m2-t01-" + uuid.uuid4().hex
    original_send = app.send_task

    def send(*args: Any, **kwargs: Any) -> Any:
        return original_send(*args, **kwargs, queue=queue)

    with start_worker(
        app, pool="solo", queues=[queue], perform_ping_check=False, shutdown_timeout=10
    ):
        with patch("apps.jobs.services.app.send_task", side_effect=send):
            job = submit_import(project(), uuid.uuid4(), upload())[0]
        deadline = time.monotonic() + 10
        while job.status in ("queued", "running") and time.monotonic() < deadline:
            time.sleep(0.1)
            job.refresh_from_db()
        assert job.status == "succeeded"
        assert (
            source_content(SourceFile.objects.select_related("snapshot").get(), 1, 2)
            == "one\ntwo\n"
        )
