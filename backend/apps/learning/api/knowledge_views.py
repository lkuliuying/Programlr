import uuid
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.models import Analysis, SourceScan
from apps.learning.api.knowledge_serializers import (
    KnowledgeHitPageSerializer,
    KnowledgeHitSerializer,
    MatchedKnowledgeCardSerializer,
    SnapshotKnowledgePageSerializer,
)
from apps.learning.api.views import ERRORS, PAGES
from apps.learning.knowledge import group_cards, read_scan, selected_hits
from apps.projects.models import Snapshot
from common.api import page_response
from common.resource_state import require_snapshot_available

FILTERS = [
    OpenApiParameter(name, str)
    for name in ("scan_id", "analysis_id", "endpoint_index", "file_path", "concept_key")
]


def selection(
    request: Request, snapshot_id: uuid.UUID
) -> tuple[SourceScan, dict[str, str], dict[str, Any]]:
    names = {"scan_id", "analysis_id", "endpoint_index", "file_path", "concept_key"}
    if set(request.query_params) - names - {"page", "page_size"} or any(
        len(request.query_params.getlist(key)) != 1 for key in request.query_params
    ):
        raise ValidationError({"query": ["不支持未知或重复查询参数。"]})
    filters = {
        name: request.query_params[name]
        for name in names
        if name in request.query_params
    }
    if any(not value for value in filters.values()):
        raise ValidationError({"query": ["筛选参数不能为空。"]})
    snapshot = get_object_or_404(Snapshot, pk=snapshot_id)
    require_snapshot_available(snapshot)
    for name in ("analysis_id", "scan_id"):
        if name in filters:
            try:
                filters[name] = str(uuid.UUID(filters[name]))
            except ValueError:
                raise ValidationError({name: ["必须为 UUID。"]}) from None
    if ("analysis_id" in filters) != ("endpoint_index" in filters):
        raise ValidationError({"query": ["接口筛选必须同时指定分析和接口序号。"]})
    analysis = None
    index = None
    if "analysis_id" in filters:
        raw = filters["endpoint_index"]
        if len(raw) > 5 or not raw.isascii() or not raw.isdecimal():
            raise ValidationError({"endpoint_index": ["必须为非负整数。"]})
        index = int(raw)
        analysis = get_object_or_404(
            Analysis, pk=filters["analysis_id"], snapshot=snapshot
        )
        if index >= len(analysis.endpoints):
            raise ValidationError({"endpoint_index": ["接口序号越界。"]})
        if analysis.source_scan_id:
            bound = str(analysis.source_scan_id)
            if "scan_id" in filters and filters["scan_id"] != bound:
                raise ValidationError({"scan_id": ["接口分析与源码扫描版本不一致。"]})
            filters["scan_id"] = bound
    if (
        "file_path" in filters
        and not snapshot.files.filter(file_path=filters["file_path"]).exists()
    ):
        raise ValidationError({"file_path": ["文件不属于当前快照。"]})
    scan = read_scan(snapshot, filters.get("scan_id"))
    return (
        scan,
        filters,
        {
            "analysis": analysis,
            "endpoint_index": index,
            "file_path": filters.get("file_path"),
            "concept_key": filters.get("concept_key"),
        },
    )


class SnapshotKnowledgeCardsView(APIView):
    @extend_schema(
        operation_id="snapshot_knowledge_cards_list",
        parameters=[*PAGES, *FILTERS],
        responses={200: SnapshotKnowledgePageSerializer, **ERRORS},
    )
    def get(self, request: Request, snapshot_id: uuid.UUID) -> Response:
        scan, filters, values = selection(request, snapshot_id)
        response = page_response(
            request,
            group_cards(selected_hits(scan, **values)),
            MatchedKnowledgeCardSerializer,
            filters=filters,
        )
        response.data.update(
            {
                "scan_id": str(scan.pk),
                "rule_version": scan.result["knowledge"]["rule_version"],
                "coverage": scan.result["knowledge"]["coverage"],
                "diagnostics": scan.result["knowledge"]["diagnostics"],
            }
        )
        return response


class SnapshotKnowledgeHitsView(APIView):
    @extend_schema(
        operation_id="snapshot_knowledge_hits_list",
        parameters=[*PAGES, *FILTERS],
        responses={200: KnowledgeHitPageSerializer, **ERRORS},
    )
    def get(self, request: Request, snapshot_id: uuid.UUID) -> Response:
        scan, filters, values = selection(request, snapshot_id)
        response = page_response(
            request,
            selected_hits(scan, **values),
            KnowledgeHitSerializer,
            filters=filters,
        )
        response.data.update(
            {
                "scan_id": str(scan.pk),
                "rule_version": scan.result["knowledge"]["rule_version"],
            }
        )
        return response
