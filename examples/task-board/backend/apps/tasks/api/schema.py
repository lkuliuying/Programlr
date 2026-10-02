from typing import Any

from apps.tasks.api.serializers import TaskSerializer
from common.schema import ContractSchema


class TaskSchema(ContractSchema):
    def _map_serializer(
        self, serializer: Any, direction: str, bypass_extensions: bool = False
    ) -> dict[str, Any]:
        # 第三方扩展点没有类型声明，限定例外并显式约束返回结构。
        schema: dict[str, Any] = super()._map_serializer(  # type: ignore[no-untyped-call]
            serializer, direction, bypass_extensions
        )
        if isinstance(serializer, TaskSerializer) and direction == "request":
            # Serializer 的额外字段拒绝和规范化规则不能仅靠 CharField 推导。
            schema["additionalProperties"] = False
            schema["properties"]["title"]["description"] = (
                "去掉首尾空白后长度 1–200；拒绝纯空白、null、非字符串和 NUL。"
            )
        return schema
