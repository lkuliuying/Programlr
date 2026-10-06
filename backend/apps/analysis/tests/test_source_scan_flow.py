import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.test import override_settings
from django.utils import timezone

from apps.analysis.models import (
    Analysis,
    AnalysisRequest,
    SnapshotPreparation,
    SourceScan,
    SourceScanRequest,
)
from apps.analysis.root_discovery import discover_roots
from apps.analysis.scan_runner import run_source_scan
from apps.analysis.scans import execute_source_scan, submit_source_scan
from apps.analysis.services import execute_analysis
from apps.analysis.tests.test_parser import fixture_sources
from apps.analysis.types import AnalysisFailed, Source
from apps.jobs.models import Job
from apps.jobs.services import reconcile_expired
from apps.jobs.tests.test_jobs import client_with_token
from apps.learning.source_scan import scan_knowledge_facts
from apps.projects.models import Snapshot
from apps.projects.services import create_project, execute_import, submit_import
from apps.projects.tests.test_archive import zip_bytes
from apps.projects.tests.test_projects import upload

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def imported_sources(contents: dict[str, bytes] | None = None) -> tuple[Snapshot, Job]:
    owner = create_project(uuid.uuid4(), "源码扫描合成项目")[0]
    contents = (
        contents
        if contents is not None
        else {source.file_path: source.content.encode() for source in fixture_sources()}
    )
    with patch("apps.jobs.services.app.send_task"):
        parent = submit_import(owner, uuid.uuid4(), upload(zip_bytes(contents)))[0]
        execute_import(str(parent.pk))
    parent.refresh_from_db()
    assert parent.status == Job.Status.SUCCEEDED
    snapshot = Snapshot.objects.get(job=parent)
    scan_job = SourceScanRequest.objects.get(snapshot=snapshot).job
    assert scan_job.parent_job_id == parent.pk and scan_job.kind == "source_scan"
    return snapshot, scan_job


def test_real_scan_subprocess_accepts_manifest_declarations_and_exact_protocol() -> (
    None
):
    snapshot, _ = imported_sources(
        {
            "urls.py": b"urlpatterns = []\n",
            "facts.py": b"from pathlib import Path\nitems = [x for x in range(3)]\n",
            "requirements.txt": b"Django==5.2\n",
        }
    )
    result = run_source_scan(
        str(snapshot.pk),
        [
            Source("urls.py", "urlpatterns = []\n"),
            Source(
                "facts.py", "from pathlib import Path\nitems = [x for x in range(3)]\n"
            ),
            Source("requirements.txt", "Django==5.2\n"),
        ],
    )
    assert result["roots"]["selected_root"] == "urls.py"
    assert result["knowledge"]["declarations"] and result["knowledge"]["hits"]
    assert result["knowledge"]["rule_version"] == "source-knowledge/1.0.0"


def test_import_scan_auto_analysis_and_reload_links_are_persistent() -> None:
    snapshot, scan_job = imported_sources()
    with patch("apps.jobs.services.app.send_task") as send:
        execute_source_scan(str(scan_job.pk))
        execute_source_scan(str(scan_job.pk))
    scan_job.refresh_from_db()
    scan = SourceScan.objects.get(job=scan_job)
    preparation = SnapshotPreparation.objects.get(snapshot=snapshot)
    assert (
        scan_job.status == Job.Status.SUCCEEDED
        and scan_job.result_url == f"/api/v1/source-scans/{scan.pk}/"
    )
    assert scan.result["roots"]["selected_root"] == "root_urls.py"
    assert scan.result["knowledge"]["coverage"]["parsed_files"] > 0
    assert preparation.status == "analyzing" and preparation.source_scan_id == scan.pk
    assert preparation.analysis_job is not None
    assert preparation.analysis_job.parent_job_id == scan_job.pk
    assert (
        AnalysisRequest.objects.get(job=preparation.analysis_job).source_scan_id
        == scan.pk
    )
    assert send.call_count == 1
    execute_analysis(str(preparation.analysis_job_id))
    preparation.refresh_from_db()
    assert preparation.status == "ready" and preparation.analysis_id is not None
    client = client_with_token()
    refreshed = client.get(f"/api/v1/snapshots/{snapshot.pk}/").json()
    assert refreshed["source_scan_id"] == str(scan.pk)
    assert refreshed["analysis_id"] == str(preparation.analysis_id)
    assert refreshed["preparation_status"] == "ready"
    shared = client.get(
        f"/api/v1/analyses/{preparation.analysis_id}/endpoint-relations/",
        {"endpoint_index": 0},
    )
    assert shared.status_code == 200 and shared.json()["direction"] == "undirected"
    assert shared.json()["graph_version"] == "shared-interface/1.0.0"
    assert (
        len([node for node in shared.json()["nodes"] if node["kind"] == "endpoint"]) > 1
    )


