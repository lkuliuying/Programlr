import hashlib
import uuid
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.analysis.models import Analysis, SourceScan
from apps.analysis.types import Source
from apps.jobs.models import Job
from apps.jobs.tests.test_jobs import client_with_token
from apps.learning.content import load_cards_only, load_content
from apps.learning.knowledge import preview_cards
from apps.learning.models import Exercise, ExerciseAttempt, KnowledgeCurriculum
from apps.learning.source_scan import scan_knowledge_facts
from apps.learning.tests.history import seed_history
from apps.projects.models import Project, Snapshot, SourceFile

pytestmark = pytest.mark.django_db
TEXT = "import contextlib, unknown_package\ndef selected():\n    with manager():\n        unknown_package.call()\ndef other():\n    yield 1\n"


def job(kind: str) -> Job:
    return Job.objects.create(
        kind=kind,
        scope=uuid.uuid4().hex,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
        status="succeeded",
        expires_at=timezone.now() + timedelta(hours=1),
    )


def fixture() -> tuple[SourceScan, Analysis]:
    load_cards_only()
    project = Project.objects.create(name="知识测试", idempotency_key=uuid.uuid4())
    snapshot = Snapshot.objects.create(
        id=uuid.uuid4(),
        project=project,
        job=job("import"),
        summary={},
        manifest_digest="0" * 64,
    )
    SourceFile.objects.create(
        id=uuid.uuid4(),
        snapshot=snapshot,
        file_path="a.py",
        sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
        size_bytes=len(TEXT.encode()),
        line_count=6,
        line_offsets=[0],
        encoding="utf-8",
    )
    SourceFile.objects.create(
        id=uuid.uuid4(),
        snapshot=snapshot,
        file_path="b.py",
        sha256=hashlib.sha256(b"import unknown_package\n").hexdigest(),
        size_bytes=23,
        line_count=1,
        line_offsets=[0],
        encoding="utf-8",
    )
    knowledge = scan_knowledge_facts(
        str(snapshot.pk),
        [Source("a.py", TEXT), Source("b.py", "import unknown_package\n")],
    )
    scan = SourceScan.objects.create(
        snapshot=snapshot,
        job=job("source_scan"),
        rule_version="source-scan/1.0.0",
        result={"roots": {}, "knowledge": knowledge},
    )
    ref = {
        "snapshot_id": str(snapshot.pk),
        "file_path": "a.py",
        "start_line": 2,
        "end_line": 4,
    }
    endpoint: dict[str, Any] = {
        "method": "GET",
        "path": "/selected/",
        "path_kind": "django_path",
        "action": "selected",
        "view": {"name": "selected", "source_ref": ref},
        "serializer": None,
        "model": None,
        "evidence": [
            {"kind": "source_fact", "rule": "python.method", "source_ref": ref}
        ],
    }
    analysis = Analysis.objects.create(
        snapshot=snapshot,
        job=job("analysis"),
        source_scan=scan,
        root_urlconf="root.py",
        rule_version="python-drf/1.1.0",
        coverage={"limitations": []},
        endpoints=[endpoint],
        diagnostics=[],
    )
    return scan, analysis


def test_snapshot_cards_unknown_facts_scope_and_no_get_writes() -> None:
    scan, analysis = fixture()
    client = client_with_token()
    url = f"/api/v1/snapshots/{scan.snapshot_id}/knowledge-cards/"
    before = (
        SourceScan.objects.count(),
        Job.objects.count(),
        ExerciseAttempt.objects.count(),
    )
    with patch("apps.jobs.services.app.send_task") as queue:
        result = client.get(url)
        assert result.status_code == 200
        values = {item["concept_key"]: item for item in result.json()["results"]}
        assert values["python-context-managers"]["mapped"]
        assert values["python-context-managers"]["card"]["version"] == "1.1.0"
        assert not values["package:unknown_package"]["mapped"]
        assert values["package:unknown_package"]["card"] is None
        selected = client.get(
            url + f"?analysis_id={analysis.pk}&endpoint_index=0"
        ).json()
        assert {item["concept_key"] for item in selected["results"]} == {
            "python-context-managers",
            "package:unknown_package",
        }
        package = next(
            item
            for item in selected["results"]
            if item["concept_key"] == "package:unknown_package"
        )
        assert package["hits"][0]["reason"] == "python.import_use"
        assert package["hits"][0]["source_ref"]["start_line"] == 4
        hits = client.get(
            f"/api/v1/snapshots/{scan.snapshot_id}/knowledge-hits/?concept_key=python-context-managers&page_size=1"
        )
        assert hits.status_code == 200 and hits.json()["count"] == 1
        assert hits.json()["results"][0]["source_ref"]["start_line"] == 3
        queue.assert_not_called()
    assert before == (
        SourceScan.objects.count(),
        Job.objects.count(),
        ExerciseAttempt.objects.count(),
    )


