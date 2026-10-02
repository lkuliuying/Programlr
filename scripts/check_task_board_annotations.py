"""检查人工标注的引用完整性，不实现或替代源码分析器。"""

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ANNOTATION = ROOT / "testdata/analysis/task-board-create.json"


def validate(data: dict[str, Any], root: Path = ROOT) -> None:
    if (
        data["source_root"] != "examples/task-board"
        or data["example_version"] != "task-board/1.0.0"
    ):
        raise ValueError("示例归属或版本不匹配。")
    base = (root / data["source_root"]).resolve()
    nodes = data["nodes"]
    ids = {node["id"] for node in nodes}
    if not ids or len(ids) != len(nodes):
        raise ValueError("节点为空或标识重复。")
    references = [node["source_ref"] for node in nodes]
    for edge in data["edges"]:
        if edge["from"] not in ids or edge["to"] not in ids:
            raise ValueError("关系指向不存在的节点。")
        if (
            edge["evidence_type"] == "framework_inference"
            and edge.get("framework_rule") not in data["framework_rules"]
        ):
            raise ValueError("框架推导缺少规则依据。")
        references.extend(edge["source_refs"])
    for ref in references:
        raw = ref["file_path"]
        relative = PurePosixPath(raw)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in raw
            or ":" in raw
        ):
            raise ValueError("引用路径越界。")
        path = (base / raw).resolve()
        if not path.is_relative_to(base) or path.suffix not in {".py", ".ts", ".tsx"}:
            raise ValueError("引用路径越界。")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != ref["sha256"]:
            raise ValueError(f"文件摘要漂移：{raw}")
        lines = content.decode("utf-8").splitlines()
        start, end = ref["start_line"], ref["end_line"]
        if not (
            isinstance(start, int)
            and isinstance(end, int)
            and 1 <= start <= end <= len(lines)
        ):
            raise ValueError(f"引用行号越界：{raw}")
        if (
            lines[start - 1].strip() != ref["start_anchor"]
            or lines[end - 1].strip() != ref["end_anchor"]
        ):
            raise ValueError(f"引用锚点漂移：{raw}")


if __name__ == "__main__":
    annotations = json.loads(ANNOTATION.read_text(encoding="utf-8"))
    validate(annotations)
    print(
        f"人工标注引用检查通过：{len(annotations['nodes'])} 个节点、{len(annotations['edges'])} 条关系。"
    )
