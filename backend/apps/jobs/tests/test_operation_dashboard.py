import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.analysis.models import AnalysisRequest
from apps.jobs.models import DeletionRequest, OperationLog
from apps.jobs.operation_export import csv_text
from apps.jobs.tests.test_jobs import client_with_token, create_job, create_snapshot
from apps.projects.models import ImportRequest, SourceFile

pytestmark = pytest.mark.django_db
PATH = "/api/v1/operation-logs/"
NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def record(result: str, *, days: int = 1, **fields: object) -> OperationLog:
    at = NOW - timedelta(days=days)
    row = OperationLog.objects.create(
        operation="analysis",
        result=result,
        events=[{"result": result, "at": at.isoformat()}],
        **fields,
    )
    OperationLog.objects.filter(pk=row.pk).update(created_at=at - timedelta(minutes=1))
    row.refresh_from_db()
    return row


def test_statistics_cover_complete_query_and_ignore_result_view_and_page() -> None:
    for _ in range(25):
        record("succeeded", project_name="目标")
    record("failed", project_name="目标")
    record("rejected", project_name="目标")
    record("replayed", project_name="目标")
    record("running", project_name="目标")
    record("accepted", project_name="目标")
    record("submitted", project_name="目标")
    record("failed", days=8, project_name="目标")
    record("succeeded", days=8, project_name="其他")
    client = client_with_token()
    filters: dict[str, str] = {
        "q": "目标",
        "result": "failed",
        "page": "99",
        "page_size": "1",
    }
    with (
        patch("apps.jobs.api.operation_views.timezone.now", return_value=NOW),
        CaptureQueriesContext(connection) as queries,
    ):
        response = client.get(PATH + "statistics/", filters)
    assert response.status_code == 200
    data = response.json()
    assert (
        data["count"] == 32 and data["failed_count"] == 2 and data["active_count"] == 3
    )
    assert data["recent_success_rate"] == 96.15 and data["previous_success_rate"] == 0
    assert data["success_rate_change_pp"] == 96.15
    assert len(data["trend"]) == 7
    assert not any(
        item["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for item in queries.captured_queries
    )
    with patch("apps.jobs.api.operation_views.timezone.now", return_value=NOW):
        empty = client.get(
            PATH + "statistics/", {"q": "不存在", "view": "active"}
        ).json()
    assert empty["count"] == 0 and empty["recent_success_rate"] is None


def test_window_boundaries_and_missing_end_times_are_not_invented() -> None:
    record("succeeded", days=7)
    record("failed", days=14)
    OperationLog.objects.create(operation="analysis", result="failed", events=[])
    with patch("apps.jobs.api.operation_views.timezone.now", return_value=NOW):
        data = client_with_token().get(PATH + "statistics/").json()
    assert data["recent_success_rate"] == 100
    assert data["previous_success_rate"] == 0
    assert data["failed_count"] == 2


def test_status_groups_and_stable_order_include_only_their_declared_results() -> None:
    first, second = record("failed"), record("failed")
    record("rejected")
    for result in ("submitted", "accepted", "running"):
        record(result)
    client = client_with_token()
    filters: dict[str, str] = {
        "view": "failed",
        "ordering": "started_at",
        "page_size": "1",
    }
    page = client.get(PATH, filters).json()
    assert page["count"] == 2 and page["results"][0]["id"] == str(first.pk)
    assert client.get(page["next"]).json()["results"][0]["id"] == str(second.pk)
    assert client.get(PATH, {"view": "active"}).json()["count"] == 3
    assert client.get(PATH, {"view": "failed", "result": "rejected"}).status_code == 400
    assert client.get(PATH, {"ordering": "private"}).status_code == 400


def test_retry_capabilities_require_available_original_inputs() -> None:
    snapshot = create_snapshot()
    scan = create_job(kind="source_scan", status="failed", snapshot_id=snapshot.pk)
    scan_log = record(
        "failed", job=scan, snapshot_id=snapshot.pk, project_id=snapshot.project_id
    )
    missing = create_job(kind="analysis", status="failed", snapshot_id=snapshot.pk)
    missing_log = record("failed", job=missing)
    import_job = create_job(kind="import", source_kind="folder", status="failed")
    ImportRequest.objects.create(
        job=import_job,
        project=snapshot.project,
        storage_id=uuid.uuid4(),
        source_kind="folder",
    )
    import_log = record("failed", job=import_job)
    record("replayed", job=scan)
    record("failed", job=create_job(kind="lab", status="failed"))
    record(
        "failed",
        job=create_job(
            kind="source_scan",
            status="failed",
            snapshot_id=snapshot.pk,
            result_deleted_at=NOW,
        ),
    )
    client = client_with_token()
    data = client.get(PATH, {"view": "retryable"}).json()
    assert {row["id"]: row["retry_action"] for row in data["results"]} == {
        str(scan_log.pk): "direct",
        str(import_log.pk): "select_folder",
    }
    assert client.get(f"{PATH}{missing_log.pk}/").json()["retry_action"] == "none"
    snapshot.project.deletion_request_id = uuid.uuid4()
    snapshot.project.save(update_fields=["deletion_request_id"])
    assert client.get(PATH, {"view": "retryable"}).json()["count"] == 0


def test_analysis_and_cleanup_retry_require_root_and_current_attempt() -> None:
    snapshot = create_snapshot()
    job = create_job(kind="analysis", status="failed", snapshot_id=snapshot.pk)
    AnalysisRequest.objects.create(job=job, snapshot=snapshot, root_urlconf="urls.py")
    row = record("failed", job=job)
    client = client_with_token()
    assert client.get(f"{PATH}{row.pk}/").json()["retry_action"] == "none"
    SourceFile.objects.create(
        id=uuid.uuid4(),
        snapshot=snapshot,
        file_path="urls.py",
        sha256="a" * 64,
        size_bytes=1,
        line_count=1,
        line_offsets=[0],
    )
    assert client.get(f"{PATH}{row.pk}/").json()["retry_action"] == "direct"
    cleanup = create_job(kind="delete", status="failed")
    deletion = DeletionRequest.objects.create(
        initial_job=cleanup,
        current_job=cleanup,
        target_type="project",
        target_id=snapshot.project_id,
        project_id=snapshot.project_id,
    )
    cleanup_row = record("failed", job=cleanup)
    assert (
        client.get(f"{PATH}{cleanup_row.pk}/").json()["retry_action"]
        == "continue_cleanup"
    )
    deletion.current_job = create_job(
        kind="delete", status="queued", previous_job=cleanup
    )
    deletion.save(update_fields=["current_job"])
    assert client.get(f"{PATH}{cleanup_row.pk}/").json()["retry_action"] == "none"


def test_export_uses_all_filtered_rows_quotes_text_and_protects_formulas() -> None:
    for number in range(23):
        record(
            "failed",
            object_name=' =HYPERLINK("x")' if number == 0 else f"中文,{number}\n第二行",
            project_name="目标",
            request_id="private-request",
            error_code="SAFE_CODE",
        )
    record("succeeded", project_name="其他")
    response = client_with_token().get(
        PATH + "export/", {"q": "目标", "view": "failed", "ordering": "started_at"}
    )
    assert response.status_code == 200 and response.content.startswith(b"\xef\xbb\xbf")
    text = response.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    assert len(rows) == 24 and rows[1][3].startswith("' =")
    assert rows[2][3] == "中文,1\n第二行"
    assert (
        "private-request" not in text
        and "events" not in text
        and "idempotency" not in text
    )
    assert response["Content-Type"].startswith("text/csv")
    assert client_with_token().get(PATH + "export/", {"page": 1}).status_code == 400


def test_export_limits_fail_before_csv_response_without_truncating() -> None:
    record("failed")
    record("failed")
    client = client_with_token()
    with patch("apps.jobs.operation_export.MAX_EXPORT_ROWS", 1):
        response = client.get(PATH + "export/")
    assert (
        response.status_code == 413
        and response.json()["code"] == "EXPORT_LIMIT_EXCEEDED"
    )
    with patch("apps.jobs.operation_export.MAX_EXPORT_BYTES", 20):
        response = client.get(PATH + "export/")
    assert (
        response.status_code == 413
        and response.json()["code"] == "EXPORT_LIMIT_EXCEEDED"
    )


def test_export_real_record_limit_accepts_10000_and_rejects_10001() -> None:
    records = OperationLog.objects.bulk_create(
        [OperationLog(operation="analysis", result="succeeded") for _ in range(10_000)],
        batch_size=1000,
    )
    client = client_with_token()
    response = client.get(PATH + "export/", {"ordering": "started_at"})
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows) == 10_001
    assert {row[0] for row in rows[1:]} == {str(row.display_id) for row in records}

    OperationLog.objects.create(operation="analysis", result="succeeded")
    response = client.get(PATH + "export/")
    assert response.status_code == 413
    assert response.json()["code"] == "EXPORT_LIMIT_EXCEEDED"
    assert not response.has_header("Content-Disposition")
    assert response["Content-Type"].startswith("application/json")


