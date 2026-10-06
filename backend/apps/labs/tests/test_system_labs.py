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
from apps.jobs.tests.test_jobs import client_with_token, create_job
from apps.labs.models import SystemLabRun
from apps.labs.system_definition import system_definition
from apps.labs.system_services import execute_system_run, submit_system_run
from apps.labs.tests.test_labs import values
from apps.learning.tests.test_learning import analysis as analysis
from common.errors import ApiProblem

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
        for _ in range(2):
            response = client.post(
                f"/api/v1/system-labs/{lab_id}/runs/",
                data,
                format="json",
                HTTP_IDEMPOTENCY_KEY=key,
            )
            assert (
                response.status_code == 410
                and response.json()["code"] == "FEATURE_RETIRED"
            )
            assert_response(
                response, schema, "/api/v1/system-labs/{lab_id}/runs/", "post"
            )
    send.assert_not_called()
    assert not SystemLabRun.objects.exists()
    job = create_job(kind="lab", status="succeeded")
    run = SystemLabRun.objects.create(
        job=job,
        analysis=analysis,
        endpoint_index=data["endpoint_index"],
        lab_id=lab_id,
        definition=system_definition(lab_id, analysis, data["endpoint_index"]),
        predictions=data["predictions"],
        cleanup={"status": "completed", "error_code": None},
    )
    with patch("apps.labs.system_adapter.execute_case") as execute:
        execute_system_run(str(job.pk))
    execute.assert_not_called()
    for url, template in [
        (f"/api/v1/system-lab-runs/{run.pk}/", "/api/v1/system-lab-runs/{run_id}/"),
        (f"/api/v1/system-lab-runs/?{query}", "/api/v1/system-lab-runs/"),
    ]:
        response = client.get(url)
        assert response.status_code == 200
        assert_response(response, schema, template)


def test_unavailable_partial_cleanup_failure_retry_and_expired_claim(
    analysis: Analysis,
) -> None:
    data = body(analysis)
    job = create_job(kind="lab")
    run = SystemLabRun.objects.create(
        job=job,
        analysis=analysis,
        endpoint_index=data["endpoint_index"],
        lab_id="container-network",
        definition=system_definition(
            "container-network", analysis, data["endpoint_index"]
        ),
        predictions=data["predictions"],
        observations=[{"historical_partial": True}],
        cleanup={"status": "unconfirmed"},
    )
    with patch("apps.labs.system_adapter.execute_case") as execute:
        execute_system_run(str(job.pk))
    execute.assert_not_called()
    job.refresh_from_db()
    run.refresh_from_db()
    assert (
        job.status == "failed"
        and job.error is not None
        and job.error["code"] == "FEATURE_RETIRED"
    )
    assert run.observations == [{"historical_partial": True}] and run.cleanup == {
        "status": "unconfirmed"
    }
    with pytest.raises(ApiProblem) as refused:
        submit_retry(job, uuid.uuid4())
    assert refused.value.machine_code == "FEATURE_RETIRED"
    assert not Job.objects.filter(previous_job=job).exists()
    late = create_job(kind="lab", expires_at=timezone.now() - timedelta(seconds=1))
    reconcile_expired()
    with patch("apps.labs.system_adapter.execute_case") as execute:
        execute_system_run(str(late.pk))
    execute.assert_not_called()
    late.refresh_from_db()
    assert (
        late.status == "failed"
        and late.error is not None
        and late.error["code"] == "QUEUE_TIMEOUT"
    )


def test_concurrent_submission_queue_failure_and_strict_inputs(
    analysis: Analysis,
) -> None:
    data, key = body(analysis), uuid.uuid4()
    before = Job.objects.count()

    def submit(_: int) -> str:
        close_old_connections()
        try:
            with pytest.raises(ApiProblem) as refused:
                submit_system_run("subprocess-lifecycle", key, data)
            return refused.value.machine_code
        finally:
            close_old_connections()

    with patch(
        "apps.jobs.services.app.send_task", side_effect=OperationalError
    ) as send:
        with ThreadPoolExecutor(max_workers=4) as pool:
            assert list(pool.map(submit, range(4))) == ["FEATURE_RETIRED"] * 4
    send.assert_not_called()
    assert Job.objects.count() == before and not SystemLabRun.objects.exists()
    client = client_with_token()
    for change in (
        {"command": "arbitrary"},
        {"predictions": {"first": "yes", "second": False}},
        {"endpoint_index": -1},
    ):
        response = client.post(
            "/api/v1/system-labs/subprocess-lifecycle/runs/",
            {**data, **change},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        assert (
            response.status_code == 410 and response.json()["code"] == "FEATURE_RETIRED"
        )
