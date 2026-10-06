from copy import deepcopy
from typing import Any

from drf_spectacular.openapi import AutoSchema

from common.serializers import StrictInputSerializer


class ContractSchema(AutoSchema):
    """补齐由公共边界保证的响应与参数约束，不生成未来业务接口。"""

    def _map_serializer(
        self, serializer: Any, direction: str, bypass_extensions: bool = False
    ) -> dict[str, Any]:
        schema: dict[str, Any] = super()._map_serializer(
            serializer, direction, bypass_extensions
        )  # type: ignore[no-untyped-call]
        if direction == "request" and isinstance(serializer, StrictInputSerializer):
            schema["additionalProperties"] = False
        return schema

    def get_operation(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        operation = super().get_operation(*args, **kwargs)
        if operation is None:
            return None
        responses = operation["responses"]
        if "403" not in responses:
            error_response = next(
                (
                    value
                    for status, value in responses.items()
                    if status.startswith("4") and "content" in value
                ),
                None,
            )
            if error_response is None:
                raise ValueError("业务接口必须声明至少一种结构化错误响应。")
            responses["403"] = {
                "description": "HOST_REJECTED、ORIGIN_REJECTED 或 CSRF_REJECTED：本地访问边界拒绝。",
                "content": deepcopy(error_response["content"]),
            }
        if operation.get("operationId") in {
            "system_checks_create",
            "lab_runs_create",
            "system_lab_runs_create",
            "project_snapshot_comparisons_create",
            "relation_reviews_create",
            "exercise_attempts_create",
            "attempt_reviews_create",
            "curriculum_card_progress_update",
            "notifications_mark_read",
            "notification_read_state_update",
        }:
            operation["deprecated"] = True
            operation["description"] = (
                "功能已退役；本入口只返回 FEATURE_RETIRED，不创建任务或修改业务数据。"
            )
            responses.clear()
            responses["410"] = {
                "description": "FEATURE_RETIRED：功能已退役；历史结果保留只读。",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                },
            }
            responses["403"] = {
                "description": "HOST_REJECTED、ORIGIN_REJECTED 或 CSRF_REJECTED：本地访问边界拒绝。",
                "content": deepcopy(responses["410"]["content"]),
            }
        for status, description in (
            ("406", "NOT_ACCEPTABLE：仅提供 application/json 响应。"),
            ("500", "INTERNAL_ERROR：未预期失败，正文不包含内部诊断。"),
        ):
            responses[status] = {
                "description": description,
                "content": deepcopy(responses["403"]["content"]),
            }
        for response in responses.values():
            response.setdefault("headers", {}).update(
                {
                    "X-Request-ID": {
                        "required": True,
                        "description": "服务端生成；错误正文的 request_id 与此值一致。",
                        "schema": {"type": "string"},
                    },
                    "Cache-Control": {
                        "required": True,
                        "schema": {"type": "string", "enum": ["no-store"]},
                    },
                }
            )
        for parameter in operation.get("parameters", []):
            if parameter["in"] == "query" and parameter["name"] in {
                "page",
                "page_size",
            }:
                is_page = parameter["name"] == "page"
                parameter["schema"].update(
                    minimum=1,
                    maximum=2147483647 if is_page else 100,
                    default=1 if is_page else 20,
                )
                parameter["description"] = (
                    "只接受单个 ASCII 十进制正整数；重复参数拒绝。"
                )
            if parameter["name"] == "Idempotency-Key":
                parameter["schema"]["format"] = "uuid"
        return operation


class RequiredPatchSchema(ContractSchema):
    """状态写入接受完整指定字段，不使用可选字段补丁语义。"""

    def _map_serializer(
        self, serializer: Any, direction: str, bypass_extensions: bool = False
    ) -> dict[str, Any]:
        schema = super()._map_serializer(serializer, direction, bypass_extensions)
        if direction == "request" and isinstance(serializer, StrictInputSerializer):
            schema["required"] = list(serializer.fields)
        return schema
