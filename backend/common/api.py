import uuid
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Model, QuerySet
from rest_framework import serializers
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from common.errors import ApiProblem
from common.serializers import StrictInputSerializer


def operation_key(request: Request) -> uuid.UUID:
    try:
        return uuid.UUID(request.headers.get("Idempotency-Key", ""))
    except ValueError:
        raise ValidationError(
            {"idempotency_key": ["必须提供 UUID 形式的操作标识。"]}
        ) from None


def query_numbers(
    request: Request,
    rules: dict[str, tuple[int, int]],
    *,
    extra: set[str] | None = None,
) -> dict[str, int]:
    if set(request.query_params) - rules.keys() - (extra or set()):
        raise ValidationError({"query": ["不支持此查询参数。"]})
    result = {}
    for name, (default, maximum) in rules.items():
        raw = request.query_params.get(name, str(default))
        if (
            len(raw) > 10
            or len(request.query_params.getlist(name)) > 1
            or not raw.isascii()
            or not raw.isdecimal()
            or not 1 <= int(raw) <= maximum
        ):
            raise ValidationError({name: ["必须为有效范围内的正整数。"]})
        result[name] = int(raw)
    return result


def page_response(
    request: Request,
    queryset: QuerySet[Model] | list[dict[str, Any]],
    serializer: type[serializers.BaseSerializer[Any]],
    *,
    filters: dict[str, str] | None = None,
    context: dict[str, Any] | None = None,
) -> Response:
    values = query_numbers(
        request,
        {"page": (1, 2147483647), "page_size": (20, 100)},
        extra=set(filters or {}),
    )
    paginator = Paginator(queryset, values["page_size"])
    try:
        page = paginator.page(values["page"])
    except EmptyPage:
        raise ApiProblem(404, "PAGE_NOT_FOUND", "请求的页码不存在。") from None

    def link(number: int) -> str:
        return (
            request.path
            + "?"
            + urlencode(
                {"page": number, "page_size": values["page_size"], **(filters or {})}
            )
        )

    return Response(
        {
            "count": paginator.count,
            "next": link(page.next_page_number()) if page.has_next() else None,
            "previous": link(page.previous_page_number())
            if page.has_previous()
            else None,
            "results": serializer(
                list(page.object_list), many=True, context=context or {}
            ).data,
        }
    )


def resource_filters(request: Request, names: tuple[str, ...]) -> dict[str, str]:
    values = {}
    for name in names:
        if name not in request.query_params:
            continue
        raw = request.query_params[name]
        if len(request.query_params.getlist(name)) != 1:
            raise ValidationError({name: ["筛选参数不能重复。"]})
        try:
            if name == "endpoint_index":
                if (
                    not raw.isascii()
                    or not raw.isdecimal()
                    or len(raw) > 4
                    or str(int(raw)) != raw
                ):
                    raise ValueError
            elif str(uuid.UUID(raw)) != raw:
                raise ValueError
        except ValueError:
            raise ValidationError({name: ["筛选参数格式无效。"]}) from None
        values[name] = raw
    return values


def json_input(
    request: Request, serializer: type[StrictInputSerializer]
) -> StrictInputSerializer:
    if request.query_params:
        raise ValidationError({"query": ["不支持此查询参数。"]})
    if request.content_type != "application/json":
        raise UnsupportedMediaType(request.content_type)
    if not request.body.strip():
        raise ValidationError({"body": ["必须提供 JSON 对象。"]})
    parsed = serializer(data=request.data)
    parsed.is_valid(raise_exception=True)
    return parsed
