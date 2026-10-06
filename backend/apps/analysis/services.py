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
from apps.analysis.models import (
    Analysis,
    AnalysisGraph,
    AnalysisRequest,
    SnapshotPreparation,
    SourceScan,
)
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
from apps.projects.services import snapshot_contents
from common.errors import ApiProblem
from common.resource_state import lock_snapshot, require_snapshot_available

logger = logging.getLogger(__name__)


def submit_analysis(
    snapshot: Snapshot,
    key: uuid.UUID,
    root_urlconf: str,
    *,
    previous: Job | None = None,
    source_scan: SourceScan | None = None,
    parent: Job | None = None,
    defer_dispatch: bool = False,
) -> tuple[Job, bool, bool]:
    digest = hashlib.sha256(
        json.dumps({"root_urlconf": root_urlconf}, sort_keys=True).encode()
    ).hexdigest()
    with transaction.atomic():
        snapshot = lock_snapshot(snapshot.pk)
        preparation = (
            SnapshotPreparation.objects.select_for_update()
            .filter(snapshot=snapshot)
            .first()
        )
        if previous is not None:
            source_scan = AnalysisRequest.objects.get(job=previous).source_scan
        elif source_scan is None and preparation is not None:
            source_scan = preparation.source_scan
        if source_scan is not None and source_scan.snapshot_id != snapshot.pk:
            raise ApiProblem(409, "SCAN_SCOPE_MISMATCH", "源码扫描必须属于当前快照。")
        if previous is not None:
            job, created = jobs.create_retry_job(previous, key, digest)
        else:
            job, created = jobs.create_analysis_job(
                snapshot.pk,
                key,
                digest,
                parent=parent,
                source_kind=parent.source_kind
                if parent
                else source_scan.job.source_kind
                if source_scan
                else snapshot.job.source_kind,
            )
        if created:
            if source_scan is not None and root_urlconf not in {
                item["file_path"] for item in source_scan.result["roots"]["candidates"]
            }:
                raise ApiProblem(
                    400, "ROOT_NOT_AVAILABLE", "请选择此快照扫描确认的根路由候选。"
                )
            AnalysisRequest.objects.create(
                job=job,
                snapshot=snapshot,
                root_urlconf=root_urlconf,
                source_scan=source_scan,
            )
            if preparation is not None:
                preparation.analysis_job = job
                preparation.analysis = None
                preparation.status = "analyzing"
                preparation.save(update_fields=["analysis_job", "analysis", "status"])
            if defer_dispatch:

                def dispatch() -> None:
                    try:
                        jobs.dispatch_analysis(job)
                    except DatabaseError as exc:
                        logger.error(
                            "job_id=%s dispatch_type=%s", job.pk, type(exc).__name__
                        )

                transaction.on_commit(dispatch)
    published = jobs.dispatch_analysis(job) if created and not defer_dispatch else True
    job.refresh_from_db()
    return job, created, published


def execute_analysis(job_id: str) -> None:
    record: AnalysisRequest | None = None
    try:
        claim = jobs.claim_analysis(job_id)
    except DatabaseError:
        raise RuntimeError("分析领取需等待期限核对。") from None
    if claim is None:
        return
    try:
        record = AnalysisRequest.objects.select_related(
            "snapshot", "snapshot__project"
        ).get(job_id=job_id)
        require_snapshot_available(record.snapshot)
        files = SourceFile.objects.filter(snapshot=record.snapshot).select_related(
            "snapshot", "snapshot__project"
        )
        contents = {
            source.file_path: content
            for source, content in snapshot_contents(
                record.snapshot,
                [
                    source
                    for source in files
                    if source.file_path.endswith((".py", ".js", ".jsx", ".ts", ".tsx"))
                ],
            )
        }
        sources = [
            Source(source.file_path, contents[source.file_path])
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
            Source(source.file_path, contents[source.file_path])
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
            lock_snapshot(record.snapshot_id)
            analysis = Analysis.objects.create(
                id=analysis_id,
                job_id=job_id,
                snapshot=record.snapshot,
                root_urlconf=record.root_urlconf,
                frontend=frontend,
                source_scan=record.source_scan,
                **result,
            )
            AnalysisGraph.objects.create(
                analysis=analysis, graph_version=GRAPH_VERSION, **graph
            )
            SnapshotPreparation.objects.filter(
                snapshot_id=record.snapshot_id, analysis_job_id=uuid.UUID(job_id)
            ).update(status="ready", analysis=analysis)
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
            if record is not None:
                SnapshotPreparation.objects.filter(
                    snapshot_id=record.snapshot_id,
                    analysis_job_id=uuid.UUID(job_id),
                    analysis_job__status=Job.Status.FAILED,
                ).update(status="failed")
        except DatabaseError:
            raise RuntimeError("分析状态需等待期限核对。") from None


def read_graph(analysis: Analysis) -> tuple[GraphData, str]:
    require_snapshot_available(analysis.snapshot)
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
    require_snapshot_available(analysis.snapshot)
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