@pytest.mark.parametrize(
    "roots,status",
    [
        ({}, "no_root"),
        ({"a.py": b"urlpatterns = []\n", "b.py": b"urlpatterns = []\n"}, "needs_root"),
    ],
)
def test_knowledge_survives_missing_or_multiple_roots(
    roots: dict[str, bytes], status: str
) -> None:
    snapshot, scan_job = imported_sources(
        {"facts.py": b"items = [x for x in range(3)]\n", **roots}
    )
    with patch("apps.jobs.services.app.send_task") as send:
        execute_source_scan(str(scan_job.pk))
    scan_job.refresh_from_db()
    scan = SourceScan.objects.get(job=scan_job)
    assert scan_job.status == Job.Status.SUCCEEDED and scan.result["knowledge"]["hits"]
    assert scan.result["roots"]["status"] == status and send.call_count == 0
    assert SnapshotPreparation.objects.get(snapshot=snapshot).status == status
    client = client_with_token()
    path = f"/api/v1/snapshots/{snapshot.pk}/analyses/"
    rejected = client.post(
        path,
        {"root_urlconf": "facts.py"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert (
        rejected.status_code == 400 and rejected.json()["code"] == "ROOT_NOT_AVAILABLE"
    )
    if status == "needs_root":
        with patch("apps.jobs.services.app.send_task"):
            selected = client.post(
                path,
                {"root_urlconf": "b.py"},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            )
        assert selected.status_code == 202
        assert (
            AnalysisRequest.objects.get(job_id=selected.json()["id"]).source_scan_id
            == scan.pk
        )


def test_scan_child_creation_failure_rolls_back_both_results() -> None:
    snapshot, scan_job = imported_sources()
    with patch(
        "apps.analysis.scans.SourceScan.objects.create",
        side_effect=DatabaseError("synthetic-private-marker"),
    ):
        execute_source_scan(str(scan_job.pk))
    scan_job.refresh_from_db()
    assert scan_job.status == Job.Status.FAILED
    assert not SourceScan.objects.exists() and not AnalysisRequest.objects.exists()
    assert SnapshotPreparation.objects.get(snapshot=snapshot).status == "failed"
    assert "synthetic-private-marker" not in str(scan_job.error)
    client = client_with_token()
    key = str(uuid.uuid4())
    with patch("apps.jobs.services.app.send_task") as send:
        retried = client.post(
            f"/api/v1/jobs/{scan_job.pk}/retries/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        replay = client.post(
            f"/api/v1/jobs/{scan_job.pk}/retries/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
    assert retried.status_code == 202 and replay.status_code == 200
    assert retried.json()["id"] == replay.json()["id"] and send.call_count == 1
    new_job = Job.objects.get(pk=retried.json()["id"])
    assert new_job.previous_job_id == scan_job.pk
    with patch("apps.jobs.services.app.send_task"):
        execute_source_scan(str(new_job.pk))
    assert SourceScan.objects.count() == AnalysisRequest.objects.count() == 1


def test_child_job_failure_rolls_back_scan_before_dispatch() -> None:
    snapshot, scan_job = imported_sources()
    with (
        patch(
            "apps.analysis.services.AnalysisRequest.objects.create",
            side_effect=DatabaseError("synthetic-create-failure"),
        ),
        patch("apps.jobs.services.app.send_task") as send,
    ):
        execute_source_scan(str(scan_job.pk))
    scan_job.refresh_from_db()
    assert scan_job.status == Job.Status.FAILED and send.call_count == 0
    assert (
        not SourceScan.objects.exists()
        and not Job.objects.filter(kind="analysis").exists()
    )
    assert SnapshotPreparation.objects.get(snapshot=snapshot).status == "failed"


def test_expired_scan_never_publishes_or_creates_analysis() -> None:
    snapshot, scan_job = imported_sources({"urls.py": b"urlpatterns = []\n"})

    def expired(snapshot_id: str, sources: list[Source]) -> dict[str, Any]:
        Job.objects.filter(pk=scan_job.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        return {
            "roots": discover_roots(snapshot_id, sources),
            "knowledge": scan_knowledge_facts(snapshot_id, sources),
        }

    with (
        patch("apps.analysis.scans.run_source_scan", side_effect=expired),
        patch("apps.jobs.services.app.send_task") as send,
    ):
        execute_source_scan(str(scan_job.pk))
    assert (
        not SourceScan.objects.exists()
        and not AnalysisRequest.objects.exists()
        and send.call_count == 0
    )
    reconcile_expired()
    scan_job.refresh_from_db()
    assert scan_job.status == Job.Status.FAILED
    assert (
        client_with_token()
        .get(f"/api/v1/snapshots/{snapshot.pk}/")
        .json()["preparation_status"]
        == "failed"
    )


def test_new_scan_clears_current_links_and_preserves_previous_results() -> None:
    snapshot, original = imported_sources()
    with patch("apps.jobs.services.app.send_task"):
        execute_source_scan(str(original.pk))
        preparation = SnapshotPreparation.objects.get(snapshot=snapshot)
        execute_analysis(str(preparation.analysis_job_id))
        next_job, created, _ = submit_source_scan(snapshot, uuid.uuid4())
    old_scan, old_analysis = (
        SourceScan.objects.get(job=original),
        Analysis.objects.get(snapshot=snapshot),
    )
    preparation.refresh_from_db()
    assert (
        created
        and preparation.status == "pending"
        and preparation.scan_job_id == next_job.pk
    )
    assert (
        preparation.source_scan_id
        is preparation.analysis_job_id
        is preparation.analysis_id
        is None
    )
    client = client_with_token()
    assert client.get(f"/api/v1/source-scans/{old_scan.pk}/").status_code == 200
    assert client.get(f"/api/v1/analyses/{old_analysis.pk}/").status_code == 200
    with patch(
        "apps.analysis.scans.run_source_scan",
        side_effect=AnalysisFailed("scan_timeout"),
    ):
        execute_source_scan(str(next_job.pk))
    assert (
        SourceScan.objects.filter(pk=old_scan.pk).exists()
        and Analysis.objects.filter(pk=old_analysis.pk).exists()
    )


def test_deleting_resources_refuse_scan_and_source_reads() -> None:
    snapshot, scan_job = imported_sources()
    snapshot.deletion_request_id = uuid.uuid4()
    snapshot.save(update_fields=["deletion_request_id"])
    client = client_with_token()
    response = client.post(
        f"/api/v1/snapshots/{snapshot.pk}/source-scans/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 410
    assert client.get(f"/api/v1/snapshots/{snapshot.pk}/files/").status_code == 410
    execute_source_scan(str(scan_job.pk))
    scan_job.refresh_from_db()
    assert scan_job.status == Job.Status.FAILED and not SourceScan.objects.exists()
