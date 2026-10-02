"""在 PostgreSQL 和实际差异进程中验证对比任务、API 和失败恢复。"""

import copy
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.db import DatabaseError, close_old_connections
from django.test import override_settings
from django.utils import timezone
from kombu.exceptions import OperationalError
from rest_framework.test import APIClient

from apps.analysis.diffs.engine import compare
from apps.analysis.diffs.services import (
    execute_comparison,
    submit_comparison,
)
from apps.analysis.diffs.types import ComparisonData, ComparisonFailed, ComparisonInput
from apps.analysis.models import Analysis, SnapshotComparison, SnapshotComparisonRequest
from apps.analysis.services import execute_analysis
from apps.analysis.tests.test_analysis import imported, submitted
from apps.analysis.tests.test_parser import fixture_sources
from apps.explanations.models import ContextPreview, Explanation
from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.jobs.retries import submit_retry
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from apps.projects.models import Snapshot
from apps.projects.services import execute_import, source_content, submit_import
from apps.projects.storage import storage_root
from apps.projects.tests.test_archive import zip_bytes
from apps.projects.tests.test_projects import upload

pytestmark = pytest.mark.django_db(transaction=True)
PATH = "/api/v1/projects/{project_id}/snapshot-comparisons/"
DETAIL = "/api/v1/snapshot-comparisons/{comparison_id}/"
FILES = DETAIL + "files/"
FILE = FILES + "{change_id}/"


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


@pytest.fixture
def snapshots() -> tuple[Snapshot, Snapshot]:
    base = imported({"old.py": b"x=1\n", "entry.ts": b"fetch('/api/tasks/');\n"})
    sources = {
        source.file_path: source.content.encode() for source in fixture_sources()
    }
    sources["views.py"] = b"\n" + sources["views.py"]
    sources.update({"new.py": b"x=1\n", "entry.ts": b"fetch('/api/tasks/');\n"})
    with patch("apps.jobs.services.app.send_task"):
        job = submit_import(base.project, uuid.uuid4(), upload(zip_bytes(sources)))[0]
    execute_import(str(job.pk))
    return base, Snapshot.objects.get(job=job)


def submit(base: Snapshot, target: Snapshot, paired: bool = False) -> Job:
    analyses = []
    if paired:
        for snapshot in (base, target):
            job = submitted(snapshot)
            execute_analysis(str(job.pk))
            analyses.append(Analysis.objects.get(job=job))
    with patch("apps.jobs.services.app.send_task"):
        return submit_comparison(
            base.project,
            uuid.uuid4(),
            base,
            target,
            analyses[0] if paired else None,
            analyses[1] if paired else None,
        )[0]


