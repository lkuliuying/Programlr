from datetime import UTC, datetime
from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.api.management_serializers import (
    ProjectActivitySerializer,
    ProjectManagementPageSerializer,
    ProjectSummarySerializer,
    SnapshotSearchPageSerializer,
    SnapshotSearchResultSerializer,
)
from apps.projects.api.views import ERRORS, PAGES
from apps.projects.models import Snapshot
from apps.projects.projections import (
    activity,
    preparation_values,
    preparations,
    project_summaries,
)
from common.api import page_response, query_numbers, text_query


def search_text(request: Request) -> dict[str, str]:
    values = text_query(request)
    if "\x00" in values.get("q", ""):
        raise ValidationError({"q": ["搜索文本不能包含 NUL 字符。"]})
    return values


class ProjectManagementView(APIView):
    @extend_schema(
        operation_id="projects_management_list",
        parameters=[
            *PAGES,
            OpenApiParameter("q", {"type": "string", "maxLength": 200}),
            OpenApiParameter("technology", str),
            OpenApiParameter(
                "ordering", str, enum=["recent_import", "created", "name"]
            ),
        ],
        responses={200: ProjectManagementPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = search_text(request)
        for name in ("technology", "ordering"):
            if name in request.query_params:
                value = request.query_params[name]
                if (
                    len(request.query_params.getlist(name)) != 1
                    or len(value) > 100
                    or "\x00" in value
                ):
                    raise ValidationError({name: ["必须为单个有效筛选值。"]})
                filters[name] = value
        ordering = filters.get("ordering", "recent_import")
        if ordering not in {"recent_import", "created", "name"}:
            raise ValidationError({"ordering": ["不支持此排序方式。"]})
        query_numbers(
            request,
            {"page": (1, 2147483647), "page_size": (20, 100)},
            extra=set(filters),
        )
        rows, context = project_summaries(filters.get("q", ""))
        technologies = sorted(
            {tag["name"] for row in rows for tag in row["technologies"]}
        )
        if filters.get("technology"):
            rows = [
                row
                for row in rows
                if any(
                    tag["name"] == filters["technology"] for tag in row["technologies"]
                )
            ]
        if ordering == "name":
            rows.sort(
                key=lambda row: (row["project"].name.casefold(), str(row["project"].pk))
            )
        else:
            rows.sort(
                key=lambda row: (
                    (
                        row["last_imported_at"] or datetime.min.replace(tzinfo=UTC),
                        row["project"].created_at,
                        str(row["project"].pk),
                    )
                    if ordering == "recent_import"
                    else (row["project"].created_at, str(row["project"].pk))
                ),
                reverse=True,
            )
        response = page_response(
            request, rows, ProjectSummarySerializer, filters=filters, context=context
        )
        response.data["technologies"] = technologies
        return response


class ProjectActivityView(APIView):
    @extend_schema(
        operation_id="projects_activity_retrieve",
        responses={200: ProjectActivitySerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        if request.query_params:
            raise ValidationError({"query": ["不支持此查询参数。"]})
        data, context = activity()
        return Response(ProjectActivitySerializer(data, context=context).data)


class SnapshotSearchView(APIView):
    @extend_schema(
        operation_id="snapshots_search",
        parameters=[
            *PAGES,
            OpenApiParameter("q", {"type": "string", "maxLength": 200}),
        ],
        responses={200: SnapshotSearchPageSerializer, **ERRORS},
    )
    def get(self, request: Request) -> Response:
        filters = search_text(request)
        values = query_numbers(
            request,
            {"page": (1, 2147483647), "page_size": (20, 100)},
            extra=set(filters),
        )
        queryset = Snapshot.objects.filter(
            project__deletion_request_id__isnull=True,
            deletion_request_id__isnull=True,
            name__icontains=filters.get("q", ""),
        ).select_related("project")
        start = (values["page"] - 1) * values["page_size"]
        page = list(queryset[start : start + values["page_size"]])
        prepared = preparations(page)
        context = {
            "preparation_fields": {
                snapshot.pk: preparation_values(prepared.get(snapshot.pk))
                for snapshot in page
            }
        }

        # 分页保留数据库切片，嵌套对象只在序列化当前批次时展开。
        class RowsSerializer(SnapshotSearchResultSerializer):
            def to_representation(self, instance: Any) -> dict[str, Any]:
                return super().to_representation(
                    {"snapshot": instance, "project": instance.project}
                )

        return page_response(
            request, queryset, RowsSerializer, filters=filters, context=context
        )
