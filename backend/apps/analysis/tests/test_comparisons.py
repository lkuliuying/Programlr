"""验证对比新增任务退役，已存比较及引用仍可只读校验。"""

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
    prepare_input,
    submit_comparison,
)
from apps.analysis.diffs.types import COMPARISON_VERSION, ComparisonFailed
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
from common.errors import ApiProblem

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


def submit(
    base: Snapshot,
    target: Snapshot,
    paired: bool = False,
    *,
    analyses: tuple[Analysis, Analysis] | None = None,
) -> Job:
    """构造升级前已存在的比较请求，不通过已退役服务写入。"""
    selected = list(analyses or [])
    if paired and not selected:
        for snapshot in (base, target):
            job = submitted(snapshot)
            execute_analysis(str(job.pk))
            selected.append(Analysis.objects.get(job=job))
    job = Job.objects.create(
        kind="snapshot_comparison",
        scope=uuid.uuid4().hex,
        snapshot_id=target.pk,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
        status=Job.Status.QUEUED,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    SnapshotComparisonRequest.objects.create(
        job=job,
        project=base.project,
        base_snapshot=base,
        target_snapshot=target,
        base_analysis=selected[0] if selected else None,
        target_analysis=selected[1] if selected else None,
    )
    return job


def publish_history(job: Job) -> SnapshotComparison:
    """纯差异算法提供历史夹具值，直接落库模拟升级前已有成功记录。"""
    record = SnapshotComparisonRequest.objects.select_related(
        "base_snapshot", "target_snapshot", "base_analysis", "target_analysis"
    ).get(job=job)
    data = compare(prepare_input(record))
    result = SnapshotComparison.objects.create(
        request=record,
        comparison_version=COMPARISON_VERSION,
        summary=data["summary"],
        data=data,
    )
    Job.objects.filter(pk=job.pk).update(
        status=Job.Status.SUCCEEDED,
        stage="completed",
        result_url=DETAIL.format(comparison_id=record.pk),
    )
    return result


def test_retired_creation_and_historical_files_api_pairing(
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
        assert first.status_code == 410 and first.json()["code"] == "FEATURE_RETIRED"
        assert_response(first, schema, PATH, "post")
        again = client.post(path, body, format="json", HTTP_IDEMPOTENCY_KEY=key)
        assert again.status_code == 410
        dispatch.assert_not_called()
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
        assert changed.status_code == 410
    assert (
        not SnapshotComparisonRequest.objects.exists()
        and not SnapshotComparison.objects.exists()
    )
    historical = submit(base, target, analyses=(base_analysis, target_analysis))
    record = SnapshotComparisonRequest.objects.get(job=historical)
    before_history = client.get(path)
    assert_response(before_history, schema, PATH)
    assert before_history.json()["results"][0]["summary"] is None
    assert (
        client.get(DETAIL.format(comparison_id=record.pk)).json()["code"]
        == "COMPARISON_NOT_READY"
    )
    publish_history(historical)
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
    publish_history(job)
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
    publish_history(second)
    assert SnapshotComparison.objects.get(request__job=second).summary == result.summary


def test_retirement_precedes_snapshot_read_retry_and_late_publication(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    base, target = snapshots
    job = submit(base, target)
    source = base.files.first()
    assert source is not None
    location = storage_root() / "snapshots" / str(base.pk) / str(source.pk)
    original = location.read_bytes()
    location.write_bytes(b"corrupt")
    with (
        patch("apps.analysis.diffs.runner.run_comparison") as parser,
        patch("apps.analysis.diffs.services.prepare_input") as read_sources,
    ):
        execute_comparison(str(job.pk))
        parser.assert_not_called()
        read_sources.assert_not_called()
    job.refresh_from_db()
    assert job.error is not None
    assert job.status == "failed" and job.error["code"] == "FEATURE_RETIRED"
    assert not SnapshotComparison.objects.exists()
    location.write_bytes(original)
    before = Job.objects.count()
    with (
        patch("apps.jobs.services.app.send_task") as queue,
        pytest.raises(ApiProblem) as error,
    ):
        submit_retry(job, uuid.uuid4())
    assert (
        error.value.machine_code == "FEATURE_RETIRED" and Job.objects.count() == before
    )
    queue.assert_not_called()
    another = submit(base, target)

    with patch(
        "apps.analysis.diffs.runner.run_comparison",
        side_effect=AssertionError("退役任务不可计算"),
    ) as parser:
        execute_comparison(str(another.pk))
        parser.assert_not_called()
    another.refresh_from_db()
    assert (
        another.status == "failed"
        and not SnapshotComparison.objects.filter(request__job=another).exists()
    )


@pytest.mark.parametrize(
    "reason", ["output_limit", "comparison_timeout", "file_line_limit"]
)
def test_retired_worker_never_reaches_parser_limits_or_partial_publication(
    snapshots: tuple[Snapshot, Snapshot], reason: str
) -> None:
    job = submit(*snapshots)
    with patch(
        "apps.analysis.diffs.runner.run_comparison",
        side_effect=ComparisonFailed(reason),
    ) as parser:
        execute_comparison(str(job.pk))
        parser.assert_not_called()
    job.refresh_from_db()
    assert job.error is not None
    assert job.status == "failed" and job.error["code"] == "FEATURE_RETIRED"
    assert (
        not SnapshotComparison.objects.exists()
        and SnapshotComparisonRequest.objects.filter(job=job).exists()
    )


def test_retired_worker_never_reaches_publish_or_retry(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    job = submit(*snapshots)
    with patch(
        "apps.analysis.diffs.services.SnapshotComparison.objects.create",
        side_effect=DatabaseError("合成写入失败"),
    ) as publish:
        execute_comparison(str(job.pk))
        publish.assert_not_called()
    job.refresh_from_db()
    assert job.status == "failed" and not SnapshotComparison.objects.exists()
    before = Job.objects.count()
    with (
        patch("apps.jobs.services.app.send_task") as queue,
        pytest.raises(ApiProblem) as error,
    ):
        submit_retry(job, uuid.uuid4())
    queue.assert_not_called()
    assert (
        error.value.machine_code == "FEATURE_RETIRED" and Job.objects.count() == before
    )


def test_retired_same_key_concurrent_creation_never_delivers_queue(
    snapshots: tuple[Snapshot, Snapshot],
) -> None:
    base, target = snapshots
    key = uuid.uuid4()

    def create(_: int) -> str:
        close_old_connections()
        try:
            with pytest.raises(ApiProblem) as error:
                submit_comparison(base.project, key, base, target, None, None)
            return error.value.machine_code
        finally:
            close_old_connections()

    with patch("apps.jobs.services.app.send_task") as send:
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(create, range(2)))
    assert (
        set(ids) == {"FEATURE_RETIRED"}
        and send.call_count == 0
        and SnapshotComparisonRequest.objects.count() == 0
    )
    with (
        patch(
            "apps.jobs.services.app.send_task",
            side_effect=OperationalError("合成队列故障"),
        ) as queue,
        pytest.raises(ApiProblem) as error,
    ):
        submit_comparison(base.project, uuid.uuid4(), base, target, None, None)
    queue.assert_not_called()
    assert (
        error.value.machine_code == "FEATURE_RETIRED"
        and not SnapshotComparisonRequest.objects.exists()
    )


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
            == 410
        )
    other = imported()
    assert (
        client.post(
            path,
            {**body, "target_snapshot_id": str(other.pk)},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        ).status_code
        == 410
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
        == 410
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
        result = publish_history(job)
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
