"""组合原始图、当前人工修订与覆盖信息，不触发解析或模型。"""

import uuid
from typing import Any

from apps.analysis.impact import change_starts, eligible_graph, reverse_impact
from apps.analysis.models import Analysis, SnapshotComparison
from apps.analysis.reviews import graph_decisions
from apps.analysis.services import read_graph
from apps.analysis.types import SourceRef
from apps.projects.models import SourceFile
from common.errors import ApiProblem


def analysis_impact(
    analysis: Analysis,
    *,
    node_id: str | None,
    references: list[SourceRef] | None = None,
    include_candidates: bool = False,
    max_nodes: int = 200,
    max_edges: int = 400,
) -> dict[str, Any]:
    graph, version = read_graph(analysis)
    reviews = graph_decisions(analysis, graph)
    unmapped: list[str]
    if node_id is not None:
        if not any(node["id"] == node_id for node in graph["nodes"]):
            raise ApiProblem(404, "RESOURCE_NOT_FOUND", "对应分析中不存在该起点。")
        starts, unmapped = [node_id], []
    else:
        starts, unmapped = change_starts(
            eligible_graph(graph, reviews, include_candidates), references or []
        )
    selection = reverse_impact(
        graph,
        starts,
        reviews,
        include_candidates=include_candidates,
        max_nodes=max_nodes,
        max_edges=max_edges,
    )
    covered = {
        ref["file_path"]
        for node in graph["nodes"]
        for ref in [
            node["source_ref"],
            *[proof["source_ref"] for proof in node["evidence"]],
        ]
        if ref
    }
    covered.update(
        proof["source_ref"]["file_path"]
        for edge in graph["edges"]
        for proof in edge["evidence"]
        if proof["source_ref"]
    )
    missing = sorted(
        set(
            SourceFile.objects.filter(snapshot_id=analysis.snapshot_id).values_list(
                "file_path", flat=True
            )
        )
        - covered
    )
    diagnostics = analysis.diagnostics
    frontend = analysis.frontend
    limitations = [
        "静态候选范围不代表运行轨迹；未找到结果不能说明没有影响。",
        "只覆盖已识别的依赖，不传播运行时参数或动态调用。",
        *analysis.coverage.get("limitations", []),
    ]
    if frontend is None:
        limitations.append("此历史分析没有前端结果；读取不会补算。")
    else:
        coverage = frontend.get("parser", {}).get("coverage", {})
        limitations.extend(coverage.get("limitations", []))
        diagnostics = [*diagnostics, *frontend.get("parser", {}).get("diagnostics", [])]
    return {
        "analysis_id": str(analysis.pk),
        "snapshot_id": str(analysis.snapshot_id),
        "graph_version": version,
        "rule_version": analysis.rule_version,
        "include_candidates": include_candidates,
        "max_nodes": max_nodes,
        "max_edges": max_edges,
        **selection,
        "unmapped_files": unmapped,
        "uncovered_files": missing,
        "limitations": list(dict.fromkeys(limitations)),
        "diagnostics": diagnostics,
        "diagnostics_url": f"/api/v1/analyses/{analysis.pk}/diagnostics/",
    }


def comparison_impact(
    result: SnapshotComparison,
    data: dict[str, Any],
    *,
    include_candidates: bool,
    max_nodes: int,
    max_edges: int,
    change_id: uuid.UUID | None,
) -> dict[str, Any]:
    files = data["files"]
    if change_id is not None:
        files = [file for file in files if file["id"] == str(change_id)]
        if not files:
            raise ApiProblem(404, "RESOURCE_NOT_FOUND", "对比中不存在指定文件变化。")
    record = result.request
    sides = {}
    for side, snapshot, analysis in (
        ("base", record.base_snapshot_id, record.base_analysis),
        ("target", record.target_snapshot_id, record.target_analysis),
    ):
        references = [ref for file in files for ref in file[side + "_ranges"]]
        impact: dict[str, Any] | None = None
        missing_graph = analysis is None
        if analysis is not None:
            try:
                impact = analysis_impact(
                    analysis,
                    node_id=None,
                    references=references,
                    include_candidates=include_candidates,
                    max_nodes=max_nodes,
                    max_edges=max_edges,
                )
            except ApiProblem as error:
                if error.machine_code != "GRAPH_NOT_AVAILABLE":
                    raise
                missing_graph = True
        if missing_graph:
            impact = None
        sides[side] = {
            "snapshot_id": str(snapshot),
            "analysis_id": str(analysis.pk) if analysis else None,
            "available": not missing_graph,
            "reason": "未绑定分析或历史图不可用，不能判断影响。"
            if missing_graph
            else None,
            "changed_files": sorted({ref["file_path"] for ref in references}),
            "impact": impact,
        }
    return {
        "comparison_id": str(result.pk),
        "change_id": str(change_id) if change_id else None,
        "include_candidates": include_candidates,
        **sides,
        "limitations": [
            "两侧分别计算：基准处理删除与修改前，目标处理新增与修改后。",
            "两侧规则不同仍可各自查看影响，不能把结果差异归因为源码变化。",
        ],
    }
