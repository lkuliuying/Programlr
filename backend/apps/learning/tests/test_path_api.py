import json
import shutil
import uuid
from pathlib import Path

import pytest

from apps.analysis.models import Analysis
from apps.jobs.tests.test_contract import assert_response, contract_schema
from apps.jobs.tests.test_jobs import client_with_token
from apps.learning.content import CONTENT_ROOT, load_cards_only
from apps.learning.models import Exercise, KnowledgeCard, KnowledgeCurriculum
from apps.learning.paths.publication import load_curricula, validate_definition
from apps.learning.tests.test_learning import analysis as analysis
from apps.learning.tests.test_learning import values
from apps.projects.models import SourceFile
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db(transaction=True)


def test_published_curriculum_path_and_no_get_writes(analysis: Analysis) -> None:
    client, schema = client_with_token(), contract_schema()
    curriculum = KnowledgeCurriculum.objects.get()
    data = values(analysis, Exercise.objects.get(kind="flow_order"))
    query = f"analysis_id={analysis.pk}&endpoint_index={data['endpoint_index']}&curriculum_id={curriculum.pk}"
    for path, template in [
        ("/api/v1/knowledge-curricula/", "/api/v1/knowledge-curricula/"),
        (
            f"/api/v1/knowledge-curricula/{curriculum.pk}/",
            "/api/v1/knowledge-curricula/{curriculum_id}/",
        ),
        ("/api/v1/learning-paths/?" + query, "/api/v1/learning-paths/"),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert_response(response, schema, template)
    result = client.get("/api/v1/learning-paths/?" + query).json()
    assert result["applicable"] and result["order"] == [
        "http",
        "react-state",
        "validation",
        "serialization",
        "orm",
    ]
    assert [item["slug"] for item in result["steps"]] == result["order"]
    assert "container-network" not in result["order"]
    assert client.get(
        "/api/v1/learning-paths/?" + query + "&goal=container-network"
    ).json()["order"] == ["http", "container-network"]
    for suffix in (
        "&goal=no-such-goal",
        "&goal=create-task&goal=subprocess",
        "&arbitrary=true",
        "&endpoint_index=0",
    ):
        assert (
            client.get("/api/v1/learning-paths/?" + query + suffix).status_code == 400
        )
    SourceFile.objects.filter(snapshot_id=analysis.snapshot_id).update(sha256="0" * 64)
    result = client.get("/api/v1/learning-paths/?" + query).json()
    assert not result["applicable"] and result["order"] == [] and result["steps"] == []
    assert (
        KnowledgeCurriculum.objects.count() == 1 and KnowledgeCard.objects.count() == 29
    )
    assert client.get("/api/v1/learning-paths/").status_code == 400
    assert client.get(f"/api/v1/knowledge-curricula/{uuid.uuid4()}/").status_code == 404


def test_publication_drift_unknown_card_cycle_and_atomic_rollback(
    analysis: Analysis, tmp_path: Path
) -> None:
    copied = tmp_path / "content"
    shutil.copytree(CONTENT_ROOT, copied)
    path = copied / "paths/task-board-foundations.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    for change in ("cycle", "card", "drift"):
        value = json.loads(json.dumps(original))
        value["version"] = "1.1.0" if change != "drift" else "1.0.0"
        if change == "cycle":
            value["edges"].append({"prerequisite": "orm", "dependent": "http"})
        elif change == "card":
            value["nodes"][0]["card_version"] = "missing"
        else:
            value["title"] = "同版本漂移"
        path.write_text(json.dumps(value), encoding="utf-8")
        cards_path = copied / "knowledge/learning-systems.json"
        cards = json.loads(cards_path.read_text(encoding="utf-8"))
        cards[0]["version"] = "2.0.0"
        cards_path.write_text(json.dumps(cards), encoding="utf-8")
        with pytest.raises(ApiProblem) as retired:
            load_curricula(copied)
        assert retired.value.machine_code == "FEATURE_RETIRED"
        if change != "drift":
            with pytest.raises(ValueError):
                validate_definition(value)
        else:
            assert KnowledgeCurriculum.objects.get().title != value["title"]
        assert KnowledgeCurriculum.objects.count() == 1
        assert not KnowledgeCard.objects.filter(version="2.0.0").exists()
        shutil.copyfile(CONTENT_ROOT / "knowledge/learning-systems.json", cards_path)
    original["version"] = "1.1.0"
    path.write_text(json.dumps(original), encoding="utf-8")
    load_cards_only(copied)
    assert set(KnowledgeCurriculum.objects.values_list("version", flat=True)) == {
        "1.0.0"
    }
