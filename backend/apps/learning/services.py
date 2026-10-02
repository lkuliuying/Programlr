import uuid
from typing import Any

from django.shortcuts import get_object_or_404

from apps.analysis.models import Analysis
from apps.learning.content import content_digest
from apps.learning.models import Exercise, ExerciseAttempt
from apps.projects.models import SourceFile
from common.errors import ApiProblem, Conflict


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
    values = dict(values)
    previous_id = values.pop("previous_attempt_id", None)
    canonical = {
        **values,
        "exercise_id": str(values["exercise_id"]),
        "analysis_id": str(values["analysis_id"]),
        "snapshot_id": str(values["snapshot_id"]),
    }
    if previous_id is not None:
        canonical["previous_attempt_id"] = str(previous_id)
    request_digest = content_digest(canonical)
    old = ExerciseAttempt.objects.filter(idempotency_key=key).first()
    if old is not None:
        if old.request_digest != request_digest:
            raise Conflict
        return old, False
    exercise = get_object_or_404(
        Exercise.objects.select_related("example"), pk=values["exercise_id"]
    )
    if values["exercise_version"] != exercise.version:
        raise ApiProblem(
            409, "EXERCISE_VERSION_MISMATCH", "题目版本不匹配，请重新读取题目。"
        )
    analysis = get_object_or_404(Analysis, pk=values["analysis_id"])
    if analysis.snapshot_id != values["snapshot_id"]:
        raise ApiProblem(409, "EXERCISE_NOT_APPLICABLE", "作答快照与分析记录不匹配。")
    if previous_id is not None:
        previous = get_object_or_404(ExerciseAttempt, pk=previous_id)
        if (
            previous.exercise_id != exercise.pk
            or previous.snapshot_id != analysis.snapshot_id
            or previous.analysis_id != analysis.pk
            or previous.endpoint_index != values["endpoint_index"]
        ):
            raise ApiProblem(
                409,
                "REATTEMPT_SCOPE_MISMATCH",
                "重新练习必须属于原题版本与同一工作区。",
            )
    applies, reason = applicability(exercise, analysis, values["endpoint_index"])
    if not applies:
        raise ApiProblem(409, "EXERCISE_NOT_APPLICABLE", reason)
    validate_answer(exercise.kind, exercise.options, values["answer"])
    answer = values["answer"]
    if exercise.kind == "code_location":
        source = SourceFile.objects.get(
            snapshot_id=analysis.snapshot_id, file_path=answer["file_path"]
        )
        if answer["end_line"] > source.line_count:
            raise ApiProblem(400, "VALIDATION_ERROR", "作答行号超出当前文件范围。")
    record, created = ExerciseAttempt.objects.get_or_create(
        idempotency_key=key,
        defaults={
            "exercise": exercise,
            "snapshot_id": analysis.snapshot_id,
            "analysis": analysis,
            "endpoint_index": values["endpoint_index"],
            "request_digest": request_digest,
            "answer": answer,
            "hint_used": values["hint_used"],
            "correct": answer == exercise.answer,
            "feedback": {
                "expected_answer": exercise.answer,
                "explanation": exercise.explanation,
                "source_refs": [
                    {"snapshot_id": str(analysis.snapshot_id), **ref}
                    for ref in exercise.source_refs
                ],
            },
            "previous_attempt_id": previous_id,
        },
    )
    if record.request_digest != request_digest:
        raise Conflict
    return record, created
