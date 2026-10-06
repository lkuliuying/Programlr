import time
import uuid

from apps.analysis.diffs.protocol import validate_comparison
from apps.analysis.diffs.types import (
    COMPARISON_VERSION,
    MAX_CHANGED_BYTES,
    MAX_FILES,
    MAX_SOURCE_BYTES,
    TIMEOUT_SECONDS,
    AnalysisInput,
    ComparisonData,
    ComparisonFailed,
    ComparisonInput,
    FileInput,
)
from apps.analysis.models import Analysis, SnapshotComparison, SnapshotComparisonRequest
from apps.analysis.protocol import validate_stored_result
from apps.analysis.services import read_graph
from apps.analysis.types import AnalysisFailed, SourceRef
from apps.explanations.evidence import read_saved_evidence
from apps.jobs import services as jobs
from apps.jobs.models import Job
from apps.projects.models import Project, Snapshot, SourceFile
from apps.projects.services import source_content, validate_snapshot
from common.errors import ApiProblem
from common.retirement import retired_feature


def submit_comparison(
    project: Project,
    key: uuid.UUID,
    base: Snapshot,
    target: Snapshot,
    base_analysis: Analysis | None,
    target_analysis: Analysis | None,
    *,
    previous: Job | None = None,
) -> tuple[Job, bool, bool]:
    retired_feature("snapshot_comparison")


def retry_comparison(previous: Job, key: uuid.UUID) -> tuple[Job, bool, bool]:
    retired_feature("snapshot_comparison")


