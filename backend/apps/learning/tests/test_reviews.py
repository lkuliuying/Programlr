import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections

from apps.analysis.models import Analysis
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from apps.learning.models import AttemptReview, Exercise, ExerciseAttempt
from apps.learning.reviews import submit_review
from apps.learning.services import submit_attempt
from apps.learning.tests.test_learning import analysis as analysis
from apps.learning.tests.test_learning import values
from common.errors import ApiProblem, Conflict

pytestmark = pytest.mark.django_db(transaction=True)


def test_review_history_idempotency_invalid_inputs_and_answer_unchanged(
    analysis: Analysis,
) -> None:
    data = values(analysis, Exercise.objects.get(kind="flow_order"))
    attempt = submit_attempt(uuid.uuid4(), {**data, "hint_used": True})[0]
    client, schema = client_with_token(), contract_schema()
    key = str(uuid.uuid4())
    body = {
        "attempt_id": str(attempt.pk),
        "judgement": "revisit",
        "note": "先核对校验，再重新练习。",
    }
    response = client.post(
        "/api/v1/attempt-reviews/", body, format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert response.status_code == 201
    assert_response(response, schema, "/api/v1/attempt-reviews/", "post")
    repeat = client.post(
        "/api/v1/attempt-reviews/", body, format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert repeat.status_code == 200 and repeat.json()["id"] == response.json()["id"]
    conflict = client.post(
        "/api/v1/attempt-reviews/",
        {**body, "judgement": "understood"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert (
        conflict.status_code == 409
        and conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    )
    for invalid in (
        {"judgement": "mastered"},
        {"note": "x" * 1001},
        {"note": None},
        {"correct": False},
    ):
        result = client.post(
            "/api/v1/attempt-reviews/",
            {**body, **invalid},
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        assert result.status_code == 400
    second = submit_review(
        uuid.uuid4(), {"attempt_id": attempt.pk, "judgement": "practicing", "note": ""}
    )[0]
    history = client.get(
        f"/api/v1/attempt-reviews/?attempt_id={attempt.pk}&page_size=1"
    )
    assert_response(history, schema, "/api/v1/attempt-reviews/", "get")
    assert history.json()["count"] == 2 and history.json()["results"][0]["id"] == str(
        second.pk
    )
    assert client.get(history.json()["next"]).status_code == 200
    assert client.get("/api/v1/attempt-reviews/").status_code == 400
    assert (
        client.get(f"/api/v1/attempt-reviews/?attempt_id={uuid.uuid4()}").status_code
        == 404
    )
    attempt.refresh_from_db()
    assert attempt.correct and attempt.hint_used and attempt.answer == data["answer"]


def test_concurrent_review_same_key_is_one_append(analysis: Analysis) -> None:
    attempt = submit_attempt(
        uuid.uuid4(), values(analysis, Exercise.objects.get(kind="flow_order"))
    )[0]
    data = {"attempt_id": attempt.pk, "judgement": "understood", "note": "仅为自评。"}
    key = uuid.uuid4()

    def submit(_: int) -> str:
        close_old_connections()
        try:
            return str(submit_review(key, data)[0].pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        identifiers = list(pool.map(submit, range(4)))
    assert len(set(identifiers)) == 1 and AttemptReview.objects.count() == 1
    with pytest.raises(Conflict):
        submit_review(key, {**data, "note": "不同内容"})


def test_reattempt_append_scope_and_legacy_null_replay(analysis: Analysis) -> None:
    exercise = Exercise.objects.get(kind="flow_order")
    data, key = values(analysis, exercise), uuid.uuid4()
    old = submit_attempt(key, data)[0]
    assert submit_attempt(key, {**data, "previous_attempt_id": None})[0].pk == old.pk
    client, schema = client_with_token(), contract_schema()
    new = client.post(
        "/api/v1/exercise-attempts/",
        {**data, "previous_attempt_id": str(old.pk), "hint_used": True},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert new.status_code == 201 and new.json()["previous_attempt_id"] == str(old.pk)
    assert_response(new, schema, "/api/v1/exercise-attempts/", "post")
    old.refresh_from_db()
    assert not old.hint_used and old.previous_attempt_id is None
    other = values(analysis, Exercise.objects.get(kind="code_location"))
    with pytest.raises(ApiProblem) as error:
        submit_attempt(uuid.uuid4(), {**other, "previous_attempt_id": old.pk})
    assert error.value.machine_code == "REATTEMPT_SCOPE_MISMATCH"
    ExerciseAttempt.objects.filter(pk=old.pk).update(endpoint_index=9999)
    with pytest.raises(ApiProblem) as error:
        submit_attempt(uuid.uuid4(), {**data, "previous_attempt_id": old.pk})
    assert error.value.machine_code == "REATTEMPT_SCOPE_MISMATCH"
