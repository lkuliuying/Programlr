import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from django.db import close_old_connections
from rest_framework.test import APIClient

from apps.jobs.models import Job
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import HOST, ORIGIN, client_with_token
from apps.learning.models import (
    CurriculumCardProgress,
    KnowledgeCard,
    KnowledgeCurriculum,
)
from apps.learning.progress import mark_card
from apps.learning.tests.history import seed_history
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def curriculum() -> KnowledgeCurriculum:
    seed_history()
    return KnowledgeCurriculum.objects.get()


def progress_url(curriculum: KnowledgeCurriculum) -> str:
    return f"/api/v1/knowledge-curricula/{curriculum.pk}/progress/"


def test_progress_get_no_writes_precise_order_and_historical_marks_preserved(
    curriculum: KnowledgeCurriculum,
) -> None:
    client, schema = client_with_token(), contract_schema()
    url = progress_url(curriculum)
    result = client.get(url)
    assert result.status_code == 200
    assert_response(
        result, schema, "/api/v1/knowledge-curricula/{curriculum_id}/progress/"
    )
    before = result.json()
    assert (
        before["curriculum_id"] == str(curriculum.pk)
        and before["version"] == curriculum.version
    )
    assert [(item["slug"], item["version"]) for item in before["cards"]] == [
        (node["slug"], node["card_version"]) for node in curriculum.definition["nodes"]
    ]
    assert before["completed_count"] == 0 and before["total_count"] == len(
        before["cards"]
    )
    assert not CurriculumCardProgress.objects.exists()
    card = before["cards"][0]
    target = url + card["card_id"] + "/"
    result = client.patch(target, {"completed": True}, format="json")
    assert result.status_code == 410 and result.json()["code"] == "FEATURE_RETIRED"
    assert_response(
        result,
        schema,
        "/api/v1/knowledge-curricula/{curriculum_id}/progress/{card_id}/",
        "patch",
    )
    assert client.patch(target, {"completed": True}, format="json").status_code == 410
    assert not CurriculumCardProgress.objects.exists()
    assert client.get(url).json() == before
    assert client.patch(target, {"completed": False}, format="json").status_code == 410
    CurriculumCardProgress.objects.create(
        curriculum=curriculum, card_id=card["card_id"], completed=True
    )
    historical = client.get(url).json()
    assert historical["completed_count"] == 1 and historical["cards"][0]["completed"]
    assert client.patch(target, {"completed": False}, format="json").status_code == 410
    assert client.get(url).json() == historical
    assert Job.objects.count() == 0


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"completed": None},
        {"completed": 1},
        {"completed": "true"},
        {"completed": True, "version": "other"},
        [],
    ],
)
def test_progress_retired_before_payload_validation(
    curriculum: KnowledgeCurriculum, payload: Any
) -> None:
    card = KnowledgeCard.objects.first()
    assert card is not None
    result = client_with_token().patch(
        progress_url(curriculum) + str(card.pk) + "/", payload, format="json"
    )
    assert result.status_code == 410 and result.json()["code"] == "FEATURE_RETIRED"
    assert_response(result, contract_schema())
    assert not CurriculumCardProgress.objects.exists()


def test_course_versions_and_card_versions_never_share_progress(
    curriculum: KnowledgeCurriculum,
) -> None:
    client = client_with_token()
    before = client.get(progress_url(curriculum)).json()
    card = KnowledgeCard.objects.get(pk=before["cards"][0]["card_id"])
    newer = KnowledgeCard.objects.create(
        slug=card.slug,
        version="2.0.0",
        title=card.title,
        body=card.body,
        applicability=card.applicability,
        review_note=card.review_note,
        content_digest="a" * 64,
    )
    invalid = client.patch(
        progress_url(curriculum) + str(newer.pk) + "/",
        {"completed": True},
        format="json",
    )
    assert invalid.status_code == 410
    second = KnowledgeCurriculum.objects.create(
        slug=curriculum.slug,
        version="2.0.0",
        title=curriculum.title,
        definition={**curriculum.definition, "version": "2.0.0"},
        content_digest="b" * 64,
    )
    assert (
        client.patch(
            progress_url(curriculum) + str(card.pk) + "/",
            {"completed": True},
            format="json",
        ).status_code
        == 410
    )
    CurriculumCardProgress.objects.create(
        curriculum=curriculum, card=card, completed=True
    )
    assert client.get(progress_url(second)).json()["completed_count"] == 0
    assert (
        client.patch(
            progress_url(second) + str(card.pk) + "/",
            {"completed": True},
            format="json",
        ).status_code
        == 410
    )
    CurriculumCardProgress.objects.create(curriculum=second, card=card, completed=True)
    assert CurriculumCardProgress.objects.count() == 2
    curriculum.definition["nodes"][0]["card_version"] = "missing"
    curriculum.save(update_fields=["definition"])
    failed = client.get(progress_url(curriculum))
    assert (
        failed.status_code == 409
        and failed.json()["code"] == "LEARNING_CONTENT_UNAVAILABLE"
    )
    assert CurriculumCardProgress.objects.count() == 2


def test_progress_security_and_missing_resources(
    curriculum: KnowledgeCurriculum,
) -> None:
    client = client_with_token()
    card_id = client.get(progress_url(curriculum)).json()["cards"][0]["card_id"]
    url = progress_url(curriculum) + card_id + "/"
    payload = {"completed": True}
    assert client.patch(url, payload, format="multipart").status_code == 410
    assert client.patch(url, "", content_type="application/json").status_code == 410
    assert client.get(progress_url(curriculum) + "?version=old").status_code == 400
    assert client.patch(url + "?version=old", payload, format="json").status_code == 410
    for origin, code in [
        (ORIGIN, "CSRF_REJECTED"),
        ("http://untrusted.invalid", "ORIGIN_REJECTED"),
    ]:
        response = APIClient(enforce_csrf_checks=True).patch(
            url, payload, format="json", HTTP_HOST=HOST, HTTP_ORIGIN=origin
        )
        assert response.status_code == 403 and response.json()["code"] == code
    assert (
        client.get(f"/api/v1/knowledge-curricula/{uuid.uuid4()}/progress/").status_code
        == 404
    )
    assert (
        client.patch(
            progress_url(curriculum) + str(uuid.uuid4()) + "/", payload, format="json"
        ).status_code
        == 410
    )
    assert not CurriculumCardProgress.objects.exists()


def test_concurrent_marks_do_not_write_course_card_records(
    curriculum: KnowledgeCurriculum,
) -> None:
    card_id = uuid.UUID(
        client_with_token().get(progress_url(curriculum)).json()["cards"][0]["card_id"]
    )

    def mark(_: int) -> None:
        close_old_connections()
        try:
            with pytest.raises(ApiProblem) as error:
                mark_card(curriculum.pk, card_id, True)
            assert error.value.machine_code == "FEATURE_RETIRED"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(mark, range(4)))
    assert not CurriculumCardProgress.objects.exists()