def analysis_input(
    analysis: Analysis | None, line_counts: dict[str, int]
) -> AnalysisInput | None:
    if analysis is None:
        return None
    result = validate_stored_result(
        {
            "rule_version": analysis.rule_version,
            "coverage": analysis.coverage,
            "endpoints": analysis.endpoints,
            "diagnostics": analysis.diagnostics,
        },
        str(analysis.snapshot_id),
        line_counts,
        analysis.rule_version,
    )
    try:
        graph, graph_version = read_graph(analysis)
    except ApiProblem as error:
        if error.machine_code != "GRAPH_NOT_AVAILABLE":
            raise
        graph, graph_version = None, None
    frontend = analysis.frontend
    front_version, association_version = None, None
    if frontend is not None:
        try:
            front_version, association_version = (
                frontend["parser"]["rule_version"],
                frontend["association_rule_version"],
            )
            if not all(
                isinstance(value, str) and 0 < len(value) <= 80
                for value in (front_version, association_version)
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise ComparisonFailed("invalid_analysis_version") from None
    if graph:
        nodes = {
            node["endpoint"]["index"]: node["endpoint"]
            for node in graph["nodes"]
            if node["endpoint"]
        }
        if set(nodes) != set(range(len(result["endpoints"]))) or any(
            any(
                left != right
                for left, right in (
                    (node["method"], result["endpoints"][index]["method"]),
                    (node["path"], result["endpoints"][index]["path"]),
                    (node["path_kind"], result["endpoints"][index]["path_kind"]),
                    (node["action"], result["endpoints"][index]["action"]),
                )
            )
            for index, node in nodes.items()
        ):
            raise ComparisonFailed("invalid_analysis_result")
    return {
        "version": {
            "analysis_id": str(analysis.pk),
            "snapshot_id": str(analysis.snapshot_id),
            "root_urlconf": analysis.root_urlconf,
            "rule_version": analysis.rule_version,
            "graph_version": graph_version,
            "frontend_rule_version": front_version,
            "association_rule_version": association_version,
        },
        "graph": graph,
        "endpoints": result["endpoints"],
    }


def prepare_input(record: SnapshotComparisonRequest) -> ComparisonInput:
    for snapshot in (record.base_snapshot, record.target_snapshot):
        validate_snapshot(snapshot)
    sides = [
        list(SourceFile.objects.filter(snapshot=snapshot).select_related("snapshot"))
        for snapshot in (record.base_snapshot, record.target_snapshot)
    ]
    maps = [{source.file_path: source for source in files} for files in sides]
    paths = sorted(maps[0].keys() | maps[1].keys())
    if len(paths) > MAX_FILES:
        raise ComparisonFailed("file_count_limit")
    if sum(source.size_bytes for files in sides for source in files) > MAX_SOURCE_BYTES:
        raise ComparisonFailed("source_bytes_limit")
    files: list[FileInput] = []
    changed_bytes, deadline = 0, time.monotonic() + TIMEOUT_SECONDS

    def ref(source: SourceFile | None) -> SourceRef | None:
        return (
            {
                "snapshot_id": str(source.snapshot_id),
                "file_path": source.file_path,
                "start_line": 1,
                "end_line": source.line_count,
            }
            if source
            else None
        )

    for path in paths:
        old, new = maps[0].get(path), maps[1].get(path)
        unchanged = bool(old and new and old.sha256 == new.sha256)
        contents: list[str | None] = []
        for source in (old, new):
            if source is None:
                contents.append(None)
                continue
            if not unchanged:
                changed_bytes += source.size_bytes
                if changed_bytes > MAX_CHANGED_BYTES:
                    raise ComparisonFailed("changed_bytes_limit")
            # 未变文件也核验已发布内容，但立即丢弃正文，不复制两个快照全文。
            text = source_content(source, 1, source.line_count)
            contents.append(None if unchanged else text)
            if time.monotonic() > deadline:
                raise ComparisonFailed("snapshot_read_timeout")
        files.append(
            {
                "file_path": path,
                "base_ref": ref(old),
                "target_ref": ref(new),
                "base_sha256": old.sha256 if old else None,
                "target_sha256": new.sha256 if new else None,
                "base_content": contents[0],
                "target_content": contents[1],
            }
        )
    counts = [
        {source.file_path: source.line_count for source in files} for files in sides
    ]
    return {
        "comparison_id": str(record.pk),
        "base_snapshot_id": str(record.base_snapshot_id),
        "target_snapshot_id": str(record.target_snapshot_id),
        "files": files,
        "base_analysis": analysis_input(record.base_analysis, counts[0]),
        "target_analysis": analysis_input(record.target_analysis, counts[1]),
        "evidence": read_saved_evidence(
            record.base_snapshot_id, record.base_analysis_id, counts[0]
        ),
    }


def execute_comparison(job_id: str) -> None:
    jobs.refuse_retired_job(job_id)


def read_comparison(result: SnapshotComparison) -> ComparisonData:
    record = result.request
    try:
        sides = [
            dict(
                SourceFile.objects.filter(snapshot_id=snapshot).values_list(
                    "file_path", "line_count"
                )
            )
            for snapshot in (record.base_snapshot_id, record.target_snapshot_id)
        ]
        analyses = [
            analysis_input(analysis, counts)
            for analysis, counts in zip(
                (record.base_analysis, record.target_analysis), sides, strict=True
            )
        ]
        data = validate_comparison(
            result.data,
            str(record.pk),
            str(record.base_snapshot_id),
            str(record.target_snapshot_id),
            (
                str(record.base_analysis_id) if record.base_analysis_id else None,
                str(record.target_analysis_id) if record.target_analysis_id else None,
            ),
            (
                analyses[0]["graph"] if analyses[0] else None,
                analyses[1]["graph"] if analyses[1] else None,
            ),
        )
        if (
            result.comparison_version != COMPARISON_VERSION
            or result.summary != data["summary"]
            or data["base_version"] != (analyses[0]["version"] if analyses[0] else None)
            or data["target_version"]
            != (analyses[1]["version"] if analyses[1] else None)
        ):
            raise ComparisonFailed("invalid_comparison_result")
        for side, snapshot in (
            ("base", record.base_snapshot_id),
            ("target", record.target_snapshot_id),
        ):
            known = {
                source.file_path: (source.sha256, source.line_count)
                for source in SourceFile.objects.filter(snapshot_id=snapshot)
            }
            saved = {}
            for file in data["files"]:
                ref = file["base_ref"] if side == "base" else file["target_ref"]
                if ref:
                    saved[file["file_path"]] = (
                        file["base_sha256"]
                        if side == "base"
                        else file["target_sha256"],
                        ref["end_line"],
                    )
            if saved != known:
                raise ComparisonFailed("invalid_comparison_result")
        return data
    except (ComparisonFailed, AnalysisFailed):
        raise ApiProblem(
            500, "INTERNAL_ERROR", "保存的快照对比无法通过完整性校验。"
        ) from None
