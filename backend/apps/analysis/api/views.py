import uuid
from collections import defaultdict
from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.api.schema import AnalysisSchema
from apps.analysis.api.serializers import (
    AnalysisInputSerializer,
    AnalysisSerializer,
    DiagnosticPageSerializer,
    DiagnosticSerializer,
    EndpointPageSerializer,
    EndpointSerializer,
    GraphQuerySerializer,
    GraphSerializer,
)
from apps.analysis.associations import frontend_node_id
from apps.analysis.models import Analysis
from apps.analysis.reviews import decisions, graph_decisions
from apps.analysis.services import query_graph, read_frontend, submit_analysis
from apps.analysis.types import GRAPH_VERSION, GraphQuery
from apps.jobs.api.serializers import ErrorSerializer, JobSerializer
from apps.projects.models import Snapshot, SourceFile
from common.api import operation_key, page_response
from common.errors import error_body

ERRORS = {status: ErrorSerializer for status in (400, 403, 404, 409, 413, 415, 503)}
PAGES = [OpenApiParameter("page", int), OpenApiParameter("page_size", int)]


class AnalysesView(APIView):
    schema = AnalysisSchema()

    @extend_schema(
        operation_id="analyses_create",
        request=AnalysisInputSerializer,
        parameters=[
            *[
                OpenApiParameter(name, str, OpenApiParameter.HEADER, required=True)
                for name in ("Idempotency-Key", "X-CSRFToken", "Origin")
            ],
            OpenApiParameter(
                "Location", str, OpenApiParameter.HEADER, response=[200, 202, 503]
            ),
        ],
        responses={200: JobSerializer, 202: JobSerializer, **ERRORS},
    )
    def post(self, request: Request, snapshot_id: uuid.UUID) -> Response:
        if request.content_type != "application/json":
            raise UnsupportedMediaType(request.content_type)
        if not request.body.strip():
            raise ValidationError({"body": ["必须提供 JSON 对象。"]})
        payload = AnalysisInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        key = operation_key(request)
        snapshot = get_object_or_404(Snapshot, pk=snapshot_id)
        root = payload.validated_data["root_urlconf"]
        get_object_or_404(SourceFile, snapshot=snapshot, file_path=root)
        job, created, published = submit_analysis(snapshot, key, root)
        location = f"/api/v1/jobs/{job.pk}/"
        if not published:
            return Response(
                error_body(
                    "SERVICE_UNAVAILABLE",
                    "分析投递未确认，记录已保存，请查询任务状态。",
                    getattr(request, "request_id"),
                    {"job_url": location},
                ),
                status=503,
                headers={"Location": location},
            )
        return Response(
            JobSerializer(job).data,
            status=202 if created else 200,
            headers={"Location": location},
        )


class AnalysisDetailView(APIView):
    @extend_schema(
        operation_id="analyses_retrieve", responses={200: AnalysisSerializer, **ERRORS}
    )
    def get(self, request: Request, analysis_id: uuid.UUID) -> Response:
        return Response(
            AnalysisSerializer(get_object_or_404(Analysis, pk=analysis_id)).data
        )


class EndpointsView(APIView):
    @extend_schema(
        operation_id="analysis_endpoints_list",
        parameters=PAGES,
        responses={200: EndpointPageSerializer, **ERRORS},
    )
    def get(self, request: Request, analysis_id: uuid.UUID) -> Response:
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        frontend = read_frontend(analysis)
        links: dict[int, list[dict[str, Any]]] = defaultdict(list)
        if frontend is not None:
            requests = {item["id"]: item for item in frontend["parser"]["requests"]}
            for match in frontend["matches"]:
                item = requests[match["request_id"]]
                for index in match["endpoint_indices"]:
                    links[index].append(
                        {
                            "request_id": frontend_node_id(analysis.pk, item["id"]),
                            "method": item["method"],
                            "path": item["path"],
                            "status": match["status"],
                            "reason": match["reason"],
                            "source_ref": item["source_ref"],
                        }
                    )
        data = [
            {
                **endpoint,
                "index": index,
                "frontend_available": frontend is not None,
                "frontend_links": links[index],
            }
            for index, endpoint in enumerate(analysis.endpoints)
        ]
        pairs = [
            (link["request_id"], str(uuid.uuid5(analysis.pk, f"endpoint:{index}")))
            for index, items in links.items()
            for link in items
            if link["status"] == "candidate"
        ]
        reviews = {
            (item["request_id"], item["target_id"]): item
            for item in decisions(analysis, pairs)
        }
        for index, items in links.items():
            for link in items:
                link["relation_review"] = reviews.get(
                    (
                        link["request_id"],
                        str(uuid.uuid5(analysis.pk, f"endpoint:{index}")),
                    )
                )
        return page_response(request, data, EndpointSerializer)


class DiagnosticsView(APIView):
    @extend_schema(
        operation_id="analysis_diagnostics_list",
        parameters=PAGES,
        responses={200: DiagnosticPageSerializer, **ERRORS},
    )
    def get(self, request: Request, analysis_id: uuid.UUID) -> Response:
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        return page_response(request, analysis.diagnostics, DiagnosticSerializer)


class GraphView(APIView):
    @extend_schema(
        operation_id="analysis_graph_retrieve",
        parameters=[GraphQuerySerializer],
        responses={200: GraphSerializer, **ERRORS},
    )
    def get(self, request: Request, analysis_id: uuid.UUID) -> Response:
        payload = GraphQuerySerializer(data=request.query_params)
        payload.is_valid(raise_exception=True)
        values = payload.validated_data
        root = values.get("root_node_id")
        query = GraphQuery(
            root_node_id=str(root) if root is not None else None,
            algorithm=values["algorithm"],
            max_nodes=values["max_nodes"],
            max_edges=values["max_edges"],
            endpoint_index=values.get("endpoint_index"),
        )
        analysis = get_object_or_404(Analysis, pk=analysis_id)
        selection = query_graph(analysis, query)
        return Response(
            GraphSerializer(
                {
                    "analysis_id": analysis.pk,
                    "snapshot_id": analysis.snapshot_id,
                    "rule_version": analysis.rule_version,
                    "graph_version": GRAPH_VERSION,
                    "root_node_id": query.root_node_id,
                    "endpoint_index": query.endpoint_index,
                    "algorithm": query.algorithm,
                    "coverage": analysis.coverage,
                    "diagnostics_url": f"/api/v1/analyses/{analysis.pk}/diagnostics/",
                    **selection,
                    "relation_reviews": graph_decisions(
                        analysis,
                        {
                            "nodes": selection["nodes"],
                            "edges": selection["edges"],
                        },
                    ),
                }
            ).data
        )
