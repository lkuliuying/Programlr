import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.test import override_settings

from apps.analysis.models import SnapshotComparison, SnapshotComparisonRequest
from apps.explanations.models import (
    ContextConsent,
    ContextPreview,
    Explanation,
    ExplanationRequest,
)
from apps.jobs.cleanup import execute_deletion, preview, retry_deletion, submit_deletion
from apps.jobs.models import DeletionRequest, Job, OperationLog
from apps.jobs.tests.test_jobs import create_job
from apps.projects.models import Project, Snapshot, SourceFile
from apps.projects.storage import storage_root
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def private_store(tmp_path: Path) -> Iterator[Path]:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "internal")):
        yield tmp_path


def snapshot(project: Project) -> Snapshot:
    identifier = uuid.uuid4()
    job = create_job(kind="import", status="succeeded", snapshot_id=identifier)
    result = Snapshot.objects.create(
        id=identifier,
        project=project,
        job=job,
        name="待清理快照",
        summary={},
        manifest_digest="0" * 64,
    )
    directory = storage_root() / "snapshots" / str(result.pk)
    directory.mkdir()
    source_id = uuid.uuid4()
    (directory / str(source_id)).write_text("internal source marker", encoding="utf-8")
    SourceFile.objects.create(
        id=source_id,
        snapshot=result,
        file_path="urls.py",
        sha256="0" * 64,
        size_bytes=22,
        line_count=1,
        line_offsets=[0],
    )
    return result


def submit(target_type: str, target: Project | Snapshot) -> Job:
    current = preview(target_type, target)
    with patch("apps.jobs.services.app.send_task"):
        return submit_deletion(
            target_type, target.pk, uuid.uuid4(), current["confirmation_digest"]
        )[0]


def test_permanent_cleanup_keeps_original_source_zip_and_task_summary(
    private_store: Path,
) -> None:
    original = private_store / "original-project"
    original.mkdir()
    (original / "urls.py").write_text("original untouched", encoding="utf-8")
    archive = private_store / "original.zip"
    archive.write_bytes(b"original archive")
    project = Project.objects.create(name="永久清理", idempotency_key=uuid.uuid4())
    source = snapshot(project)
    import_job = source.job
    import_job.error = {
        "code": "LEGACY",
        "details": {"source": "private source marker"},
    }
    import_job.save(update_fields=["error"])
    delete = submit("project", project)
    execute_deletion(str(delete.pk))
    delete.refresh_from_db()
    import_job.refresh_from_db()
    assert delete.status == "succeeded" and delete.result_url is None
    assert not Project.objects.filter(pk=project.pk).exists()
    assert not Snapshot.objects.filter(pk=source.pk).exists()
    assert not (storage_root() / "snapshots" / str(source.pk)).exists()
    assert import_job.status == "succeeded" and import_job.result_deleted_at is not None
    assert "private source marker" not in str(import_job.error)
    assert import_job.result_url is None
    assert OperationLog.objects.get(job=delete).result == "succeeded"
    assert (original / "urls.py").read_text(encoding="utf-8") == "original untouched"
    assert archive.read_bytes() == b"original archive"
    assert set(DeletionRequest.objects.get(current_job=delete).inventory) == {"scope"}
    from apps.jobs.tests.test_jobs import client_with_token

    result = client_with_token().get(f"/api/v1/jobs/{import_job.pk}/")
    assert result.status_code == 200 and result.json()["result_deleted"]
    assert result.json()["result_url"] is None
    log = OperationLog.objects.get(job=delete)
    assert (
        client_with_token().get(f"/api/v1/operation-logs/{log.pk}/").status_code == 200
    )


