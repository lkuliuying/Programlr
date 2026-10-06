import uuid
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.analysis.models import Analysis, AnalysisGraph, SourceScan
from apps.analysis.types import Source
from apps.jobs.models import Job
from apps.jobs.tests.test_jobs import client_with_token
from apps.learning.source_scan import scan_knowledge_facts
from apps.projects.models import Project, Snapshot, SourceFile

pytestmark = pytest.mark.django_db


def record(kind: str) -> Job:
    return Job.objects.create(
        kind=kind,
        scope=uuid.uuid4().hex,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
        status="succeeded",
        expires_at=timezone.now() + timedelta(hours=1),
    )


def example() -> tuple[SourceFile, SourceScan, Analysis]:
    project = Project.objects.create(name="源码依据", idempotency_key=uuid.uuid4())
    snapshot = Snapshot.objects.create(
        id=uuid.uuid4(),
        project=project,
        job=record("import"),
        summary={},
        manifest_digest="0" * 64,
    )
    source = SourceFile.objects.create(
        id=uuid.uuid4(),
        snapshot=snapshot,
        file_path="a.py",
        sha256="0" * 64,
        size_bytes=100,
        line_count=4,
        line_offsets=[0],
    )
    knowledge = scan_knowledge_facts(
        str(snapshot.pk),
        [Source("a.py", "import contextlib\ndef action():\n    return 1\n\n")],
    )
    scan = SourceScan.objects.create(
        snapshot=snapshot,
        job=record("source_scan"),
        rule_version="source-scan/1.0.0",
        result={"knowledge": knowledge},
    )
    ref = {
        "snapshot_id": str(snapshot.pk),
        "file_path": "a.py",
        "start_line": 2,
        "end_line": 3,
    }
    fact = {"kind": "source_fact", "rule": "python.method", "source_ref": ref}
    endpoint: dict[str, Any] = {
        "method": "GET",
        "path": "/items/",
        "view": {"name": "action", "source_ref": ref},
        "serializer": None,
        "model": None,
        "evidence": [fact, fact],
        "frontend_links": [],
    }
    analysis = Analysis.objects.create(
        snapshot=snapshot,
        job=record("analysis"),
        source_scan=scan,
        root_urlconf="a.py",
        rule_version="test/1",
        coverage={},
        endpoints=[endpoint],
        diagnostics=[],
    )
    AnalysisGraph.objects.create(
        analysis=analysis,
        graph_version="test/1",
        nodes=[{"id": str(uuid.uuid4()), "label": "action", "source_ref": ref}],
        edges=[{"evidence": [fact]}],
    )
    return source, scan, analysis


def endpoint(source: SourceFile) -> str:
    return f"/api/v1/snapshots/{source.snapshot_id}/files/{source.pk}/evidence/"


def test_evidence_is_paginated_deduplicated_and_get_does_not_write() -> None:
    source, scan, analysis = example()
    client = client_with_token()
    before = (Job.objects.count(), Analysis.objects.count(), SourceScan.objects.count())
    url = endpoint(source) + f"?analysis_id={analysis.pk}&page_size=2"
    first = client.get(url)
    assert first.status_code == 200
    assert first.json()["scope"] == "persisted_source_evidence"
    assert first.json()["scan_id"] == str(scan.pk)
    results = list(first.json()["results"])
    next_page = first.json()["next"]
    while next_page:
        response = client.get(next_page)
        assert response.status_code == 200
        results.extend(response.json()["results"])
        next_page = response.json()["next"]
    assert len(results) == first.json()["count"]
    assert len({item["id"] for item in results}) == len(results)
    assert {item["kind"] for item in results} >= {"interface", "relation", "knowledge"}
    assert all(item["source_ref"]["file_path"] == "a.py" for item in results)
    assert sum(item["label"] == "GET /items/ · python.method" for item in results) == 1
    assert [item["source_ref"]["start_line"] for item in results] == sorted(
        item["source_ref"]["start_line"] for item in results
    )
    assert (
        Job.objects.count(),
        Analysis.objects.count(),
        SourceScan.objects.count(),
    ) == before
    assert client.get(url).json() == first.json()


def test_no_analysis_can_read_scan_and_no_selection_stays_empty() -> None:
    source, scan, _ = example()
    client = client_with_token()
    empty = client.get(endpoint(source)).json()
    assert (
        empty["count"] == 0
        and empty["analysis_id"] is None
        and empty["scan_id"] is None
    )
    response = client.get(endpoint(source) + f"?scan_id={scan.pk}")
    assert response.status_code == 200
    assert response.json()["count"] > 0
    assert {item["kind"] for item in response.json()["results"]} == {"knowledge"}


def test_evidence_rejects_foreign_and_mismatched_analysis_scan() -> None:
    source, scan, analysis = example()
    other, foreign_scan, foreign_analysis = example()
    client = client_with_token()
    assert (
        client.get(endpoint(source) + f"?analysis_id={foreign_analysis.pk}").status_code
        == 404
    )
    assert (
        client.get(endpoint(source) + f"?scan_id={foreign_scan.pk}").status_code == 404
    )
    assert (
        client.get(
            endpoint(source) + f"?analysis_id={analysis.pk}&scan_id={foreign_scan.pk}"
        ).status_code
        == 400
    )
    analysis.source_scan = None
    analysis.save(update_fields=["source_scan"])
    response = client.get(endpoint(source) + f"?analysis_id={analysis.pk}")
    assert response.status_code == 200 and response.json()["scan_id"] is None
    assert (
        client.get(
            endpoint(source) + f"?analysis_id={analysis.pk}&scan_id={scan.pk}"
        ).status_code
        == 400
    )
    assert (
        client.get(
            f"/api/v1/snapshots/{other.snapshot_id}/files/{source.pk}/evidence/"
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "query",
    [
        "analysis_id=bad",
        "scan_id=",
        "page=0",
        "page_size=101",
        "extra=1",
        "page=1&page=2",
    ],
)
def test_evidence_rejects_invalid_query(query: str) -> None:
    source, _, _ = example()
    assert client_with_token().get(endpoint(source) + "?" + query).status_code == 400


def test_evidence_preserves_deletion_isolation() -> None:
    source, _, _ = example()
    source.snapshot.deletion_request_id = uuid.uuid4()
    source.snapshot.save(update_fields=["deletion_request_id"])
    response = client_with_token().get(endpoint(source))
    assert response.status_code == 410
    assert response.json()["code"] == "RESOURCE_DELETING"
