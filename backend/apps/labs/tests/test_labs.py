import os
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
from apps.jobs.tests.test_recovery import run_process
from apps.labs.api.serializers import LabInputSerializer
from apps.labs.definition import definition
from apps.labs.models import LabRun
from apps.labs.services import execute_run, submit_run
from apps.learning.tests.test_learning import analysis as analysis
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)


def values(analysis: Analysis) -> dict[str, Any]:
    return {
        "snapshot_id": analysis.snapshot_id,
        "analysis_id": analysis.pk,
        "endpoint_index": next(
            i
            for i, value in enumerate(analysis.endpoints)
            if value["method"] == "POST" and value["path"] == "/api/v1/tasks/"
        ),
        "lab_version": "1",
        "predictions": {
            case: {
                "status": 201 if case == "normal" else 400,
                "writes": int(case == "normal"),
            }
            for case in ("normal", "missing", "empty", "whitespace")
        },
    }


def make_run(analysis: Analysis) -> Job:
    data = values(analysis)
    job = create_job(kind="lab")
    LabRun.objects.create(
        job=job,
        analysis=analysis,
        endpoint_index=data["endpoint_index"],
        definition=definition(analysis, data["endpoint_index"]),
        predictions=data["predictions"],
    )
    return job


def test_real_http_observations_cleanup_and_contract(analysis: Analysis) -> None:
    client, schema = client_with_token(), contract_schema()
    body = values(analysis)
    query = f"analysis_id={analysis.pk}&endpoint_index={body['endpoint_index']}"
    for path, template in [
        (f"/api/v1/labs/?{query}", "/api/v1/labs/"),
        (f"/api/v1/labs/request-validation/?{query}", "/api/v1/labs/{lab_id}/"),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert_response(response, schema, template)
    with patch("apps.jobs.services.app.send_task") as send:
        response = client.post(
            "/api/v1/labs/request-validation/runs/",
            body,
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    assert response.status_code == 410 and response.json()["code"] == "FEATURE_RETIRED"
    send.assert_not_called()
    assert not LabRun.objects.exists()
    assert_response(response, schema, "/api/v1/labs/{lab_id}/runs/", "post")
    job = make_run(analysis)
    run = LabRun.objects.get(job=job)
    run.observations = [
        {
            "case_id": case["id"],
            "input": case["input"],
            "request_path": "/internal/legacy/",
            "response": {"status": 201 if case["id"] == "normal" else 400, "body": {}},
            "before_count": 0 if case["id"] == "normal" else 1,
            "after_count": 1,
            "elapsed_ms": 1,
            "observed_at": timezone.now().isoformat(),
        }
        for case in run.definition["cases"]
    ]
    run.cleanup = {
        "status": "completed",
        "observation": {"deleted_count": 1},
        "error_code": None,
    }
    run.save()
    job.status, job.result_url = "succeeded", f"/api/v1/lab-runs/{run.pk}/"
    job.save()
    with patch("apps.labs.adapter.observe") as observe:
        execute_run(str(job.pk))
    observe.assert_not_called()
    for path, template in [
        (job.result_url, "/api/v1/lab-runs/{run_id}/"),
        (f"/api/v1/lab-runs/?{query}", "/api/v1/lab-runs/"),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert_response(response, schema, template)
    run.refresh_from_db()
    assert [
        item["after_count"] - item["before_count"] for item in run.observations
    ] == [1, 0, 0, 0]


def test_concurrent_idempotency_conflict_and_explicit_retry(analysis: Analysis) -> None:
    key, data = uuid.uuid4(), values(analysis)
    before = Job.objects.count()

    def submit(_: int) -> str:
        close_old_connections()
        try:
            with pytest.raises(ApiProblem) as refused:
                submit_run(key, data)
            return refused.value.machine_code
        finally:
            close_old_connections()

    with patch("apps.jobs.services.app.send_task") as send:
        with ThreadPoolExecutor(max_workers=4) as pool:
            assert list(pool.map(submit, range(4))) == ["FEATURE_RETIRED"] * 4
    send.assert_not_called()
    assert Job.objects.count() == before and not LabRun.objects.exists()
    job = make_run(analysis)
    with (
        patch("apps.labs.adapter.observe") as observe,
        patch("apps.labs.adapter.exchange") as exchange,
    ):
        execute_run(str(job.pk))
    observe.assert_not_called()
    exchange.assert_not_called()
    job.refresh_from_db()
    assert job.error is not None and job.error["code"] == "FEATURE_RETIRED"
    with pytest.raises(ApiProblem) as refused:
        submit_retry(job, uuid.uuid4())
    assert refused.value.machine_code == "FEATURE_RETIRED"
    assert not Job.objects.filter(previous_job=job).exists()


def test_partial_response_kept_cleanup_failure_and_late_claim(
    analysis: Analysis,
) -> None:
    job = make_run(analysis)
    run = LabRun.objects.get(job=job)
    run.observations, run.cleanup = (
        [{"historical_partial": True}],
        {"status": "unconfirmed"},
    )
    run.save()
    job.status = "failed"
    job.save()
    with (
        patch("apps.labs.adapter.observe") as observe,
        patch("apps.labs.adapter.exchange") as exchange,
    ):
        execute_run(str(job.pk))
        expired = make_run(analysis)
        Job.objects.filter(pk=expired.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        reconcile_expired()
        execute_run(str(expired.pk))
    observe.assert_not_called()
    exchange.assert_not_called()
    run.refresh_from_db()
    expired.refresh_from_db()
    assert run.observations == [{"historical_partial": True}] and run.cleanup == {
        "status": "unconfirmed"
    }
    assert expired.error is not None and expired.error["code"] == "QUEUE_TIMEOUT"
    assert LabRun.objects.get(job=expired).observations == []


def test_queue_failure_input_and_applicability(analysis: Analysis) -> None:
    data = values(analysis)
    with patch(
        "apps.jobs.services.app.send_task", side_effect=OperationalError
    ) as send:
        for replacement in (
            {},
            {"snapshot_id": uuid.uuid4()},
            {"lab_version": "future"},
            {"endpoint_index": 9999},
        ):
            with pytest.raises(ApiProblem) as refused:
                submit_run(uuid.uuid4(), {**data, **replacement})
            assert refused.value.machine_code == "FEATURE_RETIRED"
    send.assert_not_called()
    assert not LabRun.objects.exists()
    strings = {
        **data,
        "snapshot_id": str(data["snapshot_id"]),
        "analysis_id": str(data["analysis_id"]),
    }
    for predictions in (
        {},
        None,
        {**data["predictions"], "normal": {"status": True, "writes": 1}},
        {**data["predictions"], "extra": {"status": 200, "writes": 0}},
    ):
        assert not LabInputSerializer(
            data={**strings, "predictions": predictions}
        ).is_valid()
    denied = client_with_token().post(
        "/api/v1/labs/request-validation/runs/",
        {**strings, "target_url": "http://invalid"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert denied.status_code == 410 and denied.json()["code"] == "FEATURE_RETIRED"


def test_parallel_runs_and_cleanup_failure_preserve_observations(
    analysis: Analysis,
) -> None:
    jobs = [make_run(analysis), make_run(analysis)]

    def execute(job: Job) -> None:
        close_old_connections()
        try:
            execute_run(str(job.pk))
        finally:
            close_old_connections()

    with (
        patch("apps.labs.adapter.observe") as observe,
        patch("apps.labs.adapter.exchange") as exchange,
    ):
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(execute, jobs))
    observe.assert_not_called()
    exchange.assert_not_called()
    for job in jobs:
        run = LabRun.objects.select_related("job").get(job=job)
        assert run.job.status == "failed" and run.job.error is not None
        assert run.job.error["code"] == "FEATURE_RETIRED"
        assert run.observations == [] and run.cleanup == {}


def test_process_exit_after_real_write_keeps_unknown_observation(
    analysis: Analysis,
) -> None:
    job = make_run(analysis)

    def crash() -> None:
        with patch(
            "apps.labs.adapter.exchange", side_effect=lambda *args: os._exit(23)
        ) as exchange:
            execute_run(str(job.pk))
        exchange.assert_not_called()

    run_process(crash)
    job.refresh_from_db()
    assert job.status == "failed" and job.error is not None
    assert job.error["code"] == "FEATURE_RETIRED"
    run = LabRun.objects.get(job=job)
    assert run.observations == [] and run.cleanup == {}
