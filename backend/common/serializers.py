from typing import Any

from rest_framework import serializers


class StrictInputSerializer(serializers.Serializer[dict[str, Any]]):
    """拒绝未知字段及隐式类型转换，保持请求摘要与用户输入一致。"""

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or set(data) - self.fields.keys():
            raise serializers.ValidationError({"body": ["JSON 字段不符合接口约定。"]})
        for name, field in self.fields.items():
            if name not in data:
                continue
            value = data[name]
            valid = True
            if isinstance(field, serializers.BooleanField):
                valid = type(value) is bool
            elif isinstance(field, serializers.IntegerField):
                valid = type(value) is int
            elif isinstance(field, (serializers.CharField, serializers.UUIDField)):
                valid = isinstance(value, str)
            if not valid:
                raise serializers.ValidationError({name: ["字段类型无效。"]})
        result: dict[str, Any] = super().to_internal_value(data)
        return result
