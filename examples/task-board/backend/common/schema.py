from copy import deepcopy
from typing import Any

from drf_spectacular.openapi import AutoSchema


class ContractSchema(AutoSchema):
    """补齐由公共边界保证的响应与参数约束，不生成未来业务接口。"""

    def get_operation(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        operation = super().get_operation(*args, **kwargs)
        if operation is None:
            return None
        responses = operation["responses"]
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