def test_partial_file_failure_stays_isolated_and_explicit_retry_finishes(
    private_store: Path,
) -> None:
    project = Project.objects.create(name="失败恢复", idempotency_key=uuid.uuid4())
    first, second = snapshot(project), snapshot(project)
    delete = submit("project", project)
    from apps.projects.storage import remove_owned_directory

    calls = 0

    def fail_once(path: Path, parent: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic")
        remove_owned_directory(path, parent)

    with patch("apps.jobs.cleanup.remove_owned_directory", side_effect=fail_once):
        execute_deletion(str(delete.pk))
    delete.refresh_from_db()
    project.refresh_from_db()
    assert delete.status == "failed" and project.deletion_request_id is not None
    assert Snapshot.objects.filter(project=project).count() == 2
    with patch("apps.jobs.services.app.send_task"):
        continued, created, _ = retry_deletion(delete, uuid.uuid4())
    assert created and continued.previous_job_id == delete.pk
    execute_deletion(str(continued.pk))
    continued.refresh_from_db()
    assert continued.status == "succeeded"
    assert not Project.objects.filter(pk=project.pk).exists()
    assert not (storage_root() / "snapshots" / str(first.pk)).exists()
    assert not (storage_root() / "snapshots" / str(second.pk)).exists()


def test_snapshot_cleanup_removes_shared_comparison_and_model_snippets_only_for_target(
    private_store: Path,
) -> None:
    from apps.analysis.diffs.engine import compare
    from apps.analysis.models import Analysis
    from apps.jobs.tests.test_jobs import client_with_token

    project = Project.objects.create(name="跨快照", idempotency_key=uuid.uuid4())
    removed, retained = snapshot(project), snapshot(project)
    analysis_job = create_job(
        kind="analysis", status="succeeded", snapshot_id=removed.pk
    )
    analysis = Analysis.objects.create(
        job=analysis_job,
        snapshot=removed,
        root_urlconf="urls.py",
        rule_version="legacy",
        coverage={},
        endpoints=[],
        diagnostics=[],
    )
    context = ContextPreview.objects.create(
        analysis=analysis,
        snapshot=removed,
        endpoint_index=0,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
        payload={"messages": ["private source marker"]},
        payload_digest="0" * 64,
    )
    consent = ContextConsent.objects.create(
        preview=context, idempotency_key=uuid.uuid4()
    )
    model_job = create_job(
        kind="explanation", status="succeeded", snapshot_id=removed.pk
    )
    ExplanationRequest.objects.create(job=model_job, consent=consent)
    Explanation.objects.create(
        job=model_job,
        preview=context,
        content={"source": "private source marker"},
        model="offline",
    )
    comparison_job = create_job(
        kind="snapshot_comparison", status="succeeded", snapshot_id=retained.pk
    )
    request = SnapshotComparisonRequest.objects.create(
        job=comparison_job,
        project=project,
        base_snapshot=removed,
        target_snapshot=retained,
    )
    SourceFile.objects.filter(snapshot=retained).update(sha256="1" * 64)
    data = compare(
        {
            "comparison_id": str(request.pk),
            "base_snapshot_id": str(removed.pk),
            "target_snapshot_id": str(retained.pk),
            "base_analysis": None,
            "target_analysis": None,
            "evidence": [],
            "files": [
                {
                    "file_path": "urls.py",
                    "base_ref": {
                        "snapshot_id": str(removed.pk),
                        "file_path": "urls.py",
                        "start_line": 1,
                        "end_line": 1,
                    },
                    "target_ref": {
                        "snapshot_id": str(retained.pk),
                        "file_path": "urls.py",
                        "start_line": 1,
                        "end_line": 1,
                    },
                    "base_sha256": "0" * 64,
                    "target_sha256": "1" * 64,
                    "base_content": "private source marker",
                    "target_content": "retained source marker",
                }
            ],
        }
    )
    SnapshotComparison.objects.create(
        request=request,
        comparison_version=data["comparison_version"],
        summary=data["summary"],
        data=data,
    )
    comparison_job.result_url = f"/api/v1/snapshot-comparisons/{request.pk}/"
    comparison_job.save(update_fields=["result_url"])
    assert client_with_token().get(comparison_job.result_url).status_code == 200
    assert "private source marker" in data["files"][0]["diff"]
    delete = submit("snapshot", removed)
    execute_deletion(str(delete.pk))
    delete.refresh_from_db()
    assert delete.status == "succeeded"
    assert Snapshot.objects.filter(pk=retained.pk).exists()
    assert (storage_root() / "snapshots" / str(retained.pk)).exists()
    assert not ContextPreview.objects.filter(pk=context.pk).exists()
    assert not Explanation.objects.filter(job=model_job).exists()
    assert not SnapshotComparisonRequest.objects.filter(pk=request.pk).exists()
    comparison_job.refresh_from_db()
    assert comparison_job.result_deleted_at is not None
    result = client_with_token().get(f"/api/v1/jobs/{comparison_job.pk}/")
    assert result.status_code == 200 and result.json()["result_deleted"]
    assert result.json()["result_url"] is None
    assert (
        client_with_token()
        .get(f"/api/v1/snapshot-comparisons/{request.pk}/")
        .status_code
        == 404
    )


def test_active_jobs_and_stale_preview_do_not_delete_files(private_store: Path) -> None:
    project = Project.objects.create(name="删除边界", idempotency_key=uuid.uuid4())
    source = snapshot(project)
    before = preview("snapshot", source)
    active = create_job(kind="analysis", snapshot_id=source.pk)
    with pytest.raises(ApiProblem) as busy:
        submit_deletion(
            "snapshot", source.pk, uuid.uuid4(), before["confirmation_digest"]
        )
    assert busy.value.machine_code == "RESOURCE_BUSY"
    active.status = "failed"
    active.save(update_fields=["status"])
    with pytest.raises(ApiProblem) as stale:
        submit_deletion(
            "snapshot", source.pk, uuid.uuid4(), before["confirmation_digest"]
        )
    assert stale.value.machine_code == "DELETION_PREVIEW_STALE"
    assert (storage_root() / "snapshots" / str(source.pk)).exists()
    assert not DeletionRequest.objects.exists()


def test_pending_snapshot_cleanup_blocks_whole_project_cleanup(
    private_store: Path,
) -> None:
    project = Project.objects.create(name="隔离范围", idempotency_key=uuid.uuid4())
    source = snapshot(project)
    delete = submit("snapshot", source)
    delete.status = "failed"
    delete.save(update_fields=["status"])
    project.refresh_from_db()
    current = preview("project", project)
    assert not current["can_delete"]
    with pytest.raises(ApiProblem) as busy:
        submit_deletion(
            "project", project.pk, uuid.uuid4(), current["confirmation_digest"]
        )
    assert busy.value.machine_code == "RESOURCE_BUSY"
    assert DeletionRequest.objects.count() == 1


def test_delete_api_confirmation_replay_and_read_isolation(private_store: Path) -> None:
    from apps.jobs.tests.test_jobs import client_with_token

    project = Project.objects.create(name="API清理", idempotency_key=uuid.uuid4())
    source = snapshot(project)
    client, key = client_with_token(), uuid.uuid4()
    current = client.get(f"/api/v1/snapshots/{source.pk}/deletion-preview/")
    assert current.status_code == 200
    body = {"confirmation_digest": current.json()["confirmation_digest"]}
    path = f"/api/v1/snapshots/{source.pk}/"
    with patch("apps.jobs.services.app.send_task") as dispatch:
        result = client.delete(path, body, format="json", HTTP_IDEMPOTENCY_KEY=str(key))
        assert result.status_code == 202
        repeated = client.delete(
            path, body, format="json", HTTP_IDEMPOTENCY_KEY=str(key)
        )
    assert repeated.status_code == 200 and repeated.json()["id"] == result.json()["id"]
    assert dispatch.call_count == 1
    assert client.get(path).status_code == 410
    assert client.get(path).json()["code"] == "RESOURCE_DELETING"
    execute_deletion(result.json()["id"])
    after = client.delete(path, body, format="json", HTTP_IDEMPOTENCY_KEY=str(key))
    assert after.status_code == 200 and after.json()["status"] == "succeeded"
    assert (
        OperationLog.objects.filter(snapshot_id=source.pk, result="replayed").count()
        == 2
    )


def test_concurrent_same_key_cleanup_retry_creates_one_attempt(
    private_store: Path,
) -> None:
    project = Project.objects.create(name="并发恢复", idempotency_key=uuid.uuid4())
    snapshot(project)
    previous = submit("project", project)
    previous.status = "failed"
    previous.save(update_fields=["status"])
    key, barrier = uuid.uuid4(), Barrier(2)

    def retry(_: int) -> tuple[uuid.UUID, bool]:
        close_old_connections()
        try:
            prior = Job.objects.get(pk=previous.pk)
            barrier.wait(timeout=5)
            job, created, _ = retry_deletion(prior, key)
            return job.pk, created
        finally:
            close_old_connections()

    with patch("apps.jobs.services.app.send_task") as dispatch:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(retry, range(2)))
    assert results[0][0] == results[1][0]
    assert sorted(created for _, created in results) == [False, True]
    assert dispatch.call_count == 1
    assert Job.objects.filter(previous_job=previous).count() == 1


