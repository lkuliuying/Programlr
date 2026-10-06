import json
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.test import override_settings

from apps.analysis.models import Analysis
from apps.analysis.services import execute_analysis, submit_analysis
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from apps.learning.content import CONTENT_ROOT, load_cards_only, load_content
from apps.learning.models import Exercise, ExerciseAttempt, KnowledgeCard
from apps.learning.services import applicability, submit_attempt, validate_answer
from apps.learning.tests.history import historical_attempt, seed_history
from apps.projects.models import Snapshot, SourceFile
from apps.projects.services import create_project, execute_import, submit_import
from apps.projects.tests.test_archive import zip_bytes
from apps.projects.tests.test_projects import upload
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def analysis(tmp_path: Path) -> Any:
    with override_settings(
        IMPORT_STORAGE_ROOT=str(tmp_path / "storage"),
        APP_ORIGIN="http://127.0.0.1:5173",
        APP_AUTHORITY="127.0.0.1:5173",
    ):
        seed_history()
        root = CONTENT_ROOT.parent / "examples/task-board"
        bundle = json.loads(
            (CONTENT_ROOT / "exercises/task-board-create.json").read_text()
        )
        archive = zip_bytes(
            {path: (root / path).read_bytes() for path in bundle["files"]}
        )
        with patch("apps.jobs.services.app.send_task"):
            job = submit_import(
                create_project(uuid.uuid4(), "题目验收")[0],
                uuid.uuid4(),
                upload(archive),
            )[0]
        execute_import(str(job.pk))
        snapshot = Snapshot.objects.get(job=job)
        with patch("apps.jobs.services.app.send_task"):
            task = submit_analysis(snapshot, uuid.uuid4(), "backend/config/urls.py")[0]
        execute_analysis(str(task.pk))
        yield Analysis.objects.get(job=task)


def values(analysis: Analysis, exercise: Exercise) -> dict[str, Any]:
    index = next(
        i
        for i, endpoint in enumerate(analysis.endpoints)
        if endpoint["method"] == "POST" and endpoint["path"] == "/api/v1/tasks/"
    )
    return {
        "analysis_id": analysis.pk,
        "snapshot_id": analysis.snapshot_id,
        "endpoint_index": index,
        "exercise_id": exercise.pk,
        "exercise_version": exercise.version,
        "answer": exercise.answer,
        "hint_used": False,
    }


def test_three_historical_types_remain_readable_and_attempt_api_is_retired(
    analysis: Analysis,
) -> None:
    client, schema = client_with_token(), contract_schema()
    assert KnowledgeCard.objects.count() == 29 and Exercise.objects.count() == 3
    for exercise in Exercise.objects.select_related("example"):
        data = values(analysis, exercise)
        listing = client.get(
            f"/api/v1/exercises/?analysis_id={analysis.pk}&endpoint_index={data['endpoint_index']}"
        )
        assert_response(listing, schema, "/api/v1/exercises/", "get")
        for item in listing.json()["results"]:
            assert item["applicable"] and not {
                "answer",
                "explanation",
                "source_refs",
            } & set(item)
        key = str(uuid.uuid4())
        result = client.post(
            "/api/v1/exercise-attempts/", data, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
        assert result.status_code == 410 and result.json()["code"] == "FEATURE_RETIRED"
        assert_response(result, schema, "/api/v1/exercise-attempts/", "post")
        repeat = client.post(
            "/api/v1/exercise-attempts/", data, format="json", HTTP_IDEMPOTENCY_KEY=key
        )
        assert repeat.status_code == 410
        historical_attempt(data)
        if exercise.kind == "flow_order":
            wrong: Any = list(reversed(exercise.answer))
        elif exercise.kind == "error_prediction":
            wrong = {key: {"status": 200, "writes": 0} for key in exercise.answer}
        else:
            wrong = {**exercise.answer, "start_line": 1, "end_line": 1}
        attempt = historical_attempt(
            {**data, "answer": wrong, "hint_used": True}, correct=False
        )
        assert not attempt.correct and attempt.hint_used
        detail = client.get(f"/api/v1/exercise-attempts/{attempt.pk}/")
        assert_response(
            detail, schema, "/api/v1/exercise-attempts/{attempt_id}/", "get"
        )
    assert ExerciseAttempt.objects.count() == 6
    history = client.get(
        f"/api/v1/exercise-attempts/?snapshot_id={analysis.snapshot_id}&analysis_id={analysis.pk}&endpoint_index={data['endpoint_index']}&page=1&page_size=2"
    )
    assert history.status_code == 200 and history.json()["count"] == 6
    assert history.json()["next"] is not None
    assert client.get(history.json()["next"]).status_code == 200


def test_invalid_version_digest_and_types(analysis: Analysis) -> None:
    for exercise in Exercise.objects.select_related("example"):
        data = values(analysis, exercise)
        invalid_values: list[Any] = [None, {}, [], "answer", True]
        for invalid in invalid_values:
            with pytest.raises(ApiProblem):
                validate_answer(exercise.kind, exercise.options, invalid)
        with pytest.raises(ApiProblem) as failure:
            submit_attempt(uuid.uuid4(), {**data, "exercise_version": "old"})
        assert failure.value.machine_code == "FEATURE_RETIRED"
        with pytest.raises(ApiProblem) as failure:
            submit_attempt(uuid.uuid4(), {**data, "snapshot_id": uuid.uuid4()})
        assert failure.value.machine_code == "FEATURE_RETIRED"
    SourceFile.objects.filter(snapshot=analysis.snapshot).update(sha256="0" * 64)
    assert not applicability(exercise, analysis, data["endpoint_index"])[0]
    with pytest.raises(ApiProblem) as failure:
        submit_attempt(uuid.uuid4(), data)
    assert (
        failure.value.machine_code == "FEATURE_RETIRED"
        and not ExerciseAttempt.objects.exists()
    )


def test_concurrent_attempt_requests_never_create_or_replay_records(
    analysis: Analysis,
) -> None:
    data, key = values(analysis, Exercise.objects.get(kind="flow_order")), uuid.uuid4()

    def operation(_: int) -> str:
        close_old_connections()
        try:
            with pytest.raises(ApiProblem) as error:
                submit_attempt(key, data)
            return error.value.machine_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=4) as executor:
        ids = list(executor.map(operation, range(4)))
    assert set(ids) == {"FEATURE_RETIRED"} and ExerciseAttempt.objects.count() == 0
    with pytest.raises(ApiProblem, match="已退役"):
        submit_attempt(key, {**data, "hint_used": True})


def test_immutable_content_upgrade_keeps_old_attempts(
    analysis: Analysis, tmp_path: Path
) -> None:
    exercise = Exercise.objects.get(kind="code_location")
    attempt = historical_attempt(values(analysis, exercise))
    assert load_content() == (29, 0)
    assert Exercise.objects.count() == 3
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_ROOT, directory)
    path = directory / "knowledge/source-mainline.json"
    cards = json.loads(path.read_text())
    cards[0]["body"] += " 新版本"
    path.write_text(json.dumps(cards))
    with pytest.raises(ValueError, match="同版本"):
        load_cards_only(directory)
    cards[0]["version"] = "1.2.0"
    path.write_text(json.dumps(cards))
    load_cards_only(directory)
    assert Exercise.objects.count() == 3 and KnowledgeCard.objects.count() == 30
    attempt.refresh_from_db()
    assert attempt.exercise.version == "1.0.0" and attempt.correct
