"""直接构造升级前已存记录；测试不得通过退役业务入口写入夹具。"""

import uuid
from pathlib import Path
from typing import Any

from apps.learning.content import (
    BUNDLE,
    CONTENT_ROOT,
    content_digest,
    load_cards_only,
    read_content,
)
from apps.learning.models import (
    Exercise,
    ExerciseAttempt,
    KnowledgeCurriculum,
    TeachingExample,
)
from apps.learning.paths.publication import CURRICULUM, validate_definition


def seed_history(root: Path = CONTENT_ROOT) -> None:
    load_cards_only(root)
    for path in sorted((root / "exercises").glob("*.json")):
        bundle = read_content(path, BUNDLE)
        signature = {"version": bundle["example_version"], "files": bundle["files"]}
        example, _ = TeachingExample.objects.get_or_create(
            version=signature["version"],
            defaults={
                "files": signature["files"],
                "content_digest": content_digest(signature),
            },
        )
        for item in bundle["exercises"]:
            Exercise.objects.get_or_create(
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
    for path in sorted((root / "paths").glob("*.json")):
        value = read_content(path, CURRICULUM)
        validate_definition(value)
        KnowledgeCurriculum.objects.get_or_create(
            slug=value["slug"],
            version=value["version"],
            defaults={
                "title": value["title"],
                "definition": value,
                "content_digest": content_digest(value),
            },
        )


def historical_attempt(
    values: dict[str, Any], *, correct: bool = True
) -> ExerciseAttempt:
    exercise = Exercise.objects.get(pk=values["exercise_id"])
    return ExerciseAttempt.objects.create(
        exercise=exercise,
        snapshot_id=values["snapshot_id"],
        analysis_id=values["analysis_id"],
        endpoint_index=values["endpoint_index"],
        idempotency_key=uuid.uuid4(),
        request_digest="0" * 64,
        answer=values["answer"],
        hint_used=values["hint_used"],
        correct=correct,
        feedback={
            "expected_answer": exercise.answer,
            "explanation": exercise.explanation,
            "source_refs": [
                {"snapshot_id": str(values["snapshot_id"]), **ref}
                for ref in exercise.source_refs
            ],
        },
        previous_attempt_id=values.get("previous_attempt_id"),
    )
