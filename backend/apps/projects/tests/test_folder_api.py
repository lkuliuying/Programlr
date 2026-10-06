import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.analysis.models import SourceScanRequest
from apps.jobs.models import Job
from apps.jobs.tests.test_jobs import client_with_token
from apps.projects.folder import CODEC_VERSION, folder_limits
from apps.projects.models import ImportRequest, Snapshot, SourceFile
from apps.projects.services import create_project, execute_import

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path) -> Any:
    with override_settings(IMPORT_STORAGE_ROOT=str(tmp_path / "storage")):
        yield


def body(entries: list[tuple[str, bytes]] | None = None) -> dict[str, Any]:
    entries = (
        entries
        if entries is not None
        else [
            ("urls.py", b"urlpatterns = []\n"),
            ("requirements.txt", b"Django==5.2\n"),
        ]
    )
    return {
        "manifest": SimpleUploadedFile(
            "manifest.json",
            json.dumps(
                {
                    "files": [
                        {"path": path, "index": index}
                        for index, (path, _) in enumerate(entries)
                    ]
                }
            ).encode(),
            content_type="application/json",
        ),
        "files": [SimpleUploadedFile("selected.txt", data) for _, data in entries],
    }


def test_folder_api_canonical_idempotency_limits_and_auto_scan() -> None:
    owner = create_project(uuid.uuid4(), "目录导入样例")[0]
    client, key = client_with_token(), str(uuid.uuid4())
    path = f"/api/v1/projects/{owner.pk}/folder-imports/"
    entries = [("b.py", b"b=2\n"), ("urls.py", b"urlpatterns = []\n")]
    with patch("apps.jobs.services.app.send_task") as send:
        first = client.post(
            path, body(entries), format="multipart", HTTP_IDEMPOTENCY_KEY=key
        )
        replay = client.post(
            path,
            body(list(reversed(entries))),
            format="multipart",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        conflict = client.post(
            path,
            body([("urls.py", b"urlpatterns = [1]\n")]),
            format="multipart",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert (
            first.status_code == 202
            and replay.status_code == 200
            and conflict.status_code == 409
        )
        assert first.json()["id"] == replay.json()["id"] and send.call_count == 1
        record = ImportRequest.objects.get(job_id=first.json()["id"])
        assert record.source_kind == record.job.source_kind == "folder"
        assert (
            record.effective_limits == asdict(folder_limits())
            and record.codec_version == CODEC_VERSION
        )
        execute_import(str(record.job_id))
    record.job.refresh_from_db()
    assert record.job.status == Job.Status.SUCCEEDED
    snapshot = Snapshot.objects.get(job=record.job)
    assert SourceFile.objects.filter(snapshot=snapshot).count() == 2
    scan = SourceScanRequest.objects.get(snapshot=snapshot)
    assert scan.job.parent_job_id == record.job_id and scan.job.source_kind == "folder"


def test_folder_retry_uses_same_canonical_content_and_original_limits() -> None:
    owner = create_project(uuid.uuid4(), "目录重试样例")[0]
    client = client_with_token()
    with patch("apps.jobs.services.app.send_task"):
        initial = client.post(
            f"/api/v1/projects/{owner.pk}/folder-imports/",
            body(),
            format="multipart",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    record = ImportRequest.objects.get(job_id=initial.json()["id"])
    Job.objects.filter(pk=record.job_id).update(
        status=Job.Status.FAILED, stage="failed"
    )
    key = str(uuid.uuid4())
    retry_path = f"/api/v1/jobs/{record.job_id}/folder-retries/"
    with patch("apps.jobs.services.app.send_task") as send:
        changed = client.post(
            retry_path,
            body([("urls.py", b"urlpatterns = [1]\n")]),
            format="multipart",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        retried = client.post(
            retry_path, body(), format="multipart", HTTP_IDEMPOTENCY_KEY=key
        )
        replay = client.post(
            retry_path, body(), format="multipart", HTTP_IDEMPOTENCY_KEY=key
        )
    assert (
        changed.status_code == 409
        and retried.status_code == 202
        and replay.status_code == 200
    )
    assert send.call_count == 1
    next_record = ImportRequest.objects.get(job_id=retried.json()["id"])
    assert (
        next_record.source_kind == "folder"
        and next_record.effective_limits == record.effective_limits
    )
    assert next_record.job.previous_job_id == record.job_id
    assert next_record.job.request_digest == record.job.request_digest


@pytest.mark.parametrize(
    "entries",
    [
        [("../unsafe.py", b"x")],
        [(".env/unsafe.py", b"x")],
        [("secrets.env", b"x")],
        [("A.py", b"a"), ("a.py", b"b")],
        [("large.py", b"x" * (1024 * 1024 + 1))],
    ],
)
def test_folder_rejection_does_not_create_jobs(
    entries: list[tuple[str, bytes]],
) -> None:
    owner = create_project(uuid.uuid4(), "目录拒绝样例")[0]
    response = client_with_token().post(
        f"/api/v1/projects/{owner.pk}/folder-imports/",
        body(entries),
        format="multipart",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert (
        response.status_code in {400, 413}
        and not ImportRequest.objects.exists()
        and not Job.objects.exists()
    )


def test_folder_manifest_is_bounded_file_and_input_fields_are_exact() -> None:
    owner = create_project(uuid.uuid4(), "清单拒绝样例")[0]
    client = client_with_token()
    path = f"/api/v1/projects/{owner.pk}/folder-imports/"
    invalid = body()
    invalid["manifest"] = '{"files":[]}'
    assert (
        client.post(
            path, invalid, format="multipart", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
        ).status_code
        == 400
    )
    invalid = body()
    invalid["extra"] = "ignored"
    assert (
        client.post(
            path, invalid, format="multipart", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())
        ).status_code
        == 400
    )
    assert not ImportRequest.objects.exists()


def test_worker_rejects_unknown_or_unbounded_persisted_policy() -> None:
    owner = create_project(uuid.uuid4(), "策略拒绝样例")[0]
    client = client_with_token()
    for field, value in [
        ("source_kind", "untrusted"),
        (
            "effective_limits",
            {**asdict(folder_limits()), "archive_bytes": 1024 * 1024 * 1024},
        ),
        ("codec_version", "future-format"),
    ]:
        with patch("apps.jobs.services.app.send_task"):
            response = client.post(
                f"/api/v1/projects/{owner.pk}/folder-imports/",
                body(),
                format="multipart",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            )
        record = ImportRequest.objects.get(job_id=response.json()["id"])
        setattr(record, field, value)
        record.save(update_fields=[field])
        execute_import(str(record.job_id))
        record.job.refresh_from_db()
        assert record.job.status == Job.Status.FAILED and record.job.error is not None
        assert record.job.error["details"]["reason"] == "import_policy_invalid"
    assert not Snapshot.objects.exists()
