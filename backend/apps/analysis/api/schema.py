from typing import Any

from apps.analysis.api.serializers import AnalysisInputSerializer
from common.schema import ContractSchema


class AnalysisSchema(ContractSchema):
    def _map_serializer(
        self, serializer: Any, direction: str, bypass_extensions: bool = False
    ) -> dict[str, Any]:
        schema: dict[str, Any] = super()._map_serializer(
            serializer, direction, bypass_extensions
        )
        if direction == "request" and isinstance(serializer, AnalysisInputSerializer):
            schema["additionalProperties"] = False
        return schema
