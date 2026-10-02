from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import include, path

from apps.tasks.api.views import CsrfView
from common.errors import error_body

urlpatterns = [
    path("api/v1/csrf/", CsrfView.as_view()),
    path("api/v1/", include("apps.tasks.api.urls")),
]


def not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return JsonResponse(
        error_body(
            "RESOURCE_NOT_FOUND",
            "请求的资源不存在。",
            getattr(request, "request_id", ""),
        ),
        status=404,
    )


def server_error(request: HttpRequest) -> HttpResponse:
    return JsonResponse(
        error_body(
            "INTERNAL_ERROR", "请求未能完成。", getattr(request, "request_id", "")
        ),
        status=500,
    )


handler404 = not_found
handler500 = server_error
