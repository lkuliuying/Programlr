import json
import uuid

import pytest

from apps.jobs.tests.test_contract import contract_schema
from apps.jobs.tests.test_jobs import client_with_token

PATH = "/api/v1/snapshots/{snapshot_id}/analyses/"


def test_analysis_contract_has_strict_input_and_evidence() -> None:
    schema = contract_schema()
    creation = schema["paths"][PATH]["post"]
    assert creation["requestBody"]["required"]
    assert set(creation["responses"]) >= {
        "200",
        "202",
        "400",
        "403",
        "404",
        "409",
        "413",
        "415",
        "503",
    }
    inputs = schema["components"]["schemas"]["AnalysisInputRequest"]
    assert inputs["additionalProperties"] is False
    assert inputs["required"] == ["root_urlconf"]
    ref = schema["components"]["schemas"]["SourceRef"]["properties"]
    assert ref["snapshot_id"]["format"] == "uuid"
    assert ref["start_line"]["minimum"] == 1
    assert schema["components"]["schemas"]["Evidence"]["properties"]["kind"] == {
        "$ref": "#/components/schemas/KindEnum"
    }
    graph = schema["paths"]["/api/v1/analyses/{analysis_id}/graph/"]["get"]
    assert graph["operationId"] == "analysis_graph_retrieve"
    parameters = {p["name"]: p["schema"] for p in graph["parameters"]}
    assert parameters["root_node_id"]["format"] == "uuid"
    assert parameters["algorithm"]["enum"] == ["bfs", "dfs"]
    assert parameters["max_nodes"] == {
        "type": "integer",
        "maximum": 1000,
        "minimum": 1,
        "default": 200,
    }
    assert parameters["max_edges"] == {
        "type": "integer",
        "maximum": 2000,
        "minimum": 1,
        "default": 400,
    }
    assert {"200", "400", "404", "409", "500", "503"} <= graph["responses"].keys()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        None,
        {"root_urlconf": 1},
        {"root_urlconf": "../urls.py"},
        {"root_urlconf": "/etc/urls.py"},
        {"root_urlconf": "C:/urls.py"},
        {"root_urlconf": "a\\urls.py"},
        {"root_urlconf": "urls.py", "command": "ignored"},
    ],
)
def test_analysis_rejects_invalid_inputs_before_database(payload: object) -> None:
    response = client_with_token().generic(
        "POST",
        PATH.format(snapshot_id=uuid.uuid4()),
        json.dumps(payload),
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "query",
    [
        "unknown=x",
        "algorithm=bfs&algorithm=dfs",
        "algorithm=other",
        "algorithm=",
        "algorithm=%20",
        "root_node_id=invalid",
        "root_node_id=",
        "root_node_id=%20",
        "root_node_id=a&root_node_id=b",
        "max_nodes=0",
        "max_nodes=1001",
        "max_edges=2001",
        "max_edges=-1",
        "max_nodes=1&max_nodes=2",
        "max_nodes=1.0",
        "max_nodes=%201",
        "max_nodes=１",
        "max_edges=true",
        "max_edges=",
    ],
)
def test_invalid_graph_query_is_rejected_before_database(query: str) -> None:
    response = client_with_token().get(
        f"/api/v1/analyses/{uuid.uuid4()}/graph/?{query}"
    )
    assert response.status_code == 400 and response.json()["code"] == "VALIDATION_ERROR"
