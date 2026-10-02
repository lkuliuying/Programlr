import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.db import DatabaseError, close_old_connections
from django.test import override_settings
from django.utils import timezone
from kombu.exceptions import OperationalError

from apps.analysis.models import Analysis
from apps.analysis.services import execute_analysis, submit_analysis
from apps.analysis.tests.test_analysis import imported
from apps.explanations.configuration import digest, encode
from apps.explanations.context import build_payload, check_preview
from apps.explanations.models import (
    ContextConsent,
    ContextPreview,
    Explanation,
    ExplanationRequest,
)
from apps.explanations.services import (
    create_consent,
    create_preview,
    execute_explanation,
    submit_explanation,
)
from apps.explanations.tests.test_adapter import OPTIONS, completion, valid_content
from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.jobs.retries import submit_retry
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from common.errors import ApiProblem, Conflict

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def preview(tmp_path: Path) -> Any:
    with override_settings(
        IMPORT_STORAGE_ROOT=str(tmp_path / "storage"),
        MODEL_OPTIONS=OPTIONS,
        APP_ORIGIN="http://127.0.0.1:5173",
        APP_AUTHORITY="127.0.0.1:5173",
    ):
        snapshot = imported()
        with patch("apps.jobs.services.app.send_task"):
            job = submit_analysis(snapshot, uuid.uuid4(), "root_urls.py")[0]
        execute_analysis(str(job.pk))
        analysis = Analysis.objects.get(job=job)
        yield create_preview(uuid.uuid4(), analysis.pk, 0, None)[0]


def submit(preview: ContextPreview) -> Job:
    consent = create_consent(preview, uuid.uuid4())[0]
    with patch("apps.jobs.services.app.send_task"):
        return submit_explanation(uuid.uuid4(), consent.pk)[0]


