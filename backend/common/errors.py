import logging
import uuid
from typing import Any

from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent
from django.db import DatabaseError
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def error_body(
    code: str, message: str, request_id: str, details: Any = None
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
        "request_id": request_id,
    }


class Conflict(APIException):
    status_code = 409
    default_detail = "同一操作标识已用于不同请求。"


class ApiProblem(APIException):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status
        self.machine_code = code
        self.public_details = details or {}
        super().__init__(message)


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    request_id = getattr(context.get("request"), "request_id", uuid.uuid4().hex)
    response = exception_handler(exc, context)
    if isinstance(exc, ApiProblem):
        return Response(
            error_body(
                exc.machine_code, str(exc.detail), request_id, exc.public_details
            ),
            status=exc.status_code,
        )
    if isinstance(exc, RequestDataTooBig):
        status, code, message = 413, "REQUEST_TOO_LARGE", "请求体超过基础接口限制。"
    elif isinstance(exc, TooManyFieldsSent):
        status, code, message = 400, "VALIDATION_ERROR", "请求字段数量超过接口限制。"
    elif isinstance(exc, DatabaseError):
        status, code, message = (
            503,
            "SERVICE_UNAVAILABLE",
            "数据库暂不可用，请稍后查询。",
        )
    elif isinstance(exc, Conflict):
        status, code, message = 409, "IDEMPOTENCY_CONFLICT", str(exc.detail)
    elif response is not None:
        status = response.status_code
        code, message = {
            400: ("VALIDATION_ERROR", "请求参数不符合要求。"),
            403: ("CSRF_REJECTED", "请求保护校验失败。"),
            404: ("RESOURCE_NOT_FOUND", "请求的资源不存在。"),
            405: ("METHOD_NOT_ALLOWED", "此资源不支持该请求方法。"),
            406: ("NOT_ACCEPTABLE", "只支持 JSON 响应。"),
            415: ("UNSUPPORTED_MEDIA_TYPE", "此接口不支持该请求内容类型。"),
        }.get(status, ("INTERNAL_ERROR", "请求未能完成。"))
    else:
        status, code, message = 500, "INTERNAL_ERROR", "服务暂时无法完成请求。"
        logger.error("request_id=%s exception_type=%s", request_id, type(exc).__name__)
    details = {"fields": exc.detail} if isinstance(exc, ValidationError) else {}
    return Response(error_body(code, message, request_id, details), status=status)
