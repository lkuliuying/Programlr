import hashlib
import json
import logging
import uuid
from typing import Any, cast

from django.db import DatabaseError, transaction

from apps.analysis.associations import associate, extend_graph
from apps.analysis.frontend_runner import run_frontend_parser, validate_frontend
from apps.analysis.frontend_types import ASSOCIATION_RULE_VERSION, FrontendAnalysis
from apps.analysis.graph import build_graph, select_graph, validate_graph
from apps.analysis.models import Analysis, AnalysisGraph, AnalysisRequest
from apps.analysis.runner import run_parser
from apps.analysis.types import (
    GRAPH_VERSION,
    AnalysisFailed,
    GraphData,
    GraphQuery,
    GraphSelection,
    Source,
)
from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.projects.exceptions import ImportRejected
from apps.projects.models import Snapshot, SourceFile
from apps.projects.services import source_content
from common.errors import ApiProblem

logger = logging.getLogger(__name__)


def submit_analysis(
    snapshot: Snapshot,
    key: uuid.UUID,
    root_urlconf: str,
    *,
    previous: Job | None = None,
) -> tuple[Job, bool, bool]:
    digest = hashlib.sha256(
        json.dumps({"root_urlconf": root_urlconf}, sort_keys=True).encode()
    ).hexdigest()
    with transaction.atomic():
        if previous is not None:
            job, created = jobs.create_retry_job(previous, key, digest)
        else:
            job, created = jobs.create_analysis_job(snapshot.pk, key, digest)
        if created:
            AnalysisRequest.objects.create(
                job=job, snapshot=snapshot, root_urlconf=root_urlconf
            )
    published = jobs.dispatch_analysis(job) if created else True
    job.refresh_from_db()
    return job, created, published


def execute_analysis(job_id: str) -> None:
    try:
        claim = jobs.claim_analysis(job_id)
    except DatabaseError:
        raise RuntimeError("分析领取需等待期限核对。") from None
    if claim is None:
        return
    try:
        record = AnalysisRequest.objects.select_related("snapshot").get(job_id=job_id)
        files = SourceFile.objects.filter(snapshot=record.snapshot).select_related(
            "snapshot"
        )
        sources = [
            Source(source.file_path, source_content(source, 1, source.line_count))
            for source in files
            if source.file_path.endswith(".py")
        ]
        result = run_parser(
            str(record.snapshot_id),
            sources,
            record.root_urlconf,
            len(files) - len(sources),
        )
        frontend_sources = [
            Source(source.file_path, source_content(source, 1, source.line_count))
            for source in files
            if source.file_path.endswith((".js", ".jsx", ".ts", ".tsx"))
        ]
        frontend = associate(
            run_frontend_parser(str(record.snapshot_id), frontend_sources),
            result["endpoints"],
        )
        result["diagnostics"].extend(frontend["parser"]["diagnostics"])
        requests = {item["id"]: item for item in frontend["parser"]["requests"]}
        for match in frontend["matches"]:
            if match["status"] != "confirmed":
                result["diagnostics"].append(
                    {
                        "code": "FRONTEND_RELATION_UNRESOLVED",
                        "message": "前端请求未形成唯一确认关系；请查看候选和路径限制。",
                        "severity": "warning",
                        "source_ref": requests[match["request_id"]]["source_ref"],
                    }
                )
        if len(result["diagnostics"]) > 10_000:
            raise AnalysisFailed("diagnostic_limit")
        result["coverage"]["diagnostic_count"] = len(result["diagnostics"])
        result["coverage"]["complete"] = not result["diagnostics"]
        analysis_id = uuid.uuid4()
        graph = validate_graph(
            extend_graph(
                analysis_id,
                build_graph(analysis_id, result),
                frontend,
                result["endpoints"],
            ),
            str(record.snapshot_id),
            {source.file_path: source.line_count for source in files},
        )

        def publish() -> str:
            analysis = Analysis.objects.create(
                id=analysis_id,
                job_id=job_id,
                snapshot=record.snapshot,
                root_urlconf=record.root_urlconf,
                frontend=frontend,
                **result,
            )
            AnalysisGraph.objects.create(
                analysis=analysis, graph_version=GRAPH_VERSION, **graph
            )
            return f"/api/v1/analyses/{analysis.pk}/"

        jobs.complete_analysis(job_id, claim, publish)
    except Exception as exc:
        # 仅在任务边界归类未知失败；内容和 traceback 不进入日志或 Celery 结果。
        if isinstance(exc, AnalysisFailed):
            code, reason = "ANALYSIS_FAILED", exc.reason
        elif isinstance(exc, ImportRejected):
            code, reason = "SNAPSHOT_NOT_READY", "snapshot_integrity"
        elif isinstance(exc, TimeoutError):
            code, reason = "EXECUTION_TIMEOUT", "execution_timeout"
        else:
            code, reason = "ANALYSIS_FAILED", "processing_failed"
            logger.error("job_id=%s exception_type=%s", job_id, type(exc).__name__)
        try:
            jobs.fail_analysis(job_id, claim, code, reason)
        except DatabaseError:
            raise RuntimeError("分析状态需等待期限核对。") from None


