import uuid

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.api.notification_serializers import (
    NotificationPageSerializer,
    NotificationReadInputSerializer,
    NotificationReadStateInputSerializer,
    NotificationReadStateSerializer,
    NotificationSerializer,
)
from apps.jobs.api.serializers import ErrorSerializer
from apps.jobs.notifications import (
    notification_jobs,
    read_through,
    unread_count,
)
from common.api import page_response
from common.retirement import retired_feature
from common.schema import RequiredPatchSchema

ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 410, 413, 415, 503)}
HEADERS = [
    OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
    for name in ("Origin", "X-CSRFToken")
]


class NotificationsView(APIView):
    @extend_schema(
        operation_id="notifications_list",
        parameters=[OpenApiParameter("page", int), OpenApiParameter("page_size", int)],
        responses={200: NotificationPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        watermark = read_through()
        now = timezone.now()
        response = page_response(
            request,
            notification_jobs(now),
            NotificationSerializer,
            context={"read_through": watermark},
        )
        response.data.update(
            NotificationReadStateSerializer(
                {
                    "read_through": watermark,
                    "unread_count": unread_count(now, watermark),
                    "as_of": now,
                }
            ).data
        )
        return response


class NotificationDetailView(APIView):
    schema = RequiredPatchSchema()

    @extend_schema(
        operation_id="notifications_mark_read",
        deprecated=True,
        parameters=HEADERS,
        request=NotificationReadInputSerializer,
        responses=ERRORS,
    )
    def patch(self, request: Request, job_id: uuid.UUID) -> Response:
        retired_feature("notification")


class NotificationReadStateView(APIView):
    schema = RequiredPatchSchema()

    @extend_schema(
        operation_id="notification_read_state_update",
        deprecated=True,
        parameters=HEADERS,
        request=NotificationReadStateInputSerializer,
        responses=ERRORS,
    )
    def patch(self, request: Request) -> Response:
        retired_feature("notification")
