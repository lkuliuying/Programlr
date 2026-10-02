"""读取已发布先修图并计算目标闭包，不在 GET 中回填或调用模型。"""

from typing import Any

from apps.analysis.models import Analysis
from apps.learning.models import Exercise, KnowledgeCard, KnowledgeCurriculum
from apps.learning.paths.graph import build_graph
from apps.learning.services import applicability
from common.errors import ApiProblem


def learning_path(
    curriculum: KnowledgeCurriculum, analysis: Analysis, index: int, goal: str
) -> dict[str, Any]:
    definition = curriculum.definition
    if goal not in definition["goals"]:
        raise ApiProblem(400, "VALIDATION_ERROR", "所选学习目标不存在。")
    graph = build_graph(
        [node["slug"] for node in definition["nodes"]], definition["edges"]
    )
    exercise = (
        Exercise.objects.select_related("example")
        .filter(example_id=definition["example_version"])
        .first()
    )
    if exercise is None:
        raise ApiProblem(
            409, "LEARNING_CONTENT_UNAVAILABLE", "课程绑定的教学内容不可用。"
        )
    applies, reason = applicability(exercise, analysis, index)
    order = graph.order_for(definition["goals"][goal]) if applies else []
    versions = {node["slug"]: node["card_version"] for node in definition["nodes"]}
    cards = {
        (card.slug, card.version): card
        for card in KnowledgeCard.objects.filter(slug__in=order)
    }
    try:
        steps = [cards[(slug, versions[slug])] for slug in order]
    except KeyError:
        raise ApiProblem(
            409, "LEARNING_CONTENT_UNAVAILABLE", "课程绑定的卡片版本不可用。"
        ) from None
    return {
        "snapshot_id": analysis.snapshot_id,
        "analysis_id": analysis.pk,
        "endpoint_index": index,
        "curriculum": curriculum,
        "goal": goal,
        "targets": definition["goals"][goal],
        "order": order,
        "steps": steps,
        "applicable": applies,
        "applicability_reason": reason,
    }