def test_preview_consent_api_and_immutable_messages(preview: ContextPreview) -> None:
    client, schema = client_with_token(), contract_schema()
    with (
        patch("apps.explanations.services.complete") as model,
        patch("apps.jobs.services.app.send_task") as queue,
    ):
        result = client.get(f"/api/v1/context-previews/{preview.pk}/")
        assert_response(result, schema, "/api/v1/context-previews/{preview_id}/", "get")
        assert result.json()["messages"] == preview.payload["messages"]
        assert preview.payload["context_bytes"] == len(
            encode(preview.payload["messages"])
        )
        denied = client.post(
            f"/api/v1/context-previews/{preview.pk}/consents/",
            {"accepted": False},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        assert denied.status_code == 400
        confirmed = client.post(
            f"/api/v1/context-previews/{preview.pk}/consents/",
            {"accepted": True},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        assert confirmed.status_code == 201
        assert_response(
            confirmed, schema, "/api/v1/context-previews/{preview_id}/consents/", "post"
        )
        model.assert_not_called()
        queue.assert_not_called()
        key = str(uuid.uuid4())
        first = client.post(
            "/api/v1/explanations/",
            {"consent_id": confirmed.json()["id"]},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert first.status_code == 202
        assert_response(first, schema, "/api/v1/explanations/", "post")
        repeated = client.post(
            "/api/v1/explanations/",
            {"consent_id": confirmed.json()["id"]},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert (
            repeated.status_code == 200 and repeated.json()["id"] == first.json()["id"]
        )
        another = client.post(
            "/api/v1/explanations/",
            {"consent_id": confirmed.json()["id"]},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        assert another.status_code == 409 and queue.call_count == 1


def test_idempotent_preview_conflict_and_config_stale(preview: ContextPreview) -> None:
    assert create_preview(preview.idempotency_key, preview.analysis_id, 0, None) == (
        preview,
        False,
    )
    with pytest.raises(Conflict):
        create_preview(preview.idempotency_key, preview.analysis_id, 1, None)
    consent = create_consent(preview, uuid.uuid4())[0]
    with (
        override_settings(MODEL_OPTIONS={**OPTIONS, "model": "changed"}),
        pytest.raises(ApiProblem) as failure,
    ):
        submit_explanation(uuid.uuid4(), consent.pk)
    assert (
        failure.value.machine_code == "CONSENT_STALE"
        and not ExplanationRequest.objects.exists()
    )
    preview.payload["snippets"][0]["content"] = "changed"
    preview.payload_digest = digest(preview.payload)
    with pytest.raises(ApiProblem):
        check_preview(preview)


def test_selection_is_complete_and_prompt_injection_is_data(
    preview: ContextPreview,
) -> None:
    analysis = preview.analysis
    with pytest.raises(ApiProblem):
        build_payload(analysis, 0, [str(uuid.uuid4())])
    with override_settings(MODEL_OPTIONS={**OPTIONS, "context_bytes": "1"}):
        full = build_payload(analysis, 0, None)
    assert full["snippets"] == preview.payload["snippets"]
    assert "context_bytes" not in full["omissions"]
    assert "不可信数据" in preview.payload["messages"][0]["content"]
    assert "relations" in json.loads(preview.payload["messages"][1]["content"])
    reduced = build_payload(analysis, 0, [preview.payload["nodes"][0]["id"]])
    assert len(reduced["nodes"]) == 1
    removed = preview.payload["snippets"][0]["id"]
    excluded = build_payload(analysis, 0, None, [removed])
    assert removed not in {item["id"] for item in excluded["snippets"]}
    assert "user_excluded" in excluded["omissions"]


def test_concurrent_same_key_and_single_consent(preview: ContextPreview) -> None:
    consent, key = create_consent(preview, uuid.uuid4())[0], uuid.uuid4()

    def operation(_: int) -> str:
        close_old_connections()
        try:
            return str(submit_explanation(key, consent.pk)[0].pk)
        finally:
            close_old_connections()

    with (
        patch("apps.jobs.services.app.send_task") as queue,
        ThreadPoolExecutor(max_workers=4) as executor,
    ):
        ids = list(executor.map(operation, range(4)))
    assert (
        len(set(ids)) == 1
        and queue.call_count == 1
        and ExplanationRequest.objects.count() == 1
    )


def test_worker_validates_once_and_publishes_atomically(
    preview: ContextPreview,
) -> None:
    job = submit(preview)
    output = valid_content(preview.payload["snippets"][0]["source_ref"])
    with patch(
        "apps.explanations.services.complete", return_value=(output, "test-model", None)
    ) as model:
        execute_explanation(str(job.pk))
        execute_explanation(str(job.pk))
    assert (
        model.call_count == 1 and model.call_args.args[1] == preview.payload["messages"]
    )
    job.refresh_from_db()
    assert job.status == "succeeded" and Explanation.objects.count() == 1
    client, schema = client_with_token(), contract_schema()
    assert job.result_url is not None
    response = client.get(job.result_url)
    assert_response(response, schema, "/api/v1/explanations/{explanation_id}/", "get")
    assert response.json()["usage"] is None
    history = client.get(
        f"/api/v1/explanations/?snapshot_id={preview.snapshot_id}&analysis_id={preview.analysis_id}&endpoint_index=0&page=1&page_size=1"
    )
    assert history.status_code == 200 and history.json()["count"] == 1


@pytest.mark.parametrize("mode", ["invalid", "write_failure", "late", "stale"])
def test_failure_never_publishes_result(preview: ContextPreview, mode: str) -> None:
    job = submit(preview)

    def output(*args: Any) -> tuple[str, str, None]:
        if mode == "late":
            Job.objects.filter(pk=job.pk).update(
                expires_at=timezone.now() - timedelta(seconds=1)
            )
            jobs.reconcile_expired()
        return (
            "invalid"
            if mode == "invalid"
            else valid_content(preview.payload["snippets"][0]["source_ref"]),
            "test-model",
            None,
        )

    with patch("apps.explanations.services.complete", side_effect=output) as model:
        if mode == "write_failure":
            with patch(
                "apps.explanations.services.Explanation.objects.create",
                side_effect=DatabaseError,
            ):
                execute_explanation(str(job.pk))
        elif mode == "stale":
            with override_settings(MODEL_OPTIONS={**OPTIONS, "model": "changed"}):
                execute_explanation(str(job.pk))
            model.assert_not_called()
        else:
            execute_explanation(str(job.pk))
    job.refresh_from_db()
    assert job.status == "failed" and not Explanation.objects.exists()


def test_failed_publish_and_explicit_retry_need_new_consent(
    preview: ContextPreview,
) -> None:
    consent = create_consent(preview, uuid.uuid4())[0]
    with patch("apps.jobs.services.app.send_task", side_effect=OperationalError):
        job, _, published = submit_explanation(uuid.uuid4(), consent.pk)
    assert not published and job.status == "failed"
    with pytest.raises(ApiProblem):
        submit_retry(job, uuid.uuid4())
    with pytest.raises(ApiProblem):
        submit_retry(job, uuid.uuid4(), consent_id=consent.pk)
    new = create_consent(preview, uuid.uuid4())[0]
    with patch("apps.jobs.services.app.send_task"):
        retry = submit_retry(job, uuid.uuid4(), consent_id=new.pk)[0]
    assert retry.previous_job_id == job.pk and retry.snapshot_id == preview.snapshot_id


@pytest.mark.parametrize("tokens", [None, 4096, 4097, 14623])
def test_reported_usage_does_not_prevent_valid_result_publishing(
    preview: ContextPreview, tokens: int | None
) -> None:
    output = valid_content(preview.payload["snippets"][0]["source_ref"])
    previous = submit(preview)
    with patch(
        "apps.explanations.services.complete", return_value=(output, "test-model", None)
    ):
        execute_explanation(str(previous.pk))
    preserved = Explanation.objects.get(job=previous)
    job = submit(preview)
    response = completion()
    response["choices"][0]["message"]["content"] = output
    if tokens is not None:
        response["usage"] = {
            "prompt_tokens": 6464,
            "completion_tokens": tokens,
            "total_tokens": 6464 + tokens,
        }
    with (
        patch(
            "apps.explanations.adapter.credential", return_value="synthetic-test-only"
        ),
        patch("apps.explanations.adapter.subprocess.Popen") as transport,
    ):
        process = transport.return_value.__enter__.return_value
        process.returncode = 0
        process.communicate.return_value = (encode({"response": response}), b"")
        execute_explanation(str(job.pk))
        execute_explanation(str(job.pk))
    transport.assert_called_once()
    job.refresh_from_db()
    client = client_with_token()
    result = client.get(f"/api/v1/jobs/{job.pk}/")
    assert_response(result, contract_schema(), "/api/v1/jobs/{job_id}/", "get")
    assert job.status == "succeeded"
    saved = Explanation.objects.get(job=job)
    assert saved.usage == response.get("usage")
    preserved.refresh_from_db()
    assert preserved.content == json.loads(output) and preserved.usage is None
    assert client.get(f"/api/v1/explanations/{preserved.pk}/").status_code == 200


def test_legacy_budget_preview_is_readable_but_consent_is_stale(
    preview: ContextPreview,
) -> None:
    preview.payload["configuration"].update(
        timeout=60, context_bytes=65536, output_tokens=4096, token_field="max_tokens"
    )
    preview.payload_digest = digest(preview.payload)
    preview.save(update_fields=["payload", "payload_digest"])
    consent = ContextConsent.objects.create(
        preview=preview, idempotency_key=uuid.uuid4()
    )
    with (
        patch("apps.explanations.services.complete") as model,
        patch("apps.jobs.services.app.send_task") as queue,
    ):
        with pytest.raises(ApiProblem) as failure:
            submit_explanation(uuid.uuid4(), consent.pk)
        assert failure.value.machine_code == "CONSENT_STALE"
        assert not ExplanationRequest.objects.exists()
        fresh = create_preview(uuid.uuid4(), preview.analysis_id, 0, None)[0]
        assert fresh.payload["configuration"] == OPTIONS
        assert fresh.payload_digest != preview.payload_digest
        create_consent(fresh, uuid.uuid4())
    model.assert_not_called()
    queue.assert_not_called()
    response = client_with_token().get(f"/api/v1/context-previews/{preview.pk}/")
    assert response.status_code == 200
    assert response.json()["configuration"]["output_tokens"] == 4096
    assert_response(
        response, contract_schema(), "/api/v1/context-previews/{preview_id}/", "get"
    )


def test_lease_renewal_allows_long_request_but_never_revives_expired_claim(
    preview: ContextPreview,
) -> None:
    job = submit(preview)
    with override_settings(JOB_EXECUTION_TIMEOUT_SECONDS=1):
        claim = jobs.claim_explanation(str(job.pk))
        assert claim is not None
        job.refresh_from_db()
        original_deadline = job.expires_at
        with patch(
            "apps.jobs.services.timezone.now",
            return_value=original_deadline - timedelta(milliseconds=100),
        ):
            assert jobs.renew_explanation_claim(str(job.pk), claim)
        with patch(
            "apps.jobs.services.timezone.now",
            return_value=original_deadline + timedelta(milliseconds=100),
        ):
            assert jobs.reconcile_expired() == 0
            assert jobs.explanation_claim_valid(str(job.pk), claim)
            assert not jobs.renew_explanation_claim(str(job.pk), uuid.uuid4())
        job.refresh_from_db()
        with patch(
            "apps.jobs.services.timezone.now",
            return_value=job.expires_at + timedelta(milliseconds=100),
        ):
            assert not jobs.renew_explanation_claim(str(job.pk), claim)
            assert jobs.reconcile_expired() == 1
            assert not jobs.complete_explanation(str(job.pk), claim, lambda: "late")


def test_only_explanation_task_has_no_celery_execution_deadline() -> None:
    from importlib import import_module

    from config.celery import app

    import_module("apps.explanations.tasks")
    import_module("apps.jobs.tasks")
    task = app.tasks["explanations.generate"]
    assert task.time_limit == 0 and task.soft_time_limit == 0
    assert app.conf.task_time_limit == 0 and app.conf.task_soft_time_limit == 0
    assert app.tasks["jobs.system_check"].time_limit != 0


def test_context_above_retired_byte_budget_is_complete(preview: ContextPreview) -> None:
    with patch(
        "apps.explanations.context.source_content", return_value="示例源码\n" * 20_000
    ):
        payload = build_payload(preview.analysis, 0, None)
    assert payload["context_bytes"] > 65536
    assert len(payload["snippets"]) == len(preview.payload["snippets"])
    assert "context_bytes" not in payload["omissions"]
