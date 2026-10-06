import uuid
from pathlib import Path
from typing import Any

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings
from rest_framework.test import APIClient

from apps.jobs.models import Job
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import HOST, ORIGIN, client_with_token
from apps.projects.models import Snapshot, SourceFile
from apps.projects.services import execute_import, source_content
from apps.projects.tests.test_projects import submitted

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def snapshot(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        job = submitted()
        execute_import(str(job.pk))
        published = Job.objects.get(pk=job.pk).snapshot_id
        assert published is not None
        yield Snapshot.objects.get(pk=published)


def test_rename_only_changes_metadata_and_preserves_import_identity(
    snapshot: Snapshot,
) -> None:
    client = client_with_token()
    url = f"/api/v1/snapshots/{snapshot.pk}/"
    schema = contract_schema()
    before = client.get(url).json()
    assert before["name"] == ""
    source = SourceFile.objects.select_related("snapshot").get(snapshot=snapshot)
    content = source_content(source, 1, source.line_count)
    digest = snapshot.manifest_digest
    jobs = Job.objects.count()
    first = client.patch(url, {"name": " 创建任务基线 "}, format="json")
    assert first.status_code == 200
    assert first.json() == {**before, "name": "创建任务基线"}
    assert_response(first, schema, "/api/v1/snapshots/{snapshot_id}/", "patch")
    replay = client.patch(url, {"name": "创建任务基线"}, format="json")
    assert replay.status_code == 200 and replay.json() == first.json()
    assert client.get(url).json() == first.json()
    history = client.get(f"/api/v1/projects/{snapshot.project_id}/snapshots/")
    assert history.json()["results"] == [first.json()]
    snapshot.refresh_from_db()
    assert snapshot.manifest_digest == digest
    assert source_content(source, 1, source.line_count) == content
    assert Job.objects.count() == jobs and Snapshot.objects.count() == 1


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": None},
        {"name": 123},
        {"name": True},
        {"name": ""},
        {"name": " "},
        {"name": "a" * 201},
        {"name": "有效", "summary": {}},
        {"name": "有效", "project_id": str(uuid.uuid4())},
        {"name": "a\x00b"},
        {"name": "a\n"},
        {"name": "a\x85b"},
        [],
    ],
)
def test_invalid_snapshot_name_does_not_change_record(
    snapshot: Snapshot, payload: Any
) -> None:
    response = client_with_token().patch(
        f"/api/v1/snapshots/{snapshot.pk}/", payload, format="json"
    )
    assert response.status_code == 400
    assert_response(response, contract_schema())
    snapshot.refresh_from_db()
    assert snapshot.name == ""


def test_rename_media_type_csrf_origin_and_missing_resource(snapshot: Snapshot) -> None:
    url = f"/api/v1/snapshots/{snapshot.pk}/"
    client = client_with_token()
    assert client.patch(url, {"name": "新名称"}, format="multipart").status_code == 415
    assert client.patch(url, "", content_type="application/json").status_code == 400
    assert (
        client.patch(
            f"/api/v1/snapshots/{uuid.uuid4()}/", {"name": "新名称"}, format="json"
        ).status_code
        == 404
    )
    untrusted = APIClient(enforce_csrf_checks=True)
    csrf_rejected = untrusted.patch(
        url,
        {"name": "新名称"},
        format="json",
        HTTP_HOST=HOST,
        HTTP_ORIGIN=ORIGIN,
    )
    assert csrf_rejected.status_code == 403
    assert csrf_rejected.json()["code"] == "CSRF_REJECTED"
    origin_rejected = untrusted.patch(
        url,
        {"name": "新名称"},
        format="json",
        HTTP_HOST=HOST,
        HTTP_ORIGIN="http://untrusted.invalid",
    )
    assert origin_rejected.status_code == 403
    assert origin_rejected.json()["code"] == "ORIGIN_REJECTED"
    snapshot.refresh_from_db()
    assert snapshot.name == ""


def test_name_migration_backfills_old_snapshot_and_can_reverse(
    snapshot: Snapshot,
) -> None:
    source = SourceFile.objects.select_related("snapshot").get(snapshot=snapshot)
    content = source_content(source, 1, source.line_count)
    identity = (
        snapshot.pk,
        snapshot.project_id,
        snapshot.job_id,
        snapshot.manifest_digest,
    )
    old = [("projects", "0001_initial")]
    current = [("projects", "0002_snapshot_name")]
    executor = MigrationExecutor(connection)
    restore_targets = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate(old)
        historical = executor.loader.project_state(old).apps.get_model(
            "projects", "Snapshot"
        )
        previous = historical.objects.get(pk=snapshot.pk)
        assert not hasattr(previous, "name")
        executor = MigrationExecutor(connection)
        executor.migrate(current)
        renamed = (
            executor.loader.project_state(current)
            .apps.get_model("projects", "Snapshot")
            .objects.get(pk=snapshot.pk)
        )
        assert renamed.name == ""
        assert (
            renamed.pk,
            renamed.project_id,
            renamed.job_id,
            renamed.manifest_digest,
        ) == identity
    finally:
        MigrationExecutor(connection).migrate(restore_targets)
    snapshot.refresh_from_db()
    assert (
        snapshot.name == "" and source_content(source, 1, source.line_count) == content
    )
