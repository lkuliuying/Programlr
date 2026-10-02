"""按版本原子发布可信知识配置；任何校验失败都保留原内容。"""

from pathlib import Path
from typing import Any

from django.db import transaction

from apps.learning.content import TEXT, VERSION, content_digest, read_content
from apps.learning.models import KnowledgeCard, KnowledgeCurriculum, TeachingExample
from apps.learning.paths.graph import build_graph

NODE = {
    "type": "object",
    "additionalProperties": False,
    "required": ["slug", "card_version"],
    "properties": {"slug": VERSION, "card_version": VERSION},
}
EDGE = {
    "type": "object",
    "additionalProperties": False,
    "required": ["prerequisite", "dependent"],
    "properties": {"prerequisite": VERSION, "dependent": VERSION},
}
CURRICULUM = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "slug",
        "version",
        "title",
        "example_version",
        "review_note",
        "nodes",
        "edges",
        "goals",
    ],
    "properties": {
        "slug": VERSION,
        "version": VERSION,
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "example_version": VERSION,
        "review_note": TEXT,
        "nodes": {"type": "array", "minItems": 1, "maxItems": 100, "items": NODE},
        "edges": {"type": "array", "maxItems": 400, "items": EDGE},
        "goals": {
            "type": "object",
            "minProperties": 1,
            "maxProperties": 20,
            "propertyNames": {"pattern": "^[a-z0-9][a-z0-9-]{0,79}$"},
            "additionalProperties": {
                "type": "array",
                "minItems": 1,
                "maxItems": 100,
                "items": VERSION,
            },
        },
    },
}


def validate_definition(value: dict[str, Any]) -> None:
    graph = build_graph([node["slug"] for node in value["nodes"]], value["edges"])
    for targets in value["goals"].values():
        graph.order_for(targets)
    if not TeachingExample.objects.filter(pk=value["example_version"]).exists():
        raise ValueError("先修配置引用了未发布示例。")
    available = set(KnowledgeCard.objects.values_list("slug", "version"))
    if any(
        (node["slug"], node["card_version"]) not in available for node in value["nodes"]
    ):
        raise ValueError("先修配置引用了未发布知识卡片版本。")


def load_curricula(root: Path) -> int:
    definitions = [
        read_content(path, CURRICULUM)
        for path in sorted((root / "paths").glob("*.json"))
    ]
    if not 1 <= len(definitions) <= 20:
        raise ValueError("知识先修配置缺失或超过上限。")
    with transaction.atomic():
        for value in definitions:
            validate_definition(value)
            record, _ = KnowledgeCurriculum.objects.get_or_create(
                slug=value["slug"],
                version=value["version"],
                defaults={
                    "title": value["title"],
                    "definition": value,
                    "content_digest": content_digest(value),
                },
            )
            if record.content_digest != content_digest(value):
                raise ValueError("先修配置同版本内容漂移，必须发布新版本。")
    return len(definitions)
