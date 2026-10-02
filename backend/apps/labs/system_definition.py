import hashlib
from typing import Any

from apps.analysis.models import Analysis
from apps.labs.definition import ROOT, definition
from apps.labs.system_adapter import PROGRAM
from apps.learning.content import TEXT, VERSION, read_content
from common.errors import ApiProblem

LAB_IDS = ("container-network", "subprocess-lifecycle")
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id",
        "version",
        "title",
        "example_version",
        "description",
        "cases",
        "program_digest",
    ],
    "properties": {
        "id": {"enum": list(LAB_IDS)},
        "version": VERSION,
        "title": TEXT,
        "example_version": {"const": "system-labs/1.0.0"},
        "program_digest": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "description": TEXT,
        "cases": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title", "prediction_label"],
                "properties": {
                    "id": {"enum": ["first", "second"]},
                    "title": TEXT,
                    "prediction_label": TEXT,
                },
            },
        },
    },
}


def system_definition(lab_id: str, analysis: Analysis, index: int) -> dict[str, Any]:
    if lab_id not in LAB_IDS:
        raise ApiProblem(404, "RESOURCE_NOT_FOUND", "固定系统实验不存在。")
    result: dict[str, Any] = read_content(ROOT / "labs" / f"{lab_id}.json", SCHEMA)
    if hashlib.sha256(PROGRAM.read_bytes()).hexdigest() != result["program_digest"]:
        raise ApiProblem(409, "LAB_VERSION_MISMATCH", "可信实验程序摘要与定义不匹配。")
    if result["id"] != lab_id or [case["id"] for case in result["cases"]] != [
        "first",
        "second",
    ]:
        raise ValueError("固定实验定义身份或用例顺序无效。")
    original = definition(analysis, index)
    result["applicable"] = original["applicable"]
    result["applicability_reason"] = original["applicability_reason"]
    return result
