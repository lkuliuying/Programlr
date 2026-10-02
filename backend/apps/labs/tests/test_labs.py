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
from apps.jobs.tests.test_jobs import client_with_token
from apps.jobs.tests.test_recovery import run_process
from apps.labs import adapter
from apps.labs.api.serializers import LabInputSerializer
from apps.labs.models import LabRun
from apps.labs.services import execute_run, submit_run
from apps.learning.tests.test_learning import analysis as analysis
from common.errors import ApiProblem, Conflict

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
    with patch("apps.jobs.services.app.send_task"):
        return submit_run(uuid.uuid4(), values(analysis))[0]


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
        assert_response(response, schema, template, "get")
    with patch("apps.jobs.services.app.send_task"):
        response = client.post(
            "/api/v1/labs/request-validation/runs/",
            body,
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
    assert response.status_code == 202
    assert_response(response, schema, "/api/v1/labs/{lab_id}/runs/", "post")
    execute_run(response.json()["id"])
    run = LabRun.objects.select_related("job").get(job_id=response.json()["id"])
    assert run.job.status == "succeeded", run.job.error
    assert run.job.snapshot_id is None
    assert [item["response"]["status"] for item in run.observations] == [
        201,
        400,
        400,
        400,
    ]
    assert [
        item["after_count"] - item["before_count"] for item in run.observations
    ] == [1, 0, 0, 0]
    assert (
        run.cleanup["status"] == "completed"
        and run.cleanup["observation"]["deleted_count"] == 1
    )
    execute_run(str(run.job_id))
    assert adapter.observe(run.id, "observe")["record_count"] == 0
    for path, template in [
        (f"/api/v1/lab-runs/{run.id}/", "/api/v1/lab-runs/{run_id}/"),
        (f"/api/v1/lab-runs/?{query}", "/api/v1/lab-runs/"),
    ]:
        response = client.get(path)
        assert_response(response, schema, template, "get")


def test_concurrent_idempotency_conflict_and_explicit_retry(analysis: Analysis) -> None:
    key, data = uuid.uuid4(), values(analysis)

    def submit() -> uuid.UUID:
        close_old_connections()
        try:
            return submit_run(key, data)[0].pk
        finally:
            close_old_connections()

    with patch("apps.jobs.services.app.send_task") as send:
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(lambda _: submit(), range(4)))
        assert len(set(ids)) == 1 and send.call_count == 1
        with pytest.raises(Conflict):
            submit_run(
                key,
                {
                    **data,
                    "predictions": {
                        **data["predictions"],
                        "normal": {"status": 400, "writes": 0},
                    },
                },
            )
    job = Job.objects.get(pk=ids[0])
    with patch(
        "apps.labs.adapter.exchange", side_effect=adapter.LabFailure("LAB_UNAVAILABLE")
    ):
        execute_run(str(job.pk))
    job.refresh_from_db()
    run = LabRun.objects.get(job=job)
    assert (
        job.status == "failed"
        and run.observations == []
        and run.cleanup["status"] == "unconfirmed"
    )
    with patch("apps.jobs.services.app.send_task"):
        retry = submit_retry(job, uuid.uuid4())[0]
    assert retry.previous_job_id == job.pk
    assert LabRun.objects.get(job=retry).id != run.id


def test_partial_response_kept_cleanup_failure_and_late_claim(
    analysis: Analysis,
) -> None:
    job = make_run(analysis)
    original = adapter.exchange

    def broken(run_id: uuid.UUID, action: str) -> dict[str, Any]:
        if action == "missing":
            return {"status": 200, "body": {"incomplete": True}}
        return original(run_id, action)

    with patch("apps.labs.adapter.exchange", side_effect=broken):
        execute_run(str(job.pk))
    job.refresh_from_db()
    run = LabRun.objects.get(job=job)
    assert job.error is not None
    assert job.error["code"] == "LAB_INVALID_RESPONSE" and len(run.observations) == 2
    assert (
        run.observations[-1]["after_count"] is None
        and run.cleanup["status"] == "completed"
    )
    expired = make_run(analysis)

    def terminate(run_id: uuid.UUID, action: str) -> dict[str, Any]:
        result = original(run_id, action)
        if action == "normal":
            Job.objects.filter(pk=expired.pk).update(
                expires_at=timezone.now() - timedelta(seconds=1)
            )
            reconcile_expired()
        return result

    with patch("apps.labs.adapter.exchange", side_effect=terminate):
        execute_run(str(expired.pk))
    expired.refresh_from_db()
    assert expired.error is not None
    assert expired.status == "failed" and expired.error["code"] == "EXECUTION_TIMEOUT"
    assert LabRun.objects.get(job=expired).observations == []


def test_queue_failure_input_and_applicability(analysis: Analysis) -> None:
    data = values(analysis)
    with patch("apps.jobs.services.app.send_task", side_effect=OperationalError):
        job, created, published = submit_run(uuid.uuid4(), data)
    assert created and not published and job.status == "failed"
    assert LabRun.objects.filter(job=job).exists()
    for replacement in (
        {"snapshot_id": uuid.uuid4()},
        {"lab_version": "future"},
        {"endpoint_index": 9999},
    ):
        with pytest.raises(ApiProblem):
            submit_run(uuid.uuid4(), {**data, **replacement})
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
    client = client_with_token()
    denied = client.post(
        "/api/v1/labs/request-validation/runs/",
        {**strings, "target_url": "http://invalid"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert denied.status_code == 400


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

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(execute, jobs))
    for job in jobs:
        run = LabRun.objects.select_related("job").get(job=job)
        assert run.job.status == "succeeded"
        assert [
            item["after_count"] - item["before_count"] for item in run.observations
        ] == [1, 0, 0, 0]
        assert run.cleanup["observation"]["deleted_count"] == 1

    failed = make_run(analysis)
    original = adapter.observe

    def unavailable_cleanup(run_id: uuid.UUID, action: str) -> dict[str, Any]:
        if action == "close":
            raise adapter.LabFailure("LAB_UNAVAILABLE")
        return original(run_id, action)

    try:
        with patch("apps.labs.adapter.observe", side_effect=unavailable_cleanup):
            execute_run(str(failed.pk))
        run = LabRun.objects.select_related("job").get(job=failed)
        assert (
            run.job.error is not None and run.job.error["code"] == "LAB_CLEANUP_FAILED"
        )
        assert run.job.status == "failed" and len(run.observations) == 4
        assert run.cleanup["status"] == "unconfirmed"
        assert original(run.id, "observe")["record_count"] == 1
    finally:
        original(LabRun.objects.get(job=failed).id, "close")


def test_process_exit_after_real_write_keeps_unknown_observation(
    analysis: Analysis,
) -> None:
    job = make_run(analysis)

    def crash() -> None:
        original = adapter.exchange

        def interrupted(run_id: uuid.UUID, action: str) -> dict[str, Any]:
            result = original(run_id, action)
            if action == "normal":
                os._exit(23)
            return result

        with patch("apps.labs.adapter.exchange", side_effect=interrupted):
            execute_run(str(job.pk))

    run = LabRun.objects.get(job=job)
    try:
        run_process(crash, expected=23)
        assert adapter.observe(run.id, "observe")["record_count"] == 1
        Job.objects.filter(pk=job.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        reconcile_expired()
        execute_run(str(job.pk))
        run.refresh_from_db()
        job.refresh_from_db()
        assert job.status == "failed" and job.error is not None
        assert job.error["code"] == "EXECUTION_TIMEOUT" and run.observations == []
        assert run.cleanup == {}
    finally:
        adapter.observe(run.id, "close")
