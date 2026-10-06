"""读取旧课程的精确版本进度，新增标记入口已退役。"""

from typing import Any

from apps.learning.models import (
    CurriculumCardProgress,
    KnowledgeCard,
    KnowledgeCurriculum,
)
from common.errors import ApiProblem
from common.retirement import retired_feature


def curriculum_cards(curriculum: KnowledgeCurriculum) -> list[KnowledgeCard]:
    nodes = curriculum.definition.get("nodes")
    if not isinstance(nodes, list):
        raise ApiProblem(
            409, "LEARNING_CONTENT_UNAVAILABLE", "课程绑定的卡片定义不可用。"
        )
    try:
        identities = [(node["slug"], node["card_version"]) for node in nodes]
        if len(set(identities)) != len(identities):
            raise ValueError
        available = {
            (card.slug, card.version): card
            for card in KnowledgeCard.objects.filter(
                slug__in=[slug for slug, _ in identities]
            )
        }
        return [available[identity] for identity in identities]
    except (KeyError, TypeError, ValueError):
        raise ApiProblem(
            409, "LEARNING_CONTENT_UNAVAILABLE", "课程绑定的卡片版本不可用。"
        ) from None


def curriculum_progress(curriculum: KnowledgeCurriculum) -> dict[str, Any]:
    cards = curriculum_cards(curriculum)
    completed = set(
        CurriculumCardProgress.objects.filter(
            curriculum=curriculum, card__in=cards, completed=True
        ).values_list("card_id", flat=True)
    )
    return {
        "curriculum_id": curriculum.pk,
        "version": curriculum.version,
        "completed_count": len(completed),
        "total_count": len(cards),
        "cards": [
            {
                "card_id": card.pk,
                "slug": card.slug,
                "version": card.version,
                "title": card.title,
                "completed": card.pk in completed,
            }
            for card in cards
        ],
    }


def mark_card(curriculum_id: Any, card_id: Any, completed: bool) -> dict[str, Any]:
    retired_feature("course_progress")