def test_actual_pipeline_files_api_history_pairing_and_idempotency(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    base, target = snapshots
    analysis_job = submitted(base)
    execute_analysis(str(analysis_job.pk))
    base_analysis = Analysis.objects.get(job=analysis_job)
    target_job = submitted(target)
    execute_analysis(str(target_job.pk))
    target_analysis = Analysis.objects.get(job=target_job)
    client, schema, key = client_with_token(), contract_schema(), str(uuid.uuid4())
    path = PATH.format(project_id=base.project_id)
    body = {
        "base_snapshot_id": str(base.pk),
        "target_snapshot_id": str(target.pk),
        "base_analysis_id": str(base_analysis.pk),
        "target_analysis_id": str(target_analysis.pk),
    }
    with patch("apps.jobs.services.app.send_task") as dispatch:
        first = client.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY=key)
        assert first.status_code == 202
        assert_response(first, schema, PATH, "post")
        again = client.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY=key)
        assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
        assert (
            dispatch.call_count == 1
            and dispatch.call_args.args[0] == "analysis.compare"
        )
        changed = client.post(
            path,
            {
                **body,
                "target_snapshot_id": str(base.pk),
                "target_analysis_id": str(base_analysis.pk),
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert changed.status_code == 409
    record = SnapshotComparisonRequest.objects.get(job_id=first.json()["id"])
    before_history = client.get(path)
    assert_response(before_history, schema, PATH)
    assert before_history.json()["results"][0]["summary"] is None
    assert (
        client.get(DETAIL.format(comparison_id=record.pk)).json()["code"]
        == "COMPARISON_NOT_READY"
    )
    execute_comparison(first.json()["id"])
    record.job.refresh_from_db()
    assert record.job.status == "succeeded", record.job.error
    assert record.job.snapshot_id == target.pk
    assert record.job.result_url == DETAIL.format(comparison_id=record.pk)
    response = client.get(record.job.result_url)
    assert_response(response, schema, DETAIL)
    data = response.json()
    assert data["comparability"] == "comparable"
    assert (
        data["summary"]["added"]
        == data["summary"]["deleted"]
        == data["summary"]["modified"]
        == 1
    )
    assert all(item["change_type"] == "unchanged" for item in data["interfaces"])
    page = client.get(FILES.format(comparison_id=record.pk), {"page_size": "2"})
    assert_response(page, schema, FILES)
    assert page.json()["count"] == sum(data["summary"].values()) and page.json()["next"]
    files = SnapshotComparison.objects.get(request=record).data["files"]
    modified = next(file for file in files if file["file_path"] == "views.py")
    detail = client.get(FILE.format(comparison_id=record.pk, change_id=modified["id"]))
    assert_response(detail, schema, FILE)
    assert "+\n" in detail.json()["diff"]
    assert detail.json()["base_ref"]["snapshot_id"] == str(base.pk)
    assert detail.json()["target_ref"]["snapshot_id"] == str(target.pk)
    with patch(
        "apps.analysis.diffs.services.execute_comparison",
        side_effect=AssertionError("读取不可执行"),
    ):
        history = client.get(path)
        assert (
            history.status_code == 200
            and history.json()["results"][0]["summary"] == data["summary"]
        )
    execute_comparison(str(record.job_id))
    assert SnapshotComparison.objects.count() == 1
    assert (
        client.get(
            FILE.format(comparison_id=record.pk, change_id=uuid.uuid4())
        ).status_code
        == 404
    )
    assert (
        client.get(FILES.format(comparison_id=record.pk), {"page": "999"}).status_code
        == 404
    )
    assert (
        client.get(DETAIL.format(comparison_id=record.pk), {"unknown": "1"}).status_code
        == 400
    )


def test_file_only_identical_normalized_newline_and_history_reads(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    base, _ = snapshots
    job = submit(base, base)
    execute_comparison(str(job.pk))
    result = SnapshotComparison.objects.get(request__job=job)
    assert result.data["comparability"] == "files_only"
    assert result.summary["unchanged"] == base.files.count()
    assert not any(file["diff"] for file in result.data["files"])
    contents = {
        source.file_path: source_content(source, 1, source.line_count)
        .replace("\n", "\r\n")
        .encode()
        for source in base.files.select_related("snapshot")
    }
    with patch("apps.jobs.services.app.send_task"):
        imported_job = submit_import(
            base.project, uuid.uuid4(), upload(zip_bytes(contents))
        )[0]
    execute_import(str(imported_job.pk))
    target = Snapshot.objects.get(job=imported_job)
    second = submit(base, target)
    execute_comparison(str(second.pk))
    assert SnapshotComparison.objects.get(request__job=second).summary == result.summary


def test_corrupt_snapshot_fail_retry_and_late_result_cannot_publish(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    base, target = snapshots
    job = submit(base, target)
    source = base.files.first()
    assert source is not None
    location = storage_root() / "snapshots" / str(base.pk) / str(source.pk)
    original = location.read_bytes()
    location.write_bytes(b"corrupt")
    execute_comparison(str(job.pk))
    job.refresh_from_db()
    assert job.error is not None
    assert job.status == "failed" and job.error["code"] == "SNAPSHOT_NOT_READY"
    assert not SnapshotComparison.objects.exists()
    location.write_bytes(original)
    with patch("apps.jobs.services.app.send_task"):
        retry = submit_retry(job, uuid.uuid4())[0]
    assert retry.previous_job_id == job.pk and retry.snapshot_id == target.pk
    execute_comparison(str(retry.pk))
    retry.refresh_from_db()
    assert retry.status == "succeeded" and SnapshotComparison.objects.count() == 1
    another = submit(base, target)

    def late(input: ComparisonInput) -> ComparisonData:
        value = compare(input)
        Job.objects.filter(pk=another.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        jobs.reconcile_expired()
        return value

    with patch("apps.analysis.diffs.services.run_comparison", side_effect=late):
        execute_comparison(str(another.pk))
    another.refresh_from_db()
    assert (
        another.status == "failed"
        and not SnapshotComparison.objects.filter(request__job=another).exists()
    )


@pytest.mark.parametrize(
    "reason", ["output_limit", "comparison_timeout", "file_line_limit"]
)
def test_limit_failure_retains_request_and_never_publishes_partial(
    snapshots: tuple[Snapshot, Snapshot], reason: str
) -> None:
    job = submit(*snapshots)
    with patch(
        "apps.analysis.diffs.services.run_comparison",
        side_effect=ComparisonFailed(reason),
    ):
        execute_comparison(str(job.pk))
    job.refresh_from_db()
    assert job.error is not None
    assert job.status == "failed" and job.error["details"]["reason"] == reason
    assert (
        not SnapshotComparison.objects.exists()
        and SnapshotComparisonRequest.objects.filter(job=job).exists()
    )


def test_publish_database_error_rolls_back_then_explicit_retry(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    job = submit(*snapshots)
    with patch(
        "apps.analysis.diffs.services.SnapshotComparison.objects.create",
        side_effect=DatabaseError("合成写入失败"),
    ):
        execute_comparison(str(job.pk))
    job.refresh_from_db()
    assert job.status == "failed" and not SnapshotComparison.objects.exists()
    with patch("apps.jobs.services.app.send_task"):
        retry = submit_retry(job, uuid.uuid4())[0]
    execute_comparison(str(retry.pk))
    assert SnapshotComparison.objects.filter(request__job=retry).exists()


def test_same_key_concurrent_creation_and_queue_delivery_failure(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    base, target = snapshots
    key = uuid.uuid4()

    def create(_: int) -> uuid.UUID:
        close_old_connections()
        try:
            return submit_comparison(base.project, key, base, target, None, None)[0].pk
        finally:
            close_old_connections()

    with patch("apps.jobs.services.app.send_task") as send:
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(create, range(2)))
    assert (
        ids[0] == ids[1]
        and send.call_count == 1
        and SnapshotComparisonRequest.objects.count() == 1
    )
    with patch(
        "apps.jobs.services.app.send_task", side_effect=OperationalError("合成队列故障")
    ):
        job, created, published = submit_comparison(
            base.project, uuid.uuid4(), base, target, None, None
        )
    assert created and not published and job.status == "failed"
    assert SnapshotComparisonRequest.objects.filter(job=job).exists()


def test_scope_pairing_strict_input_and_origin_protection(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    base, target = snapshots
    client, path = client_with_token(), PATH.format(project_id=base.project_id)
    body = {"base_snapshot_id": str(base.pk), "target_snapshot_id": str(target.pk)}
    for change in (
        {"base_snapshot_id": None},
        {"base_snapshot_id": True},
        {"unknown": "1"},
        {"base_analysis_id": str(uuid.uuid4())},
    ):
        assert (
            client.post(
                path,
                {**body, **change},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            ).status_code
            == 400
        )
    other = imported()
    assert (
        client.post(
            path,
            {**body, "target_snapshot_id": str(other.pk)},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        ).status_code
        == 409
    )
    job = submitted(base)
    execute_analysis(str(job.pk))
    analysis = Analysis.objects.get(job=job)
    assert (
        client.post(
            path,
            {
                **body,
                "base_analysis_id": str(analysis.pk),
                "target_analysis_id": str(analysis.pk),
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        ).status_code
        == 409
    )
    assert (
        APIClient(enforce_csrf_checks=True).post(path, body, format="json").status_code
        == 403
    )
    assert client.get(path, {"other": "1"}).status_code == 400
    assert not SnapshotComparisonRequest.objects.exists()


def test_old_explanation_refs_are_read_without_model_and_corrupt_results_fail_closed(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    base, target = snapshots
    analysis_job = submitted(base)
    execute_analysis(str(analysis_job.pk))
    analysis = Analysis.objects.get(job=analysis_job)
    refs, snippets = [], []
    for path in ("models.py", "views.py", "old.py"):
        source = base.files.select_related("snapshot").get(file_path=path)
        ref = {
            "snapshot_id": str(base.pk),
            "file_path": path,
            "start_line": 1,
            "end_line": 1,
        }
        text = source_content(source, 1, 1)
        refs.append(ref)
        snippets.append(
            {
                "id": path,
                "source_ref": ref,
                "content": text,
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    preview = ContextPreview.objects.create(
        analysis=analysis,
        snapshot=base,
        endpoint_index=0,
        idempotency_key=uuid.uuid4(),
        request_digest="a" * 64,
        payload={"snippets": snippets},
        payload_digest="a" * 64,
    )
    explanation_job = jobs.create_explanation_job(
        base.pk, "synthetic-history", uuid.uuid4(), "a" * 64, None
    )[0]
    content = {
        section: [{"kind": "source_fact", "text": "合成历史证据", "source_refs": refs}]
        for section in ("purpose", "evidence", "mechanism", "knowledge", "verification")
    }
    explanation = Explanation.objects.create(
        job=explanation_job, preview=preview, content=content, model="synthetic-history"
    )
    before = copy.deepcopy(explanation.content)
    job = submit(base, target)
    with patch(
        "apps.explanations.adapter.complete", side_effect=AssertionError("不能调用模型")
    ):
        execute_comparison(str(job.pk))
        result = SnapshotComparison.objects.get(request__job=job)
        response = client_with_token().get(DETAIL.format(comparison_id=result.pk))
    assert response.status_code == 200
    saved = response.json()["evidence"][0]
    assert saved["explanation_id"] == str(explanation.pk)
    applicability = {
        item["source_ref"]["file_path"]: item["applicability"]
        for item in saved["references"]
    }
    assert applicability == {
        "models.py": "unchanged",
        "views.py": "review",
        "old.py": "deleted",
    }
    explanation.refresh_from_db()
    assert explanation.content == before
    damaged = copy.deepcopy(result.data)
    damaged["files"][0]["base_ref"]["snapshot_id"] = str(target.pk)
    SnapshotComparison.objects.filter(pk=result.pk).update(data=damaged)
    assert (
        client_with_token().get(DETAIL.format(comparison_id=result.pk)).status_code
        == 500
    )
