import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone
from kombu.exceptions import OperationalError

from apps.analysis.models import Analysis
from apps.jobs.models import Job
from apps.jobs.retries import submit_retry
from apps.jobs.services import reconcile_expired
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from apps.labs.models import SystemLabRun
from apps.labs.system_adapter import execute_case
from apps.labs.system_services import execute_system_run, submit_system_run
from apps.labs.tests.test_labs import values
from apps.learning.tests.test_learning import analysis as analysis
from common.errors import Conflict

pytestmark = pytest.mark.django_db(transaction=True)


def body(analysis: Analysis) -> dict[str, Any]:
    return {**values(analysis), "predictions": {"first": True, "second": False}}


@pytest.mark.parametrize("lab_id", ["container-network", "subprocess-lifecycle"])
def test_real_observations_idempotency_and_public_contract(
    analysis: Analysis, lab_id: str
) -> None:
    client, schema = client_with_token(), contract_schema()
    data, key = body(analysis), str(uuid.uuid4())
    query = f"analysis_id={analysis.pk}&endpoint_index={data['endpoint_index']}"
    for url, template in [
        (f"/api/v1/system-labs/?{query}", "/api/v1/system-labs/"),
        (f"/api/v1/system-labs/{lab_id}/?{query}", "/api/v1/system-labs/{lab_id}/"),
    ]:
        response = client.get(url)
        assert response.status_code == 200
        assert_response(response, schema, template)
    with patch("apps.jobs.services.app.send_task") as send:
        response = client.post(
            f"/api/v1/system-labs/{lab_id}/runs/",
            data,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert response.status_code == 202
        assert_response(response, schema, "/api/v1/system-labs/{lab_id}/runs/", "post")
        repeat = client.post(
            f"/api/v1/system-labs/{lab_id}/runs/",
            data,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert (
            repeat.status_code == 200
            and repeat.json()["id"] == response.json()["id"]
            and send.call_count == 1
        )
    execute_system_run(response.json()["id"])
    run = SystemLabRun.objects.select_related("job").get(job_id=response.json()["id"])
    assert run.job.status == "succeeded", run.job.error
    assert run.cleanup["status"] == "completed" and len(run.observations) == 2
    if lab_id == "container-network":
        assert (
            run.observations[0]["hostname"] == "localhost"
            and not run.observations[0]["connected"]
        )
        assert (
            run.observations[1]["hostname"] == "task-board-api"
            and run.observations[1]["connected"]
            and run.observations[1]["addresses"]
        )
    else:
        assert (
            run.observations[0]["return_code"] == 0
            and run.observations[1]["timed_out"]
            and run.observations[1]["reaped"]
        )
    original = run.observations
    execute_system_run(str(run.job_id))
    run.refresh_from_db()
    assert run.observations == original
    for url, template in [
        (f"/api/v1/system-lab-runs/{run.pk}/", "/api/v1/system-lab-runs/{run_id}/"),
        (f"/api/v1/system-lab-runs/?{query}", "/api/v1/system-lab-runs/"),
    ]:
        assert_response(client.get(url), schema, template)


def test_unavailable_partial_cleanup_failure_retry_and_expired_claim(
    analysis: Analysis,
) -> None:
    data = body(analysis)
    with patch("apps.jobs.services.app.send_task"):
        job = submit_system_run("container-network", uuid.uuid4(), data)[0]
    real = execute_case

    def unavailable(lab: str, case: str) -> dict[str, Any]:
        result = real(lab, "first")
        result.update(
            case_id=case,
            hostname="localhost" if case == "first" else "task-board-api",
            connected=False,
            error_code="DNS_FAILED",
            addresses=[],
        )
        return result

    with patch("apps.labs.system_services.execute_case", side_effect=unavailable):
        execute_system_run(str(job.pk))
    job.refresh_from_db()
    run = SystemLabRun.objects.get(job=job)
    assert job.error is not None
    assert (
        job.status == "failed"
        and job.error["code"] == "SYSTEM_LAB_UNAVAILABLE"
        and len(run.observations) == 2
    )
    with patch("apps.jobs.services.app.send_task"):
        retry = submit_retry(job, uuid.uuid4())[0]
    new = SystemLabRun.objects.get(job=retry)
    assert (
        retry.previous_job_id == job.pk
        and new.pk != run.pk
        and new.predictions == run.predictions
    )
    bad = real("subprocess-lifecycle", "first")
    bad.update(
        reaped=False, status="unavailable", error_code="SYSTEM_LAB_CLEANUP_FAILED"
    )
    with patch("apps.labs.system_services.execute_case", return_value=bad):
        execute_system_run(str(retry.pk))
    retry.refresh_from_db()
    new.refresh_from_db()
    assert retry.status == "failed" and new.cleanup["status"] == "unconfirmed"
    with patch("apps.jobs.services.app.send_task"):
        late = submit_system_run("subprocess-lifecycle", uuid.uuid4(), data)[0]

    def expire(lab: str, case: str) -> dict[str, Any]:
        result = real(lab, case)
        Job.objects.filter(pk=late.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        reconcile_expired()
        return result

    with patch("apps.labs.system_services.execute_case", side_effect=expire):
        execute_system_run(str(late.pk))
    late.refresh_from_db()
    assert (
        late.status == "failed" and not SystemLabRun.objects.get(job=late).observations
    )


def test_concurrent_submission_queue_failure_and_strict_inputs(
    analysis: Analysis,
) -> None:
    data, key = body(analysis), uuid.uuid4()

    def submit(_: int) -> str:
        close_old_connections()
        try:
            return str(submit_system_run("subprocess-lifecycle", key, data)[0].pk)
        finally:
            close_old_connections()

    with patch("apps.jobs.services.app.send_task") as send:
        with ThreadPoolExecutor(max_workers=4) as pool:
            identifiers = list(pool.map(submit, range(4)))
    assert len(set(identifiers)) == 1 and send.call_count == 1
    with pytest.raises(Conflict):
        submit_system_run(
            "subprocess-lifecycle",
            key,
            {**data, "predictions": {"first": False, "second": False}},
        )
    with patch("apps.jobs.services.app.send_task", side_effect=OperationalError):
        failed, _, published = submit_system_run(
            "subprocess-lifecycle", uuid.uuid4(), data
        )
    assert (
        not published
        and failed.status == "failed"
        and SystemLabRun.objects.filter(job=failed).exists()
    )
    client = client_with_token()
    for change in (
        {"command": "arbitrary"},
        {"predictions": {"first": "yes", "second": False}},
        {"endpoint_index": -1},
    ):
        assert (
            client.post(
                "/api/v1/system-labs/subprocess-lifecycle/runs/",
                {**data, **change},
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
            ).status_code
            == 400
        )
