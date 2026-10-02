import json
import os
import subprocess
import time
import uuid
from typing import Any
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.explanations.configuration import encode
from apps.explanations.models import ContextPreview, Explanation
from apps.explanations.services import create_consent, submit_explanation
from apps.explanations.tests.test_adapter import completion, valid_content
from apps.explanations.tests.test_explanations import preview as preview  # noqa: F401
from apps.jobs import services as jobs
from apps.jobs.retries import submit_retry
from apps.jobs.tests.test_jobs import client_with_token
from apps.jobs.tests.test_recovery import reconcile_in_process, run_process

pytestmark = pytest.mark.django_db(transaction=True)


def crashing_worker(queue: str) -> None:
    from celery.contrib.testing.worker import start_worker

    import apps.explanations.tasks  # noqa: F401
    from config.celery import app

    with (
        override_settings(JOB_EXECUTION_TIMEOUT_SECONDS=1),
        patch(
            "apps.explanations.services.complete",
            side_effect=lambda *args, **kwargs: os._exit(23),
        ),
    ):
        with start_worker(
            app,
            pool="solo",
            queues=[queue],
            perform_ping_check=False,
            shutdown_timeout=5,
        ):
            time.sleep(12)


def read_history(explanation_id: str) -> None:
    response = client_with_token().get(f"/api/v1/explanations/{explanation_id}/")
    assert response.status_code == 200 and response.json()["model"] == "test-model"


def test_real_worker_crash_reconcile_retry_and_new_reader(
    preview: ContextPreview,
) -> None:
    from celery.contrib.testing.worker import start_worker

    import apps.explanations.tasks  # noqa: F401
    from config.celery import app

    queue, original_send = "m4-" + uuid.uuid4().hex, app.send_task

    def send(*args: Any, **kwargs: Any) -> Any:
        return original_send(*args, **kwargs, queue=queue)

    def respond(
        config: Any, messages: list[dict[str, str]], **kwargs: Any
    ) -> tuple[str, str, None]:
        ref = json.loads(messages[1]["content"])["snippets"][0]["source_ref"]
        return valid_content(ref), "test-model", None

    try:
        with patch("apps.jobs.services.app.send_task", side_effect=send):
            job = submit_explanation(
                uuid.uuid4(), create_consent(preview, uuid.uuid4())[0].pk
            )[0]
        run_process(crashing_worker, queue, expected=23)
        job.refresh_from_db()
        assert job.status == "running" and job.claim_id is not None
        time.sleep(max(0, (job.expires_at.timestamp() - time.time())) + 0.05)
        run_process(reconcile_in_process)
        job.refresh_from_db()
        assert job.status == "failed"
        assert not jobs.complete_explanation(str(job.pk), job.claim_id, lambda: "late")
        consent = create_consent(preview, uuid.uuid4())[0]
        with (
            patch("apps.explanations.services.complete", side_effect=respond),
            start_worker(
                app,
                pool="solo",
                queues=[queue],
                perform_ping_check=False,
                shutdown_timeout=10,
            ),
        ):
            with patch("apps.jobs.services.app.send_task", side_effect=send):
                retry = submit_retry(job, uuid.uuid4(), consent_id=consent.pk)[0]
            deadline = time.monotonic() + 15
            while retry.status in {"queued", "running"} and time.monotonic() < deadline:
                time.sleep(0.1)
                retry.refresh_from_db()
        assert retry.status == "succeeded" and retry.previous_job_id == job.pk
        result = Explanation.objects.get(job=retry)
        run_process(read_history, str(result.pk))
    finally:
        with app.connection_for_write() as broker:
            broker.default_channel.queue_delete(queue)


def test_prefork_worker_renews_claim_while_waiting_without_request_deadline(
    preview: ContextPreview,
) -> None:
    from celery.contrib.testing.worker import start_worker

    import apps.explanations.tasks  # noqa: F401
    from config.celery import app

    class SyntheticProcess:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.returncode: int | None = None
            self.started = time.monotonic()

        def __enter__(self) -> "SyntheticProcess":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def communicate(
            self, payload: bytes | None = None, timeout: float | None = None
        ) -> tuple[bytes, bytes]:
            if time.monotonic() - self.started < 2:
                time.sleep(min(timeout or 2, 0.2))
                raise subprocess.TimeoutExpired("fixed-worker", timeout or 0)
            response = completion()
            response["choices"][0]["message"]["content"] = valid_content(
                preview.payload["snippets"][0]["source_ref"]
            )
            response["usage"] = {
                "prompt_tokens": 6464,
                "completion_tokens": 14623,
                "total_tokens": 21087,
            }
            self.returncode = 0
            return encode({"response": response}), b""

        def poll(self) -> int | None:
            return self.returncode

        def kill(self) -> None:
            self.returncode = -9

    queue, original_send = "m4-" + uuid.uuid4().hex, app.send_task

    def send(*args: Any, **kwargs: Any) -> Any:
        return original_send(*args, **kwargs, queue=queue)

    try:
        with (
            override_settings(JOB_EXECUTION_TIMEOUT_SECONDS=1),
            patch(
                "apps.explanations.adapter.credential",
                return_value="synthetic-test-only",
            ),
            patch("apps.explanations.adapter.subprocess.Popen", SyntheticProcess),
            start_worker(
                app,
                pool="prefork",
                concurrency=1,
                queues=[queue],
                perform_ping_check=False,
                shutdown_timeout=10,
            ),
        ):
            with patch("apps.jobs.services.app.send_task", side_effect=send):
                job = submit_explanation(
                    uuid.uuid4(), create_consent(preview, uuid.uuid4())[0].pk
                )[0]
            deadline = time.monotonic() + 15
            while job.status in {"queued", "running"} and time.monotonic() < deadline:
                time.sleep(0.1)
                jobs.reconcile_expired()
                job.refresh_from_db()
        assert job.status == "succeeded"
        assert (job.updated_at - job.created_at).total_seconds() >= 2
        explanation = Explanation.objects.get(job=job)
        assert (
            explanation.usage is not None
            and explanation.usage["completion_tokens"] == 14623
        )
    finally:
        with app.connection_for_write() as broker:
            broker.default_channel.queue_delete(queue)