def read_graph(analysis: Analysis) -> tuple[GraphData, str]:
    record = AnalysisGraph.objects.filter(analysis=analysis).first()
    if record is None:
        raise ApiProblem(
            409,
            "GRAPH_NOT_AVAILABLE",
            "该历史分析没有图结果，请使用新操作标识重新分析原快照。",
        )
    try:
        graph = validate_graph(
            {"nodes": record.nodes, "edges": record.edges},
            str(analysis.snapshot_id),
            dict(
                SourceFile.objects.filter(snapshot_id=analysis.snapshot_id).values_list(
                    "file_path", "line_count"
                )
            ),
            record.graph_version,
        )
    except AnalysisFailed:
        raise ApiProblem(
            500, "INTERNAL_ERROR", "保存的图结果无法通过完整性校验。"
        ) from None
    return graph, record.graph_version


def query_graph(analysis: Analysis, query: GraphQuery) -> GraphSelection:
    graph, version = read_graph(analysis)
    try:
        return {**select_graph(graph, query), "graph_version": version}
    except KeyError:
        raise ApiProblem(
            404, "RESOURCE_NOT_FOUND", "当前分析中不存在该图节点。"
        ) from None


def read_frontend(analysis: Analysis) -> FrontendAnalysis | None:
    """历史未分析与有效空结果分开；读取只校验，不执行分析。"""
    value: Any = analysis.frontend
    if value is None:
        return None
    try:
        if (
            not isinstance(value, dict)
            or set(value) != {"parser", "association_rule_version", "matches"}
            or value["association_rule_version"] != ASSOCIATION_RULE_VERSION
        ):
            raise AnalysisFailed("invalid_frontend_result")
        parser = validate_frontend(
            value["parser"],
            str(analysis.snapshot_id),
            {
                p: count
                for p, count in SourceFile.objects.filter(
                    snapshot_id=analysis.snapshot_id
                ).values_list("file_path", "line_count")
                if p.endswith((".js", ".jsx", ".ts", ".tsx"))
            },
        )
        requests = {item["id"]: item for item in parser["requests"]}
        if not isinstance(value["matches"], list) or len(value["matches"]) != len(
            requests
        ):
            raise AnalysisFailed("invalid_frontend_result")
        seen: set[str] = set()
        candidates = 0
        for match in value["matches"]:
            if not isinstance(match, dict) or set(match) != {
                "request_id",
                "status",
                "reason",
                "endpoint_indices",
                "evidence",
            }:
                raise AnalysisFailed("invalid_frontend_result")
            identity = match["request_id"]
            if (
                not isinstance(identity, str)
                or identity not in requests
                or identity in seen
            ):
                raise AnalysisFailed("invalid_frontend_result")
            seen.add(identity)
            indices = match["endpoint_indices"]
            if (
                not isinstance(indices, list)
                or any(
                    type(i) is not int or not 0 <= i < len(analysis.endpoints)
                    for i in indices
                )
                or indices != sorted(set(indices))
            ):
                raise AnalysisFailed("invalid_frontend_result")
            candidates += len(indices)
            if (
                candidates > 30_000
                or match["status"] not in {"confirmed", "candidate", "unmatched"}
                or not isinstance(match["reason"], str)
                or len(match["reason"]) > 200
                or match["evidence"] != requests[identity]["evidence"]
            ):
                raise AnalysisFailed("invalid_frontend_result")
            if (
                (
                    match["status"] == "confirmed"
                    and (
                        len(indices) != 1
                        or requests[identity]["resolution"] != "static"
                    )
                )
                or (match["status"] == "candidate" and not indices)
                or (match["status"] == "unmatched" and indices)
            ):
                raise AnalysisFailed("invalid_frontend_result")
        return cast(FrontendAnalysis, value)
    except (AnalysisFailed, KeyError, TypeError, ValueError):
        raise ApiProblem(
            500, "INTERNAL_ERROR", "保存的前端分析无法通过完整性校验。"
        ) from None
