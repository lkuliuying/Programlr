from unittest.mock import patch

import pytest
from kombu.exceptions import OperationalError

from apps.jobs.services import execute_check
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token

pytestmark = pytest.mark.django_db


def test_persisted_job_lifecycle_matches_contract() -> None:
    schema = contract_schema()
    client = client_with_token()
    path = "/api/v1/system-checks/"
    key = "ecb391e9-830d-4e9a-b2b6-c823c9465076"
    with patch("apps.jobs.services.app.send_task"):
        submitted = client.post(path, {}, format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert submitted.status_code == 202
    assert_response(submitted, schema, path, "post")
    replay = client.post(path, {}, format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert replay.status_code == 200
    assert_response(replay, schema, path, "post")
    assert replay.json()["id"] == submitted.json()["id"]
    execute_check(submitted.json()["id"])
    detail = client.get(submitted["Location"])
    assert detail.json()["status"] == "succeeded"
    assert_response(detail, schema, "/api/v1/jobs/{job_id}/")
    assert_response(
        client.get(detail.json()["result_url"]),
        schema,
        "/api/v1/system-checks/{check_id}/",
    )
    assert_response(client.get("/api/v1/jobs/"), schema, "/api/v1/jobs/")


def test_publish_failure_and_failed_job_have_different_http_statuses() -> None:
    schema = contract_schema()
    client = client_with_token()
    path = "/api/v1/system-checks/"
    with patch(
        "apps.jobs.services.app.send_task",
        side_effect=OperationalError("test-only-failure"),
    ):
        response = client.post(
            path,
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="96d45a78-051c-4d49-8f66-07d3fcb6c406",
        )
    assert response.status_code == 503
    assert_response(response, schema, path, "post")
    failed = client.get(response["Location"])
    assert failed.status_code == 200
    assert failed.json()["error"]["code"] == "QUEUE_UNAVAILABLE"
    assert_response(failed, schema, "/api/v1/jobs/{job_id}/")