def test_scan_version_filter_cross_snapshot_invalid_queries_and_deleted_resource() -> (
    None
):
    scan, analysis = fixture()
    client = client_with_token()
    url = f"/api/v1/snapshots/{scan.snapshot_id}/knowledge-cards/"
    newer = SourceScan.objects.create(
        snapshot=scan.snapshot,
        job=job("source_scan"),
        rule_version=scan.rule_version,
        result={
            "roots": {},
            "knowledge": scan_knowledge_facts(str(scan.snapshot_id), []),
        },
    )
    assert client.get(url).json()["count"] == 0
    selected = client.get(url + f"?analysis_id={analysis.pk}&endpoint_index=0").json()
    assert selected["scan_id"] == str(scan.pk) and selected["count"] == 2
    for query in (
        "endpoint_index=0",
        "scan_id=bad",
        "scan_id=x&scan_id=y",
        "unknown=1",
        "file_path=missing.py",
        f"analysis_id={analysis.pk}&endpoint_index=0&scan_id={newer.pk}",
    ):
        assert client.get(url + "?" + query).status_code == 400
    scan.snapshot.deletion_request_id = uuid.uuid4()
    scan.snapshot.save(update_fields=["deletion_request_id"])
    assert client.get(url).status_code == 410


def test_decorator_belongs_to_selected_symbol_without_expanding_model_snippets() -> (
    None
):
    scan, analysis = fixture()
    text = "from rest_framework.decorators import api_view\n@api_view(['GET'])\ndef selected():\n    return response\n"
    scan.result["knowledge"] = scan_knowledge_facts(
        str(scan.snapshot_id), [Source("a.py", text)]
    )
    scan.save(update_fields=["result"])
    ref = {
        "snapshot_id": str(scan.snapshot_id),
        "file_path": "a.py",
        "start_line": 3,
        "end_line": 4,
    }
    analysis.endpoints[0]["view"]["source_ref"] = ref
    analysis.endpoints[0]["evidence"][0]["source_ref"] = ref
    analysis.save(update_fields=["endpoints"])
    result = client_with_token().get(
        f"/api/v1/snapshots/{scan.snapshot_id}/knowledge-cards/?analysis_id={analysis.pk}&endpoint_index=0"
    )
    assert result.status_code == 200
    cards = {item["concept_key"]: item for item in result.json()["results"]}
    assert cards["python-decorators"]["hits"][0]["source_ref"]["start_line"] == 2
    assert preview_cards(analysis, [ref], endpoint_index=0) == []
    assert {
        item["slug"]
        for item in preview_cards(analysis, [dict(ref, start_line=2)], endpoint_index=0)
    } == {"python-decorators", "drf-framework", "drf-views"}


def test_cards_only_loader_and_retired_writes_preserve_history() -> None:
    assert load_cards_only() == 29
    assert not Exercise.objects.exists() and not KnowledgeCurriculum.objects.exists()
    assert load_content() == (29, 0)
    seed_history()
    exercise_count, course_count = (
        Exercise.objects.count(),
        KnowledgeCurriculum.objects.count(),
    )
    client = client_with_token()
    for url in ("/api/v1/exercise-attempts/", "/api/v1/attempt-reviews/"):
        result = client.post(
            url, {}, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
        )
        assert result.status_code == 410 and result.json()["code"] == "FEATURE_RETIRED"
    course = KnowledgeCurriculum.objects.get()
    card = course.definition["nodes"][0]
    from apps.learning.models import KnowledgeCard

    record = KnowledgeCard.objects.get(slug=card["slug"], version=card["card_version"])
    response = client.patch(
        f"/api/v1/knowledge-curricula/{course.pk}/progress/{record.pk}/",
        {"completed": True},
        format="json",
    )
    assert response.status_code == 410
    assert client.get(f"/api/v1/knowledge-curricula/{course.pk}/").status_code == 200
    assert (Exercise.objects.count(), KnowledgeCurriculum.objects.count()) == (
        exercise_count,
        course_count,
    )


