"""载入可信的版本化教学内容；相同版本的内容漂移不能静默覆盖。"""

import json
from pathlib import Path
from typing import Any

from django.db import transaction
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]

from apps.learning.models import KnowledgeCard

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
    """兼容旧导入名，只发布知识卡片，不再发布退役内容。"""
    return load_cards_only(root), 0


def load_cards_only(root: Path = CONTENT_ROOT) -> int:
    """发布可信知识卡片，不创建课程、进度、练习或实验记录。"""
    cards: list[dict[str, Any]] = []
    for path in sorted((root / "knowledge").glob("*.json")):
        cards.extend(
            read_content(path, {"type": "array", "maxItems": 100, "items": CARD})
        )
    if not cards or len(cards) > 100:
        raise ValueError("知识内容缺失或超过限制。")
    with transaction.atomic():
        for card in cards:
            record, _ = KnowledgeCard.objects.get_or_create(
                slug=card["slug"],
                version=card["version"],
                defaults={**card, "content_digest": content_digest(card)},
            )
            if record.content_digest != content_digest(card):
                raise ValueError("知识卡片同版本内容漂移，必须发布新版本。")
    return len(cards)
