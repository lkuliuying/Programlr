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
from apps.learning.tests.history import historical_attempt
from apps.learning.tests.test_learning import analysis as analysis
from apps.learning.tests.test_learning import values
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)


def test_review_history_readable_retired_requests_do_not_change_answer(
    analysis: Analysis,
) -> None:
    data = values(analysis, Exercise.objects.get(kind="flow_order"))
    attempt = historical_attempt({**data, "hint_used": True})
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
    assert response.status_code == 410 and response.json()["code"] == "FEATURE_RETIRED"
    assert_response(response, schema, "/api/v1/attempt-reviews/", "post")
    repeat = client.post(
        "/api/v1/attempt-reviews/", body, format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert repeat.status_code == 410
    conflict = client.post(
        "/api/v1/attempt-reviews/",
        {**body, "judgement": "understood"},
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert conflict.status_code == 410 and conflict.json()["code"] == "FEATURE_RETIRED"
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
        assert result.status_code == 410 and result.json()["code"] == "FEATURE_RETIRED"
    assert not AttemptReview.objects.exists()
    AttemptReview.objects.create(
        attempt=attempt,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
        judgement="revisit",
        note=body["note"],
    )
    second = AttemptReview.objects.create(
        attempt=attempt,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
        judgement="practicing",
        note="",
    )
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


def test_concurrent_review_same_key_never_appends(analysis: Analysis) -> None:
    attempt = historical_attempt(
        values(analysis, Exercise.objects.get(kind="flow_order"))
    )
    data = {"attempt_id": attempt.pk, "judgement": "understood", "note": "仅为自评。"}
    key = uuid.uuid4()

    def submit(_: int) -> str:
        close_old_connections()
        try:
            with pytest.raises(ApiProblem) as error:
                submit_review(key, data)
            return error.value.machine_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        identifiers = list(pool.map(submit, range(4)))
    assert (
        set(identifiers) == {"FEATURE_RETIRED"} and AttemptReview.objects.count() == 0
    )
    with pytest.raises(ApiProblem, match="已退役"):
        submit_review(key, {**data, "note": "不同内容"})


def test_historical_reattempt_chain_readable_but_no_new_or_replayed_attempt(
    analysis: Analysis,
) -> None:
    exercise = Exercise.objects.get(kind="flow_order")
    data, key = values(analysis, exercise), uuid.uuid4()
    old = historical_attempt(data)
    with pytest.raises(ApiProblem) as error:
        submit_attempt(key, {**data, "previous_attempt_id": None})
    assert error.value.machine_code == "FEATURE_RETIRED"
    client, schema = client_with_token(), contract_schema()
    new = client.post(
        "/api/v1/exercise-attempts/",
        {**data, "previous_attempt_id": str(old.pk), "hint_used": True},
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert new.status_code == 410 and new.json()["code"] == "FEATURE_RETIRED"
    assert_response(new, schema, "/api/v1/exercise-attempts/", "post")
    old.refresh_from_db()
    assert not old.hint_used and old.previous_attempt_id is None
    historical = historical_attempt(
        {**data, "previous_attempt_id": old.pk, "hint_used": True}
    )
    detail = client.get(f"/api/v1/exercise-attempts/{historical.pk}/")
    assert detail.status_code == 200 and detail.json()["previous_attempt_id"] == str(
        old.pk
    )
    assert ExerciseAttempt.objects.count() == 2
    other = values(analysis, Exercise.objects.get(kind="code_location"))
    with pytest.raises(ApiProblem) as error:
        submit_attempt(uuid.uuid4(), {**other, "previous_attempt_id": old.pk})
    assert error.value.machine_code == "FEATURE_RETIRED"
    ExerciseAttempt.objects.filter(pk=old.pk).update(endpoint_index=9999)
    with pytest.raises(ApiProblem) as error:
        submit_attempt(uuid.uuid4(), {**data, "previous_attempt_id": old.pk})
    assert error.value.machine_code == "FEATURE_RETIRED"
