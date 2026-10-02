import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any

import pytest
from django.db import close_old_connections
from django.utils import timezone

from apps.labs.models import LabSession
from apps.labs.services import CASES, close_run, open_run, reconcile_runs
from apps.tasks.models import Task
from apps.tasks.tests.test_tasks import client_with_token

pytestmark = pytest.mark.django_db(transaction=True)


def test_four_inputs_isolation_replay_and_close() -> None:
    client = client_with_token()
    one, two = uuid.uuid4(), uuid.uuid4()
    for run in (one, two):
        path = f"/internal/labs/runs/{run}/"
        assert client.post(path, {}, format="json").status_code == 200
        for case, payload in CASES.items():
            response = client.post(path + f"cases/{case}/", payload, format="json")
            assert response.status_code == (201 if case == "normal" else 400)
        assert (
            client.post(
                path + "cases/normal/", CASES["normal"], format="json"
            ).status_code
            == 200
        )
        assert client.get(path).json()["record_count"] == 1
    unrelated = Task.objects.create(title="保留", idempotency_key=uuid.uuid4())
    assert close_run(one)["deleted_count"] == 1
    assert close_run(one)["deleted_count"] == 1
    assert Task.objects.count() == 2 and Task.objects.filter(pk=unrelated.pk).exists()
    assert (
        client.post(
            f"/internal/labs/runs/{one}/cases/normal/", CASES["normal"], format="json"
        ).status_code
        == 409
    )
    assert open_run(one).closed
    close_run(two)
    assert Task.objects.count() == 1


def test_concurrent_same_case_and_cleanup_fence() -> None:
    run = uuid.uuid4()
    open_run(run)

    def submit(_: int) -> int:
        close_old_connections()
        try:
            return (
                client_with_token()
                .post(
                    f"/internal/labs/runs/{run}/cases/normal/",
                    CASES["normal"],
                    format="json",
                )
                .status_code
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(submit, range(4)))
    assert statuses.count(201) == 1 and statuses.count(200) == 3
    LabSession.objects.filter(pk=run).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert submit(0) == 409
    assert reconcile_runs() == 1 and Task.objects.count() == 0


def test_boundaries_and_no_side_effect_on_bad_input() -> None:
    client = client_with_token()
    run = open_run(uuid.uuid4())
    path = f"/internal/labs/runs/{run.id}/cases/normal/"
    invalid_bodies: tuple[Any, ...] = (
        {"title": "其他"},
        {"title": "实验任务", "command": "ignored"},
        [],
    )
    for body in invalid_bodies:
        assert client.post(path, body, format="json").status_code == 400
    assert client.post(path, "null", content_type="application/json").status_code == 400
    assert client.post(path).status_code == 415
    assert Task.objects.count() == 0
    client.credentials(HTTP_HOST="127.0.0.1:5174", HTTP_ORIGIN="http://invalid")
    assert client.post(path, CASES["normal"], format="json").status_code == 403
