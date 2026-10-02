import json
from pathlib import Path
from typing import Any

from apps.analysis.models import Analysis
from apps.projects.models import SourceFile
from common.errors import ApiProblem

ROOT = Path(__file__).resolve().parents[3] / "content"


def definition(analysis: Analysis, index: int) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(
        (ROOT / "labs/request-validation.json").read_text(encoding="utf-8")
    )
    signature = json.loads(
        (ROOT / "exercises/task-board-create.json").read_text(encoding="utf-8")
    )["files"]
    if not 0 <= index < len(analysis.endpoints):
        raise ApiProblem(400, "VALIDATION_ERROR", "接口序号越界。")
    endpoint = analysis.endpoints[index]
    actual = dict(
        SourceFile.objects.filter(snapshot_id=analysis.snapshot_id).values_list(
            "file_path", "sha256"
        )
    )
    result["applicable"] = (
        endpoint["method"] == "POST"
        and endpoint["path"] == "/api/v1/tasks/"
        and all(actual.get(path) == digest for path, digest in signature.items())
    )
    result["applicability_reason"] = (
        "仅在独立内置示例运行，不运行此快照。"
        if result["applicable"]
        else "当前接口或快照不匹配内置任务簿，尚无对应实验。"
    )
    return result
