import json
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.db import DatabaseError
from drf_spectacular.generators import SchemaGenerator
from jsonschema import (  # type: ignore[import-untyped]
    Draft202012Validator,
    FormatChecker,
)
from rest_framework.test import APIClient

from apps.tasks.api.views import TaskListCreateView

HOST = "127.0.0.1:5174"
LIST_PATH = "/api/v1/tasks/"
POST_PATH = "/api/v1/tasks/"
LIST_VIEW = TaskListCreateView


def test_contract_matches_example_only() -> None:
    # 第三方生成入口尚无类型声明，下面逐项断言其实际结构。
    schema = SchemaGenerator().get_schema(public=True)  # type: ignore[no-untyped-call]
    assert set(schema["paths"]) == {"/api/v1/csrf/", "/api/v1/tasks/"}
    create = schema["paths"]["/api/v1/tasks/"]["post"]
    assert create["operationId"] == "task_board_tasks_create"
    assert create["requestBody"]["required"]
    assert {"200", "201", "400", "403", "409", "413", "415", "503"} <= set(
        create["responses"]
    )
    body = schema["components"]["schemas"]["TaskRequest"]
    assert body["required"] == ["title"]
    assert body["additionalProperties"] is False
    assert body["properties"]["title"]["maxLength"] == 200
    assert set(schema["components"]["schemas"]["Task"]["properties"]) == {
        "id",
        "title",
        "created_at",
    }


def contract_schema() -> dict[str, Any]:
    output = StringIO()
    call_command(
        "spectacular",
        format="openapi-json",
        stdout=output,
        validate=True,
        fail_on_warn=True,
    )
    schema: dict[str, Any] = json.loads(output.getvalue())
    return schema


def json_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [json_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {
        key: json_schema(item) for key, item in value.items() if key != "nullable"
    }
    return {"anyOf": [result, {"type": "null"}]} if value.get("nullable") else result


def assert_response(
    response: Any, schema: dict[str, Any], path: str | None = None, method: str = "get"
) -> None:
    if path is None:
        body_schema = {"$ref": "#/components/schemas/Error"}
    else:
        declaration = schema["paths"][path][method]["responses"][
            str(response.status_code)
        ]
        body_schema = declaration["content"]["application/json"]["schema"]
    validator = Draft202012Validator(
        json_schema({**body_schema, "components": schema["components"]}),
        format_checker=FormatChecker(),
    )
    validator.validate(response.json())
    assert response["Cache-Control"] == "no-store"
    assert response["X-Request-ID"]
    if response.status_code >= 400:
        assert response.json()["request_id"] == response["X-Request-ID"]
        assert set(response.json()) == {"code", "message", "details", "request_id"}
        assert "internal-diagnostic-example" not in response.content.decode()


def test_public_contract_metadata() -> None:
    schema = contract_schema()
    ids = []
    for methods in schema["paths"].values():
        for operation in methods.values():
            ids.append(operation["operationId"])
            assert {"406", "500"} <= operation["responses"].keys()
            for response in operation["responses"].values():
                assert response["headers"]["X-Request-ID"]["required"]
                assert response["headers"]["Cache-Control"]["schema"]["enum"] == [
                    "no-store"
                ]
    assert len(ids) == len(set(ids))
    parameters = {p["name"]: p for p in schema["paths"][LIST_PATH]["get"]["parameters"]}
    assert parameters["page"]["schema"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 2147483647,
        "default": 1,
    }
    assert parameters["page_size"]["schema"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "default": 20,
    }
    creation = schema["paths"][POST_PATH]["post"]
    key = next(p for p in creation["parameters"] if p["name"] == "Idempotency-Key")
    assert key["required"] and key["schema"]["format"] == "uuid"


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "VALIDATION_ERROR"),
        (403, "ORIGIN_REJECTED"),
        (404, "RESOURCE_NOT_FOUND"),
        (405, "METHOD_NOT_ALLOWED"),
        (406, "NOT_ACCEPTABLE"),
        (413, "REQUEST_TOO_LARGE"),
        (500, "INTERNAL_ERROR"),
        (503, "SERVICE_UNAVAILABLE"),
    ],
)
def test_error_boundary(
    status: int,
    code: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    schema = contract_schema()
    client = APIClient(enforce_csrf_checks=True)
    token_response = client.get("/api/v1/csrf/", HTTP_HOST=HOST)
    assert_response(token_response, schema, "/api/v1/csrf/")
    client.credentials(
        HTTP_HOST=HOST,
        HTTP_ORIGIN=f"http://{HOST}",
        HTTP_X_CSRFTOKEN=token_response.json()["csrf_token"],
    )
    schema_path: str | None = LIST_PATH
    method = "get"
    if status in (500, 503):

        def fail(*args: Any, **kwargs: Any) -> None:
            raise (DatabaseError if status == 503 else RuntimeError)(
                "internal-diagnostic-example"
            )

        monkeypatch.setattr(LIST_VIEW, "get", fail)
        response = client.get(LIST_PATH)
    elif status == 400:
        response = client.get(LIST_PATH + "?page_size=101")
    elif status == 403:
        client.credentials(HTTP_HOST="untrusted.invalid")
        response = client.get(LIST_PATH)
    elif status == 404:
        response = client.get("/api/v1/not-implemented/")
        schema_path = None
    elif status == 405:
        response = client.put(LIST_PATH, {}, format="json")
        schema_path = None
    elif status == 406:
        response = client.get(LIST_PATH, HTTP_ACCEPT="text/html")
    else:
        response = client.post(POST_PATH, "x" * 5000, content_type="application/json")
        schema_path, method = POST_PATH, "post"
    assert response.status_code == status
    assert response.json()["code"] == code
    assert_response(response, schema, schema_path, method)
    assert "internal-diagnostic-example" not in caplog.text


def test_csrf_rejection_uses_error_contract() -> None:
    response = APIClient(enforce_csrf_checks=True).post(
        POST_PATH, {}, format="json", HTTP_HOST=HOST, HTTP_ORIGIN=f"http://{HOST}"
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_REJECTED"
    assert_response(response, contract_schema(), POST_PATH, "post")
