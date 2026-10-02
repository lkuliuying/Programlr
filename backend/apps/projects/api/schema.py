from typing import Any

from apps.projects.api.serializers import (
    ImportInputSerializer,
    ProjectInputSerializer,
    SnapshotNameInputSerializer,
)
from common.schema import ContractSchema


class ProjectSchema(ContractSchema):
    def _map_serializer(
        self, serializer: Any, direction: str, bypass_extensions: bool = False
    ) -> dict[str, Any]:
        # 生成器无法推导额外字段拒绝，补充实际输入边界。
        schema: dict[str, Any] = super()._map_serializer(
            serializer, direction, bypass_extensions
        )
        if direction == "request" and isinstance(
            serializer, (ProjectInputSerializer, ImportInputSerializer)
        ):
            schema["additionalProperties"] = False
        if direction == "request" and isinstance(
            serializer, SnapshotNameInputSerializer
        ):
            # PATCH 只接受完整名称，不使用通用的可选字段补丁规则。
            schema["required"] = ["name"]
        return schema
