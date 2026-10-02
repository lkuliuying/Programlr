"""载入可信的版本化教学内容；相同版本的内容漂移不能静默覆盖。"""

import json
from pathlib import Path
from typing import Any

from django.db import transaction
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]

from apps.learning.models import Exercise, KnowledgeCard, TeachingExample
from common.errors import ApiProblem

CONTENT_ROOT = Path(__file__).resolve().parents[3] / "content"
TEXT = {"type": "string", "minLength": 1, "maxLength": 8000}
VERSION = {"type": "string", "pattern": r"^[a-zA-Z0-9./_-]{1,40}$"}
REF = {
    "type": "object",
    "additionalProperties": False,
    "required": ["file_path", "start_line", "end_line"],
    "properties": {
        "file_path": TEXT,
        "start_line": {"type": "integer", "minimum": 1},
        "end_line": {"type": "integer", "minimum": 1},
    },
}
CARD = {
    "type": "object",
    "additionalProperties": False,
    "required": ["slug", "version", "title", "body", "applicability", "review_note"],
    "properties": {
        "slug": VERSION,
        "version": VERSION,
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "body": TEXT,
        "applicability": TEXT,
        "review_note": TEXT,
    },
}
EXERCISE = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "slug",
        "version",
        "answer_version",
        "kind",
        "question",
        "hint",
        "options",
        "answer",
        "explanation",
        "source_refs",
        "review_note",
    ],
    "properties": {
        "slug": VERSION,
        "version": VERSION,
        "answer_version": VERSION,
        "kind": {"enum": ["flow_order", "error_prediction", "code_location"]},
        "question": TEXT,
        "hint": TEXT,
        "options": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "required": ["id", "label"],
                "additionalProperties": False,
                "properties": {"id": VERSION, "label": TEXT},
            },
        },
        "answer": {},
        "explanation": TEXT,
        "source_refs": {"type": "array", "minItems": 1, "maxItems": 20, "items": REF},
        "review_note": TEXT,
    },
}
BUNDLE = {
    "type": "object",
    "additionalProperties": False,
    "required": ["example_version", "files", "exercises"],
    "properties": {
        "example_version": VERSION,
        "files": {
            "type": "object",
            "minProperties": 1,
            "maxProperties": 100,
            "additionalProperties": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        },
        "exercises": {
            "type": "array",
            "minItems": 3,
            "maxItems": 30,
            "items": EXERCISE,
        },
    },
}


def content_digest(value: Any) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def read_content(path: Path, schema: dict[str, Any]) -> Any:
    if path.is_symlink() or path.stat().st_size > 262144:
        raise ValueError("教学内容文件不符合边界。")
    value = json.loads(path.read_text(encoding="utf-8"))
    try:
        Draft202012Validator(schema).validate(value)
    except ValidationError:
        raise ValueError("教学内容结构无效。") from None
    return value


def load_content(root: Path = CONTENT_ROOT) -> tuple[int, int]:
    from apps.learning.services import validate_answer

    cards: list[dict[str, Any]] = []
    bundles = []
    for path in sorted((root / "knowledge").glob("*.json")):
        cards.extend(
            read_content(path, {"type": "array", "maxItems": 30, "items": CARD})
        )
    for path in sorted((root / "exercises").glob("*.json")):
        bundles.append(read_content(path, BUNDLE))
    if not cards or not bundles or len(cards) > 100 or len(bundles) > 20:
        raise ValueError("教学内容缺失或超过限制。")
    with transaction.atomic():
        for card in cards:
            record, _ = KnowledgeCard.objects.get_or_create(
                slug=card["slug"],
                version=card["version"],
                defaults={**card, "content_digest": content_digest(card)},
            )
            if record.content_digest != content_digest(card):
                raise ValueError("知识卡片同版本内容漂移，必须发布新版本。")
        count = 0
        for bundle in bundles:
            signature = {"version": bundle["example_version"], "files": bundle["files"]}
            for path in signature["files"]:
                if (
                    path.startswith("/")
                    or "\\" in path
                    or ":" in path
                    or any(part in {"", ".", ".."} for part in path.split("/"))
                ):
                    raise ValueError("示例引用路径不符合约定。")
            example, _ = TeachingExample.objects.get_or_create(
                version=signature["version"],
                defaults={
                    "files": signature["files"],
                    "content_digest": content_digest(signature),
                },
            )
            if example.content_digest != content_digest(signature):
                raise ValueError("示例同版本摘要漂移，必须重新核对并发布新版本。")
            for item in bundle["exercises"]:
                if len({option["id"] for option in item["options"]}) != len(
                    item["options"]
                ):
                    raise ValueError("题目选项标识重复。")
                try:
                    validate_answer(item["kind"], item["options"], item["answer"])
                except ApiProblem:
                    raise ValueError("教学答案格式无效。") from None
                for ref in item["source_refs"]:
                    if (
                        ref["file_path"] not in example.files
                        or ref["start_line"] > ref["end_line"]
                    ):
                        raise ValueError("教学引用未绑定示例文件。")
                exercise, _ = Exercise.objects.get_or_create(
                    slug=item["slug"],
                    version=item["version"],
                    defaults={
                        **item,
                        "example": example,
                        "content_digest": content_digest(
                            {**item, "example": example.version}
                        ),
                    },
                )
                if exercise.content_digest != content_digest(
                    {**item, "example": example.version}
                ):
                    raise ValueError("题目同版本内容漂移，必须发布新版本。")
                count += 1
        from apps.learning.paths.publication import load_curricula

        load_curricula(root)
    return len(cards), count
