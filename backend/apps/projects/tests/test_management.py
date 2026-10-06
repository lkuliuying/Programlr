import uuid
from datetime import timedelta
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.analysis.models import SnapshotPreparation, SourceScan
from apps.jobs.models import Job, OperationLog
from apps.jobs.tests.test_jobs import client_with_token
from apps.projects.models import ImportRequest, Project, Snapshot, SourceFile
from apps.projects.services import create_project

pytestmark = pytest.mark.django_db(transaction=True)


def make_job(kind: str, status: str = "succeeded") -> Job:
    return Job.objects.create(
        kind=kind,
        status=status,
        stage="completed" if status == "succeeded" else status,
        idempotency_key=uuid.uuid4(),
        request_digest="a" * 64,
        expires_at=timezone.now() + timedelta(hours=1),
    )


def make_snapshot(
    owner: Project, name: str, files: tuple[str, ...] = ("app.py",)
) -> Snapshot:
    job = make_job("import")
    snapshot = Snapshot.objects.create(
        id=uuid.uuid4(),
        project=owner,
        job=job,
        name=name,
        manifest_digest="a" * 64,
        summary={
            "entries": len(files),
            "accepted": len(files),
            "excluded": 0,
            "skipped": 0,
            "rejected": 0,
            "declared_bytes": 1,
            "extracted_bytes": 1,
            "reasons": {},
        },
    )
    job.snapshot_id = snapshot.pk
    job.result_url = f"/api/v1/snapshots/{snapshot.pk}/"
    job.save(update_fields=["snapshot_id", "result_url"])
    for path in files:
        SourceFile.objects.create(
            id=uuid.uuid4(),
            snapshot=snapshot,
            file_path=path,
            sha256="a" * 64,
            size_bytes=1,
            line_count=1,
            line_offsets=[0],
        )
    return snapshot


def prepare(
    snapshot: Snapshot,
    status: str,
    declarations: list[dict[str, Any]] | None = None,
    packages: list[dict[str, Any]] | None = None,
) -> SnapshotPreparation:
    job = make_job("source_scan")
    job.snapshot_id = snapshot.pk
    job.save(update_fields=["snapshot_id"])
    roots = [{"file_path": "urls.py"}] if status != "no_root" else []
    scan = SourceScan.objects.create(
        snapshot=snapshot,
        job=job,
        rule_version="fixture",
        result={
            "roots": {
                "candidates": roots,
                "selected_root": "urls.py" if status == "ready" else None,
            },
            "knowledge": {
                "packages": packages or [],
                "declarations": declarations or [],
            },
        },
    )
    job.result_url = f"/api/v1/source-scans/{scan.pk}/"
    job.save(update_fields=["result_url"])
    return SnapshotPreparation.objects.create(
        snapshot=snapshot, status=status, scan_job=job, source_scan=scan
    )


def test_management_uses_latest_readable_snapshot_and_distinguishes_evidence() -> None:
    owner = create_project(uuid.uuid4(), "项目 Alpha")[0]
    old = make_snapshot(owner, "旧 Python", ("old.py",))
    prepare(old, "ready", declarations=[{"distribution": "django"}])
    latest = make_snapshot(owner, "当前 TSX", ("App.tsx",))
    prepare(
        latest,
        "no_root",
        declarations=[{"distribution": "fastapi"}],
        packages=[
            {
                "name": "django",
                "kind": "third_party",
                "distribution": "django",
                "source_refs": [{}],
            }
        ],
    )
    hidden = make_snapshot(owner, "已隔离")
    hidden.deletion_request_id = uuid.uuid4()
    hidden.save(update_fields=["deletion_request_id"])
    empty = create_project(uuid.uuid4(), "空项目")[0]
    before = (Project.objects.count(), Snapshot.objects.count(), Job.objects.count())
    page = client_with_token().get("/api/v1/projects/management/").json()
    row = next(
        item for item in page["results"] if item["project"]["id"] == str(owner.pk)
    )
    assert row["snapshot_count"] == 2
    assert row["latest_snapshot"]["id"] == str(latest.pk)
    assert row["root_count"] == 0 and row["root_path"] is None
    assert row["last_imported_at"] is not None
    assert row["technologies"] == [
        {"name": "Django", "evidence_kind": "usage"},
        {"name": "FastAPI", "evidence_kind": "declaration"},
        {"name": "TypeScript", "evidence_kind": "language"},
    ]
    assert "React" not in page["technologies"] and "Python" not in page["technologies"]
    empty_row = next(
        item for item in page["results"] if item["project"]["id"] == str(empty.pk)
    )
    assert empty_row["last_imported_at"] is None and empty_row["technologies"] == []
    assert before == (
        Project.objects.count(),
        Snapshot.objects.count(),
        Job.objects.count(),
    )


