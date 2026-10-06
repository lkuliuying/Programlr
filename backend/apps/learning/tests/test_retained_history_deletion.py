import uuid

import pytest

from apps.analysis.models import Analysis
from apps.jobs.tests.test_jobs import client_with_token
from apps.learning.models import (
    AttemptReview,
    Exercise,
    ExerciseAttempt,
    KnowledgeCurriculum,
)
from apps.learning.tests.history import historical_attempt
from apps.learning.tests.test_learning import analysis as analysis
from apps.learning.tests.test_learning import values
from apps.projects.models import Project, Snapshot

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("target", ["snapshot", "project"])
def test_retained_learning_reads_are_isolated_while_deletion_marker_remains(
    analysis: Analysis, target: str
) -> None:
    exercise = Exercise.objects.get(kind="flow_order")
    data = values(analysis, exercise)
    attempt = historical_attempt(data)
    review = AttemptReview.objects.create(
        attempt=attempt,
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
        judgement="revisit",
        note="只供历史读取核对的自评记录。",
    )
    client = client_with_token()
    workspace = {
        "analysis_id": str(analysis.pk),
        "endpoint_index": str(data["endpoint_index"]),
    }
    path = {
        **workspace,
        "curriculum_id": str(KnowledgeCurriculum.objects.get().pk),
    }
    reads = [
        (f"/api/v1/exercise-attempts/{attempt.pk}/", {}),
        ("/api/v1/attempt-reviews/", {"attempt_id": str(attempt.pk)}),
        ("/api/v1/exercises/", workspace),
        (f"/api/v1/exercises/{exercise.pk}/", workspace),
        ("/api/v1/learning-paths/", path),
    ]
    for url, query in reads:
        assert client.get(url, query).status_code == 200
    assert client.get("/api/v1/exercise-attempts/").json()["count"] == 1
    assert (
        client.get("/api/v1/attempt-reviews/", {"attempt_id": str(attempt.pk)}).json()[
            "results"
        ][0]["note"]
        == review.note
    )

    if target == "snapshot":
        Snapshot.objects.filter(pk=analysis.snapshot_id).update(
            deletion_request_id=uuid.uuid4()
        )
    else:
        Project.objects.filter(pk=analysis.snapshot.project_id).update(
            deletion_request_id=uuid.uuid4()
        )
    for query in ({}, {"snapshot_id": str(analysis.snapshot_id)}, workspace):
        response = client.get("/api/v1/exercise-attempts/", query)
        assert response.status_code == 200
        assert response.json()["count"] == 0 and response.json()["results"] == []
    for url, query in reads:
        response = client.get(url, query)
        assert response.status_code == 410
        assert response.json()["code"] == "RESOURCE_DELETING"
        assert not {"answer", "feedback", "note"} & response.json().keys()
    assert ExerciseAttempt.objects.filter(pk=attempt.pk).exists()
    assert AttemptReview.objects.filter(pk=review.pk).exists()
    assert client.get("/api/v1/knowledge-cards/").status_code == 200
    assert client.get("/api/v1/knowledge-curricula/").status_code == 200