def test_concurrent_same_key_delete_start_replays_original(
    private_store: Path,
) -> None:
    from apps.jobs.cleanup import target_object

    project = Project.objects.create(name="并发清理", idempotency_key=uuid.uuid4())
    snapshot(project)
    digest = preview("project", project)["confirmation_digest"]
    key, barrier = uuid.uuid4(), Barrier(2)

    def lock_after_both_requests(
        target_type: str, target_id: uuid.UUID, *, locked: bool = False
    ) -> Project | Snapshot:
        barrier.wait(timeout=5)
        return target_object(target_type, target_id, locked=locked)

    def submit_once(_: int) -> tuple[uuid.UUID, bool]:
        close_old_connections()
        try:
            job, created, _ = submit_deletion("project", project.pk, key, digest)
            return job.pk, created
        finally:
            close_old_connections()

    with (
        patch("apps.jobs.cleanup.target_object", side_effect=lock_after_both_requests),
        patch("apps.jobs.services.app.send_task") as dispatch,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        results = list(pool.map(submit_once, range(2)))
    assert results[0][0] == results[1][0]
    assert sorted(created for _, created in results) == [False, True]
    assert dispatch.call_count == 1
    assert DeletionRequest.objects.count() == 1


def test_preview_digest_detects_internal_file_change_and_never_follows_symlink(
    private_store: Path,
) -> None:
    project = Project.objects.create(name="副本边界", idempotency_key=uuid.uuid4())
    source = snapshot(project)
    directory = storage_root() / "snapshots" / str(source.pk)
    original = private_store / "original-secret.py"
    original.write_text("original unchanged", encoding="utf-8")
    current = preview("snapshot", source)
    (directory / "unexpected.bin").write_bytes(b"changed internal copy")
    with pytest.raises(ApiProblem) as stale:
        submit_deletion(
            "snapshot", source.pk, uuid.uuid4(), current["confirmation_digest"]
        )
    assert stale.value.machine_code == "DELETION_PREVIEW_STALE"
    (directory / "external-link").symlink_to(original)
    delete = submit("snapshot", source)
    execute_deletion(str(delete.pk))
    delete.refresh_from_db()
    assert delete.status == "succeeded"
    assert original.read_text(encoding="utf-8") == "original unchanged"
