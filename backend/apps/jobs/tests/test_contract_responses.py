import uuid
from unittest.mock import patch

import pytest
from kombu.exceptions import OperationalError

from apps.jobs.models import SystemCheck
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token, create_job
from apps.projects.models import Project

pytestmark = pytest.mark.django_db


def test_persisted_job_lifecycle_matches_contract() -> None:
    schema, client = contract_schema(), client_with_token()
    path, key = "/api/v1/system-checks/", str(uuid.uuid4())
    with patch("apps.jobs.services.app.send_task") as dispatch:
        submitted = client.post(path, {}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        replay = client.post(path, {}, format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert submitted.status_code == replay.status_code == 410
    dispatch.assert_not_called()
    assert_response(submitted, schema, path, "post")
    job = create_job(status="succeeded")
    SystemCheck.objects.create(job=job)
    detail = client.get(f"/api/v1/jobs/{job.pk}/")
    assert detail.json()["status"] == "succeeded"
    assert_response(detail, schema, "/api/v1/jobs/{job_id}/")
    assert_response(
        client.get(detail.json()["result_url"]),
        schema,
        "/api/v1/system-checks/{check_id}/",
    )
    assert_response(client.get("/api/v1/jobs/"), schema, "/api/v1/jobs/")


def test_publish_failure_and_failed_job_have_different_http_statuses() -> None:
    schema, client = contract_schema(), client_with_token()
    project = Project.objects.create(name="清理契约", idempotency_key=uuid.uuid4())
    preview = client.get(f"/api/v1/projects/{project.pk}/deletion-preview/")
    path = f"/api/v1/projects/{project.pk}/"
    with patch(
        "apps.jobs.services.app.send_task",
        side_effect=OperationalError("test-only-failure"),
    ):
        response = client.delete(
            path,
            {"confirmation_digest": preview.json()["confirmation_digest"]},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    assert response.status_code == 503
    assert_response(response, schema, "/api/v1/projects/{project_id}/", "delete")
    failed = client.get(response["Location"])
    assert (
        failed.status_code == 200
        and failed.json()["error"]["code"] == "QUEUE_UNAVAILABLE"
    )
    assert_response(failed, schema, "/api/v1/jobs/{job_id}/")