def test_management_filter_sort_and_facets_apply_before_pagination() -> None:
    owners = [
        create_project(uuid.uuid4(), name)[0] for name in ("Alpha", "Beta", "Empty")
    ]
    first = make_snapshot(owners[0], "python", ("a.py",))
    second = make_snapshot(owners[1], "typescript", ("b.ts",))
    client = client_with_token()
    page = client.get("/api/v1/projects/management/", {"page_size": 1}).json()
    assert page["count"] == 3 and page["results"][0]["latest_snapshot"]["id"] == str(
        second.pk
    )
    assert page["technologies"] == ["Python", "TypeScript"]
    filtered = client.get(
        "/api/v1/projects/management/",
        {"technology": "Python", "ordering": "name", "page_size": "1"},
    ).json()
    assert filtered["count"] == 1 and filtered["results"][0]["latest_snapshot"][
        "id"
    ] == str(first.pk)
    assert filtered["technologies"] == ["Python", "TypeScript"]
    named = client.get(
        "/api/v1/projects/management/", {"q": "alpha", "page_size": "1"}
    ).json()
    assert named["count"] == 1 and named["technologies"] == ["Python"]
    created = client.get("/api/v1/projects/management/", {"ordering": "created"}).json()
    assert created["results"][0]["project"]["id"] == str(owners[2].pk)
    ordered = client.get(
        "/api/v1/projects/management/", {"ordering": "name", "page_size": "1"}
    ).json()
    assert "ordering=name" in ordered["next"]
    assert client.get(ordered["next"]).json()["results"][0]["project"]["name"] == "Beta"


@pytest.mark.parametrize(
    "query",
    [
        "q=a&q=b",
        "technology=Python&technology=TypeScript",
        "ordering=updated",
        "q=" + "a" * 201,
        "q=%00",
        "page=0",
        "unknown=1",
    ],
)
def test_management_rejects_invalid_queries(query: str) -> None:
    assert (
        client_with_token().get("/api/v1/projects/management/?" + query).status_code
        == 400
    )


def test_projection_batches_snapshot_facts_without_per_project_queries() -> None:
    for index in range(8):
        prepare(
            make_snapshot(create_project(uuid.uuid4(), f"项目 {index}")[0], str(index)),
            "no_root",
        )
    with CaptureQueriesContext(connection) as captured:
        response = client_with_token().get("/api/v1/projects/management/?page_size=8")
    assert response.status_code == 200
    assert len(captured) <= 8


def test_activity_keeps_root_selection_separate_from_completed_and_uses_real_events() -> (
    None
):
    owner = create_project(uuid.uuid4(), "活动项目")[0]
    waiting = make_snapshot(owner, "等待根选择")
    preparation = prepare(waiting, "needs_root")
    no_root = make_snapshot(owner, "无根可读")
    prepare(no_root, "no_root")
    failed_import = make_job("import", "failed")
    ImportRequest.objects.create(
        project=owner, job=failed_import, storage_id=uuid.uuid4()
    )
    OperationLog.objects.create(
        project_id=owner.pk,
        operation="source_scan",
        job=preparation.scan_job,
        events=[
            {
                "at": timezone.now().isoformat(),
                "result": "succeeded",
                "stage": "completed",
            },
            {"at": "invalid", "result": "running"},
        ],
    )
    before = (Job.objects.count(), OperationLog.objects.count())
    response = client_with_token().get("/api/v1/projects/activity/")
    assert response.status_code == 200
    data = response.json()
    assert {item["status"] for item in data["active"]} == {"needs_root", "failed"}
    assert [item["status"] for item in data["recent"]] == ["no_root"]
    record = next(item for item in data["active"] if item["status"] == "needs_root")
    assert record["endpoint_count"] is None and record["root_count"] == 1
    assert [stage["kind"] for stage in record["stages"]] == ["import", "source_scan"]
    assert len(record["stages"][1]["events"]) == 1
    assert record["stages"][1]["events"][0]["at"].endswith("Z")
    assert before == (Job.objects.count(), OperationLog.objects.count())


