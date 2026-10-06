import uuid
from typing import Any

from apps.analysis.models import Analysis
from apps.learning.models import Exercise, ExerciseAttempt
from apps.projects.models import SourceFile
from common.errors import ApiProblem
from common.retirement import retired_feature


def applicability(
    exercise: Exercise, analysis: Analysis, endpoint_index: int
) -> tuple[bool, str]:
    if not 0 <= endpoint_index < len(analysis.endpoints):
        raise ApiProblem(404, "RESOURCE_NOT_FOUND", "所选接口不存在。")
    endpoint = analysis.endpoints[endpoint_index]
    if endpoint["method"] != "POST" or endpoint["path"] != "/api/v1/tasks/":
        return False, "固定题仅适用于内置任务簿的创建任务接口。"
    actual = dict(
        SourceFile.objects.filter(snapshot_id=analysis.snapshot_id).values_list(
            "file_path", "sha256"
        )
    )
    if any(
        actual.get(path) != expected
        for path, expected in exercise.example.files.items()
    ):
        return False, "当前快照与教学示例的已核对源码版本不匹配。"
    return True, "已核对示例相关文件摘要；不代表其他导入文件或运行行为已验证。"


def validate_answer(kind: str, options: list[dict[str, Any]], answer: Any) -> None:
    ids = {option["id"] for option in options}
    valid = False
    if kind == "flow_order":
        valid = (
            isinstance(answer, list)
            and all(isinstance(item, str) for item in answer)
            and len(answer) == len(ids)
            and set(answer) == ids
        )
    elif kind == "error_prediction":
        valid = (
            isinstance(answer, dict)
            and set(answer) == ids
            and all(
                isinstance(value, dict)
                and set(value) == {"status", "writes"}
                and type(value["status"]) is int
                and 100 <= value["status"] <= 599
                and type(value["writes"]) is int
                and value["writes"] in {0, 1}
                for value in answer.values()
            )
        )
    elif kind == "code_location":
        valid = (
            isinstance(answer, dict)
            and set(answer) == {"file_path", "start_line", "end_line"}
            and isinstance(answer["file_path"], str)
            and answer["file_path"] in ids
        )
        if valid:
            valid = (
                type(answer["start_line"]) is int
                and type(answer["end_line"]) is int
                and 1 <= answer["start_line"] <= answer["end_line"] <= 1_000_000
            )
    if not valid:
        raise ApiProblem(400, "VALIDATION_ERROR", "作答格式不符合当前题型要求。")


def submit_attempt(
    key: uuid.UUID, values: dict[str, Any]
) -> tuple[ExerciseAttempt, bool]:
    retired_feature("exercise")