def test_export_real_byte_limit_accepts_exactly_10_mib_and_rejects_one_more() -> None:
    records = OperationLog.objects.bulk_create(
        [
            OperationLog(
                operation="analysis",
                result="succeeded",
                project_name="项" * 150,
                object_name="象" * 150,
            )
            for _ in range(9000)
        ],
        batch_size=1000,
    )
    client = client_with_token()
    response = client.get(PATH + "export/")
    assert response.status_code == 200
    limit = 10 * 1024 * 1024
    remaining = limit - len(response.content)
    assert remaining > 0

    # 只补合法名称文本，按实际 UTF-8 字节数达到边界，不替换生产容量常量。
    for row in records:
        for field in ("project_name", "object_name"):
            value = getattr(row, field)
            size = min(remaining, (200 - len(value)) * 3)
            triples, remainder = divmod(size, 3)
            padding = "补" * triples + (
                "x" if remainder == 1 else "é" if remainder else ""
            )
            setattr(row, field, value + padding)
            remaining -= size
    assert remaining == 0
    assert all(
        len(row.project_name) <= 200 and len(row.object_name) <= 200 for row in records
    )
    OperationLog.objects.bulk_update(
        records, ["project_name", "object_name"], batch_size=500
    )

    response = client.get(PATH + "export/")
    assert response.status_code == 200 and len(response.content) == limit
    assert (
        sum(1 for _ in csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        == 9001
    )

    last = records[-1]
    assert len(last.object_name) < 200
    OperationLog.objects.filter(pk=last.pk).update(object_name=last.object_name + "x")
    response = client.get(PATH + "export/")
    assert response.status_code == 413
    assert response.json()["code"] == "EXPORT_LIMIT_EXCEEDED"
    assert not response.has_header("Content-Disposition")
    assert response["Content-Type"].startswith("application/json")


def test_export_empty_result_contains_only_bom_and_header() -> None:
    record("succeeded", project_name="保留项目")
    response = client_with_token().get(PATH + "export/", {"q": "不存在的项目"})
    expected = (
        '"日志编号","操作类型","项目","操作对象","结果","来源",'
        '"开始时间","结束时间","耗时（秒）","错误码","结果已删除"\r\n'
    )
    assert response.status_code == 200
    assert response.content == b"\xef\xbb\xbf" + expected.encode("utf-8")


@pytest.mark.parametrize(
    "value",
    ["=1+1", "+SUM(1,2)", "-1+2", "@SUM(1,2)", "\ttext", "\ntext", "\rtext", " \t=1+1"],
)
def test_export_formula_prefixes_are_literal_text(value: str) -> None:
    protected = csv_text(value)
    assert protected == "'" + value
    output = io.StringIO(newline="")
    csv.writer(output, quoting=csv.QUOTE_ALL).writerow([protected])
    assert list(csv.reader(io.StringIO(output.getvalue())))[0] == ["'" + value]


def test_related_and_history_do_not_cross_context_or_guess_names() -> None:
    owner = uuid.uuid4()
    parent = create_job(kind="import", status="succeeded")
    current = create_job(kind="source_scan", status="failed", parent_job=parent)
    next_job = create_job(
        kind="source_scan", status="queued", previous_job=current, parent_job=parent
    )
    parent_log = record("succeeded", job=parent, project_id=owner)
    current_log = record("failed", job=current, project_id=owner)
    next_log = record("accepted", job=next_job, project_id=owner)
    old = record("succeeded", days=2, project_id=owner, object_name="同名")
    record("succeeded", days=2, project_id=uuid.uuid4(), object_name="同名")
    client = client_with_token()
    related = client.get(f"{PATH}{current_log.pk}/related/").json()
    assert {row["id"]: row["relation"] for row in related["results"]} == {
        str(parent_log.pk): "parent",
        str(next_log.pk): "retry",
    }
    history = client.get(f"{PATH}{current_log.pk}/history/", {"page_size": 1}).json()
    assert history["count"] == 2
    assert str(old.pk) in {
        row["id"]
        for row in client.get(f"{PATH}{current_log.pk}/history/").json()["results"]
    }
    orphan = record("failed")
    assert client.get(f"{PATH}{orphan.pk}/history/").json()["count"] == 0
