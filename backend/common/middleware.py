import uuid
from collections.abc import Callable

from django.conf import settings
from django.core.exceptions import (
    DisallowedHost,
    RequestDataTooBig,
    TooManyFieldsSent,
    TooManyFilesSent,
)
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import CsrfViewMiddleware

from common.errors import error_body


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    return JsonResponse(
        error_body(
            "CSRF_REJECTED",
            "CSRF 校验失败，请刷新页面后重试。",
            getattr(request, "request_id", ""),
        ),
        status=403,
    )


def protected_target(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


class LocalBoundaryMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.csrf = CsrfViewMiddleware(get_response)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            return self.respond(request)
        except (RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent):
            request_id = getattr(request, "request_id", uuid.uuid4().hex)
            code = (
                "ARCHIVE_LIMIT_EXCEEDED"
                if getattr(request, "import_upload", False)
                else "REQUEST_TOO_LARGE"
            )
            response = JsonResponse(
                error_body(
                    code,
                    "上传超过接收限制或缺少有效长度。",
                    request_id,
                ),
                status=413,
            )
            response["X-Request-ID"] = request_id
            response["Cache-Control"] = "no-store"
            return response

    def respond(self, request: HttpRequest) -> HttpResponse:
        response: HttpResponse
        request_id = getattr(request, "request_id", uuid.uuid4().hex)
        setattr(request, "request_id", request_id)
        try:
            host_valid = request.get_host() == settings.APP_AUTHORITY
        except DisallowedHost:
            host_valid = False
        if not host_valid:
            response = JsonResponse(
                error_body("ORIGIN_REJECTED", "请求主机不受信任。", request_id),
                status=403,
            )
        elif request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            if request.headers.get("Origin") != settings.APP_ORIGIN:
                response = JsonResponse(
                    error_body("ORIGIN_REJECTED", "写请求来源不受信任。", request_id),
                    status=403,
                )
            else:
                # DRF 的视图豁免不应绕过匿名写操作；对固定非豁免目标调用标准检查。
                self.csrf.process_request(request)
                rejection = self.csrf.process_view(request, protected_target, (), {})
                response = (
                    rejection if rejection is not None else self.get_response(request)
                )
        else:
            response = self.get_response(request)
        response["X-Request-ID"] = request_id
        response["Cache-Control"] = "no-store"
        return response