def test_snapshot_search_is_global_paginated_and_excludes_isolated_resources() -> None:
    owners = [create_project(uuid.uuid4(), name)[0] for name in ("甲", "乙", "隔离")]
    for owner in owners:
        make_snapshot(owner, "Release 中文 %")
    owners[2].deletion_request_id = uuid.uuid4()
    owners[2].save(update_fields=["deletion_request_id"])
    client = client_with_token()
    response = client.get("/api/v1/snapshots/", {"q": "release", "page_size": "1"})
    assert response.status_code == 200
    page = response.json()
    assert page["count"] == 2 and "q=release" in page["next"]
    assert (
        page["results"][0]["snapshot"]["project_id"]
        == page["results"][0]["project"]["id"]
    )
    assert client.get(page["next"]).json()["results"][0]["project"]["name"] == "甲"
    assert client.get("/api/v1/snapshots/?q=%25").json()["count"] == 2
    assert client.get("/api/v1/snapshots/?q=missing").json()["count"] == 0
    for query in ("q=a&q=b", "q=%00", "q=" + "a" * 201, "unknown=1"):
        assert client.get("/api/v1/snapshots/?" + query).status_code == 400


@pytest.mark.parametrize("has_execution_log", [True, False])
def test_activity_prefers_original_execution_events_after_replay(
    has_execution_log: bool,
) -> None:
    owner = create_project(uuid.uuid4(), "重放项目")[0]
    preparation = prepare(make_snapshot(owner, "已完成版本"), "no_root")
    original = [
        {
            "at": "2026-10-04T01:00:00Z",
            "result": "running",
            "stage": "source_scanning",
        },
        {
            "at": "2026-10-04T01:01:00Z",
            "result": "succeeded",
            "stage": "completed",
        },
    ]
    replay = [
        {"at": "2026-10-04T02:00:00Z", "result": "replayed"},
        {"at": "2026-10-04T02:00:01Z", "result": "response"},
    ]
    if has_execution_log:
        OperationLog.objects.create(
            project_id=owner.pk,
            operation="source_scan",
            job=preparation.scan_job,
            result="succeeded",
            events=original,
        )
    OperationLog.objects.create(
        project_id=owner.pk,
        operation="source_scan",
        job=preparation.scan_job,
        result="replayed",
        events=replay,
    )
    before = OperationLog.objects.count()
    response = client_with_token().get("/api/v1/projects/activity/")
    assert response.status_code == 200
    observed = response.json()["recent"][0]["stages"][1]["events"]
    expected = original if has_execution_log else replay
    assert observed == [
        {**event, "stage": event.get("stage", ""), "error_code": ""}
        for event in expected
    ]
    assert OperationLog.objects.count() == before


def test_local_or_ambiguous_package_names_are_not_framework_usage() -> None:
    owner = create_project(uuid.uuid4(), "同名模块")[0]
    prepare(
        make_snapshot(owner, "本地模块"),
        "no_root",
        packages=[
            {
                "name": "django",
                "kind": "local",
                "distribution": None,
                "source_refs": [{}],
            },
            {
                "name": "rest_framework",
                "kind": "unknown",
                "distribution": None,
                "source_refs": [{}],
            },
            {
                "name": "flask",
                "kind": "third_party",
                "distribution": "flask",
                "source_refs": [{}],
            },
            {
                "name": "flask",
                "kind": "local",
                "distribution": None,
                "source_refs": [{}],
            },
        ],
    )
    result = client_with_token().get("/api/v1/projects/management/").json()
    assert result["technologies"] == ["Python"]


@pytest.mark.parametrize(
    "status,section", [("needs_root", "active"), ("no_root", "recent")]
)
def test_activity_orders_by_current_task_time_before_limiting(
    status: str, section: str
) -> None:
    owner = create_project(uuid.uuid4(), "重新识别")[0]
    original = prepare(make_snapshot(owner, "最早导入"), status)
    for index in range(6):
        prepare(make_snapshot(owner, f"后续导入 {index}"), status)
    assert original.scan_job_id is not None
    Job.objects.filter(pk=original.scan_job_id).update(
        updated_at=timezone.now() + timedelta(minutes=1)
    )
    result = client_with_token().get("/api/v1/projects/activity/").json()
    assert len(result[section]) == 5
    assert result[section][0]["snapshot"]["id"] == str(original.snapshot_id)
