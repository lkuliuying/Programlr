"""使用框架已有类型验证插件，不创建数据库模型或业务接口。"""

from django.http import HttpRequest, HttpResponse
from rest_framework.fields import IntegerField


def request_method(request: HttpRequest) -> str | None:
    return request.method


def render_count(value: object) -> HttpResponse:
    field: IntegerField = IntegerField(min_value=0, max_value=10)
    count: int = field.run_validation(value)
    return HttpResponse(str(count))
