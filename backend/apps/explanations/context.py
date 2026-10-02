import hashlib
from typing import Any

from apps.analysis.models import Analysis
from apps.analysis.services import query_graph
from apps.analysis.types import GraphQuery
from apps.explanations.configuration import (
    ModelConfiguration,
    configuration,
    digest,
    encode,
)
from apps.explanations.models import ContextPreview
from apps.explanations.validation import TEMPLATE, TEMPLATE_VERSION
from apps.projects.exceptions import ImportRejected
from apps.projects.models import SourceFile
from apps.projects.services import source_content
from common.errors import ApiProblem


def build_payload(
    analysis: Analysis,
    endpoint_index: int,
    node_ids: list[str] | None,
    excluded_snippets: list[str] | None = None,
) -> dict[str, Any]:
    config = configuration()
    if not 0 <= endpoint_index < len(analysis.endpoints):
        raise ApiProblem(404, "RESOURCE_NOT_FOUND", "该分析中不存在所选接口。")
    selection = query_graph(
        analysis, GraphQuery(endpoint_index=endpoint_index, max_nodes=50, max_edges=100)
    )
    nodes = selection["nodes"]
    if node_ids is not None:
        if not node_ids or not set(node_ids) <= {n["id"] for n in nodes}:
            raise ApiProblem(
                400, "VALIDATION_ERROR", "节点选择必须来自所选接口的有界关系图。"
            )
        nodes = [n for n in nodes if n["id"] in node_ids]
    selected_ids = {n["id"] for n in nodes}
    edges = [
        e
        for e in selection["edges"]
        if e["source_id"] in selected_ids and e["target_id"] in selected_ids
    ]
    references = [n["source_ref"] for n in nodes if n["source_ref"] is not None]
    references += [
        ev["source_ref"]
        for item in [*nodes, *edges]
        for ev in item["evidence"]
        if ev["source_ref"] is not None
    ]
    ranges: dict[str, list[tuple[int, int]]] = {}
    for ref in references:
        ranges.setdefault(ref["file_path"], []).append(
            (ref["start_line"], ref["end_line"])
        )
    files = {
        f.file_path: f
        for f in SourceFile.objects.filter(
            snapshot_id=analysis.snapshot_id
        ).select_related("snapshot")
    }
    snippets: list[dict[str, Any]] = []
    available_ids: set[str] = set()
    omitted = list(selection["truncation_reasons"])
    endpoint = analysis.endpoints[endpoint_index]
    context: dict[str, Any] = {
        "snapshot_id": str(analysis.snapshot_id),
        "endpoint": {"method": endpoint["method"], "path": endpoint["path"]},
        "limitations": analysis.coverage["limitations"],
        "relations": [
            {
                "source": next(
                    n["name"] for n in nodes if n["id"] == edge["source_id"]
                ),
                "target": next(
                    n["name"] for n in nodes if n["id"] == edge["target_id"]
                ),
                "relation": edge["relation"],
                "evidence": [
                    {"kind": ev["kind"], "rule": ev["rule"]} for ev in edge["evidence"]
                ],
            }
            for edge in edges
        ],
        "snippets": snippets,
    }

    def messages() -> list[dict[str, str]]:
        return [
            {"role": "system", "content": TEMPLATE},
            {"role": "user", "content": encode(context).decode("utf-8")},
        ]

    for path, spans in sorted(ranges.items()):
        merged: list[tuple[int, int]] = []
        for start, end in sorted(set(spans)):
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        for start, end in merged:
            source = files[path]
            try:
                content = source_content(source, start, end)
            except ImportRejected:
                raise ApiProblem(
                    409, "SNAPSHOT_NOT_READY", "快照内容完整性检查失败。"
                ) from None
            ref = {
                "snapshot_id": str(analysis.snapshot_id),
                "file_path": path,
                "start_line": start,
                "end_line": end,
            }
            snippet_id = digest(ref)
            available_ids.add(snippet_id)
            if snippet_id in (excluded_snippets or []):
                omitted.append("user_excluded")
                continue
            snippet = {
                "id": snippet_id,
                "source_ref": ref,
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
                "content": content,
            }
            snippets.append(snippet)
    if not set(excluded_snippets or []) <= available_ids:
        raise ApiProblem(
            400, "VALIDATION_ERROR", "排除片段必须来自当前节点选择的引用范围。"
        )
    if not snippets:
        raise ApiProblem(
            409,
            "CONTEXT_UNAVAILABLE",
            "当前选择没有可用源码片段，请调整节点或排除范围。",
        )
    return {
        "configuration": config.binding(),
        "excluded_snippets": sorted(set(excluded_snippets or [])),
        "template_version": TEMPLATE_VERSION,
        "messages": messages(),
        "snippets": snippets,
        "nodes": [{"id": n["id"], "name": n["name"], "kind": n["kind"]} for n in nodes],
        "omissions": sorted(set(omitted)),
        "context_bytes": len(encode(messages())),
    }


def check_preview(preview: ContextPreview) -> ModelConfiguration:
    config = configuration()
    payload = preview.payload
    if (
        digest(payload) != preview.payload_digest
        or payload["configuration"] != config.binding()
        or payload["template_version"] != TEMPLATE_VERSION
        or payload["messages"][0] != {"role": "system", "content": TEMPLATE}
    ):
        raise ApiProblem(
            409, "CONSENT_STALE", "外发范围或模型配置已变化，请重新预览并确认。"
        )
    for item in payload["snippets"]:
        ref = item["source_ref"]
        source = (
            SourceFile.objects.select_related("snapshot")
            .filter(snapshot_id=preview.snapshot_id, file_path=ref["file_path"])
            .first()
        )
        if (
            source is None
            or ref["snapshot_id"] != str(preview.snapshot_id)
            or not 1 <= ref["start_line"] <= ref["end_line"] <= source.line_count
        ):
            raise ApiProblem(409, "CONSENT_STALE", "预览引用已失效，请重新核对快照。")
        try:
            content = source_content(source, ref["start_line"], ref["end_line"])
        except ImportRejected:
            raise ApiProblem(
                409, "CONSENT_STALE", "快照完整性检查失败，未发送请求。"
            ) from None
        if (
            content != item["content"]
            or hashlib.sha256(content.encode()).hexdigest() != item["sha256"]
        ):
            raise ApiProblem(409, "CONSENT_STALE", "预览片段已失效，未发送请求。")
    return config
