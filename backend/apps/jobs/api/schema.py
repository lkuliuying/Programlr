from typing import Any

from common.schema import ContractSchema


class SystemCheckSchema(ContractSchema):
    def get_operation(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        operation = super().get_operation(*args, **kwargs)
        # 空对象也必须显式提交；默认生成器只根据必填字段判断正文是否必填。
        if operation is not None and "requestBody" in operation:
            operation["requestBody"]["required"] = True
        return operation
