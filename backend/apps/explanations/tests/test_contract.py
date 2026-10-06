from typing import Any

import pytest
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient

from apps.jobs.tests.test_contract import contract_schema


def test_m4_contract_operations_and_server_only_answers() -> None:
    schema = contract_schema()
    operations = [
        operation["operationId"]
        for methods in schema["paths"].values()
        for method, operation in methods.items()
        if method in {"get", "post", "patch", "delete"}
    ]
    assert len(operations) == len(set(operations)) == 83
    assert {
        "labs_list",
        "labs_retrieve",
        "lab_runs_create",
        "lab_runs_list",
        "lab_runs_retrieve",
        "relation_reviews_list",
        "relation_reviews_create",
        "knowledge_curricula_list",
        "knowledge_curricula_retrieve",
        "learning_paths_retrieve",
        "attempt_reviews_list",
        "attempt_reviews_create",
        "system_labs_list",
        "system_labs_retrieve",
        "system_lab_runs_create",
        "system_lab_runs_list",
        "system_lab_runs_retrieve",
        "snapshots_rename",
        "notifications_list",
        "notifications_mark_read",
        "notification_read_state_update",
        "curriculum_progress_retrieve",
        "curriculum_card_progress_update",
        "source_scans_create",
        "source_scans_retrieve",
        "snapshot_knowledge_cards_list",
        "snapshot_knowledge_hits_list",
        "endpoint_relations_retrieve",
        "folder_imports_create",
        "folder_imports_retry",
        "projects_delete",
        "snapshots_delete",
        "operation_logs_list",
        "operation_logs_retrieve",
    } <= set(operations)
    for path, method in (
        ("/api/v1/exercise-attempts/", "post"),
        ("/api/v1/attempt-reviews/", "post"),
        (
            "/api/v1/knowledge-curricula/{curriculum_id}/progress/{card_id}/",
            "patch",
        ),
    ):
        operation = schema["paths"][path][method]
        assert operation["deprecated"] and "410" in operation["responses"]
        assert not any(status.startswith("2") for status in operation["responses"])
    types = schema["components"]["schemas"]
    assert not {"answer", "explanation", "source_refs"} & set(
        types["Exercise"]["properties"]
    )
    assert types["Explanation"]["properties"]["usage"]["nullable"]
    for name in (
        "PreviewInputRequest",
        "ConsentInputRequest",
        "ExplanationInputRequest",
        "AttemptInputRequest",
    ):
        assert types[name]["additionalProperties"] is False
    assert types["KindEnum"]["enum"] == [
        "source_fact",
        "static_inference",
        "framework_rule",
    ]
    assert types["StatusEnum"]["enum"] == ["queued", "running", "succeeded", "failed"]


@pytest.mark.parametrize(
    ("path", "body"),
    [("context-previews/", {}), ("explanations/", {}), ("exercise-attempts/", {})],
)
def test_m4_posts_do_not_bypass_origin_or_csrf(path: str, body: dict[str, Any]) -> None:
    # 此处只验证无数据库的传输边界，持久审计的拒绝记录另由隔离数据库测试覆盖。
    middleware = [
        item
        for item in settings.MIDDLEWARE
        if item != "apps.jobs.audit_middleware.OperationLogMiddleware"
    ]
    with override_settings(MIDDLEWARE=middleware):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            "/api/v1/" + path,
            body,
            format="json",
            HTTP_HOST="127.0.0.1:5173",
            HTTP_ORIGIN="http://127.0.0.1:9999",
        )
        assert response.status_code == 403
        response = client.post(
            "/api/v1/" + path,
            body,
            format="json",
            HTTP_HOST="127.0.0.1:5173",
            HTTP_ORIGIN="http://127.0.0.1:5173",
        )
        assert response.status_code == 403


def test_history_parameter_limit_is_explicit() -> None:
    response = APIClient().get(
        "/api/v1/explanations/?a=1&b=2&c=3&d=4&e=5&f=6", HTTP_HOST="127.0.0.1:5173"
    )
    assert response.status_code == 400 and response.json()["code"] == "VALIDATION_ERROR"