def test_unknown_multiline_decorator_uses_exact_owner_without_sibling_injection() -> (
    None
):
    scan, analysis = fixture()
    text = (
        "import mysterious as m\n@m.decorate(\n    option=True,\n)\n"
        "def selected():\n    return result\n@m.other\ndef other():\n    return another\n"
    )
    scan.result["knowledge"] = scan_knowledge_facts(
        str(scan.snapshot_id), [Source("a.py", text)]
    )
    scan.save(update_fields=["result"])
    SourceFile.objects.filter(snapshot=scan.snapshot, file_path="a.py").update(
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        size_bytes=len(text.encode()),
        line_count=len(text.splitlines()),
    )
    ref = {
        "snapshot_id": str(scan.snapshot_id),
        "file_path": "a.py",
        "start_line": 5,
        "end_line": 6,
    }
    analysis.endpoints[0]["view"]["source_ref"] = ref
    analysis.endpoints[0]["evidence"][0]["source_ref"] = ref
    analysis.save(update_fields=["endpoints"])
    client = client_with_token()
    filters = {"analysis_id": str(analysis.pk), "endpoint_index": "0"}
    response = client.get(
        f"/api/v1/snapshots/{scan.snapshot_id}/knowledge-cards/", filters
    )
    assert response.status_code == 200
    values = {item["concept_key"]: item for item in response.json()["results"]}
    package = values["package:mysterious"]
    assert package["card"] is None and not package["mapped"]
    assert package["hit_count"] == 1
    assert package["hits"][0]["reason"] == "python.import_use"
    assert package["hits"][0]["source_ref"]["start_line"] == 2
    hits = client.get(
        f"/api/v1/snapshots/{scan.snapshot_id}/knowledge-hits/",
        {**filters, "concept_key": "package:mysterious"},
    )
    assert hits.status_code == 200 and hits.json()["count"] == 1
    assert hits.json()["results"][0]["source_ref"]["start_line"] == 2
    assert preview_cards(analysis, [ref], endpoint_index=0) == []
    assert {
        card["slug"]
        for card in preview_cards(analysis, [dict(ref, start_line=2)], endpoint_index=0)
    } == {"python-decorators"}


@pytest.mark.parametrize("name", ["apps", "requests"])
def test_import_package_identity_survives_filtering_to_only_interface_uses(
    name: str,
) -> None:
    scan, analysis = fixture()
    text = f"from {name}.tasks.services import operation\ndef selected():\n    return operation()\n"
    units = [
        Source("a.py", text),
        Source(f"{name}/tasks/services.py", "def operation():\n    return 1\n"),
        Source(f"{name}/tasks/other.py", "value = 1\n"),
    ]
    for source in units:
        metadata = {
            "sha256": hashlib.sha256(source.content.encode()).hexdigest(),
            "size_bytes": len(source.content.encode()),
            "line_count": len(source.content.splitlines()),
            "line_offsets": [0],
            "encoding": "utf-8",
        }
        SourceFile.objects.update_or_create(
            snapshot=scan.snapshot,
            file_path=source.file_path,
            defaults=metadata,
            create_defaults={"id": uuid.uuid4(), **metadata},
        )
    scan.result["knowledge"] = scan_knowledge_facts(str(scan.snapshot_id), units)
    scan.save(update_fields=["result"])
    assert {
        package["kind"]
        for package in scan.result["knowledge"]["packages"]
        if package["name"] == name
    } == {"local", "third_party" if name == "requests" else "unknown"}
    ref = {
        "snapshot_id": str(scan.snapshot_id),
        "file_path": "a.py",
        "start_line": 2,
        "end_line": 3,
    }
    analysis.endpoints[0]["view"]["source_ref"] = ref
    analysis.endpoints[0]["evidence"][0]["source_ref"] = ref
    analysis.save(update_fields=["endpoints"])
    client = client_with_token()
    url = f"/api/v1/snapshots/{scan.snapshot_id}/knowledge-cards/"
    snapshot_page = client.get(url).json()
    interface_page = client.get(
        url, {"analysis_id": str(analysis.pk), "endpoint_index": "0"}
    ).json()
    file_page = client.get(url, {"file_path": "a.py"}).json()
    assert snapshot_page["count"] == interface_page["count"] == file_page["count"] == 1
    snapshot_package, interface_package, file_package = (
        page["results"][0] for page in (snapshot_page, interface_page, file_page)
    )
    for package in (snapshot_package, interface_package, file_package):
        assert package["concept_key"] == f"package:{name}" and not package["mapped"]
        assert package["package"] == {
            "name": name,
            "kind": "local",
            "distribution": None,
        }
    assert snapshot_package["hit_count"] == file_package["hit_count"] == 2
    assert interface_package["hit_count"] == 1
    assert interface_package["hits"][0]["source_ref"]["start_line"] == 3
    assert preview_cards(analysis, [ref], endpoint_index=0) == []
