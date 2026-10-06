from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import include, path

from apps.jobs.api.notification_views import (
    NotificationDetailView,
    NotificationReadStateView,
    NotificationsView,
)
from apps.jobs.api.views import (
    CsrfView,
    JobDetailView,
    JobRetriesView,
    JobsView,
    SystemCheckDetailView,
    SystemChecksView,
)
from common.errors import error_body

urlpatterns = [
    path("api/v1/", include("apps.jobs.api.operation_urls")),
    path("api/v1/", include("apps.labs.api.urls")),
    path("api/v1/", include("apps.explanations.api.urls")),
    path("api/v1/", include("apps.learning.api.urls")),
    path("api/v1/", include("apps.analysis.api.urls")),
    path("api/v1/", include("apps.projects.api.urls")),
    path("api/v1/csrf/", CsrfView.as_view()),
    path("api/v1/jobs/", JobsView.as_view()),
    path("api/v1/notifications/", NotificationsView.as_view()),
    path("api/v1/notifications/<uuid:job_id>/", NotificationDetailView.as_view()),
    path("api/v1/notification-read-state/", NotificationReadStateView.as_view()),
    path("api/v1/jobs/<uuid:job_id>/", JobDetailView.as_view()),
    path("api/v1/jobs/<uuid:job_id>/retries/", JobRetriesView.as_view()),
    path("api/v1/system-checks/", SystemChecksView.as_view()),
    path("api/v1/system-checks/<uuid:check_id>/", SystemCheckDetailView.as_view()),
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
