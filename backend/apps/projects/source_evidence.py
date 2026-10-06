"""聚合已保存的文件依据，不执行源码或触发新的分析。"""

import hashlib
import json
from typing import Any

from apps.analysis.models import Analysis, AnalysisGraph, SourceScan
from apps.learning.knowledge import knowledge_hits
from apps.projects.models import SourceFile


def file_evidence(
    source: SourceFile, analysis: Analysis | None, scan: SourceScan | None
) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}

    def add(
        kind: str,
        label: str,
        reference: Any,
        endpoint_index: int | None = None,
        node_id: str | None = None,
        concept_key: str | None = None,
    ) -> None:
        if not isinstance(reference, dict):
            return
        start, end = reference.get("start_line"), reference.get("end_line")
        if (
            str(reference.get("snapshot_id")) != str(source.snapshot_id)
            or reference.get("file_path") != source.file_path
            or type(start) is not int
            or type(end) is not int
            or not 1 <= start <= end <= source.line_count
        ):
            return
        item = {
            "kind": kind,
            "label": label,
            "source_ref": reference,
            "endpoint_index": endpoint_index,
            "node_id": node_id,
            "concept_key": concept_key,
        }
        identity = hashlib.sha256(
            json.dumps(item, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        records[identity] = {"id": identity, **item}

    if analysis is not None:
        for index, endpoint in enumerate(analysis.endpoints):
            title = f"{endpoint['method']} {endpoint['path']}"
            for name, label in (
                ("view", "处理器"),
                ("serializer", "序列化器"),
                ("model", "数据模型"),
            ):
                symbol = endpoint.get(name)
                if symbol:
                    add("interface", f"{title} · {label}", symbol["source_ref"], index)
            for evidence in endpoint.get("evidence", []):
                add(
                    "interface",
                    f"{title} · {evidence['rule']}",
                    evidence.get("source_ref"),
                    index,
                )
            for link in endpoint.get("frontend_links", []):
                add(
                    "frontend",
                    f"{title} · 前端请求（{link['status']}）",
                    link.get("source_ref"),
                    index,
                )
        graph = AnalysisGraph.objects.filter(analysis=analysis).first()
        if graph is not None:
            for node in graph.nodes:
                add(
                    "relation",
                    f"关系节点 · {node.get('label', node.get('kind', '源码'))}",
                    node.get("source_ref"),
                    node_id=node["id"],
                )
            for edge in graph.edges:
                for evidence in edge.get("evidence", []):
                    add(
                        "relation",
                        f"关系依据 · {evidence['rule']}",
                        evidence.get("source_ref"),
                    )
    if scan is not None and isinstance(scan.result.get("knowledge"), dict):
        for hit in knowledge_hits(scan):
            add(
                "knowledge",
                f"知识命中 · {hit['concept_key']} · {hit['rule_id']}",
                hit["source_ref"],
                concept_key=hit["concept_key"],
            )
    return sorted(
        records.values(),
        key=lambda item: (
            item["source_ref"]["start_line"],
            item["source_ref"]["end_line"],
            item["kind"],
            item["id"],
        ),
    )
