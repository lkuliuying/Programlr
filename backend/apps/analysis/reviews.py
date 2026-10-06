"""读取历史人工候选决定；写入入口已退役。"""

import uuid
from typing import Literal, TypedDict

from apps.analysis.models import Analysis, RelationReview, RelationReviewState
from apps.analysis.services import read_graph
from apps.analysis.types import GraphData
from common.errors import ApiProblem
from common.retirement import retired_feature

ReviewAction = Literal["confirm", "exclude", "reset"]


class ReviewStateData(TypedDict):
    analysis_id: str
    request_id: str
    revision: int
    confirmed_target_id: str | None
    excluded_target_ids: list[str]


class ReviewDecision(TypedDict):
    request_id: str
    target_id: str
    revision: int
    decision: Literal["confirmed", "excluded", "undecided"]


def request_candidates(analysis: Analysis, request_id: uuid.UUID) -> set[str]:
    graph, _ = read_graph(analysis)
    if not any(
        node["id"] == str(request_id) and node["kind"] == "frontend_request"
        for node in graph["nodes"]
    ):
        raise ApiProblem(404, "RESOURCE_NOT_FOUND", "当前分析中不存在该前端请求。")
    return {
        edge["target_id"]
        for edge in graph["edges"]
        if edge["source_id"] == str(request_id)
        and edge["relation"] == "candidate_match"
    }


def state_data(
    analysis: Analysis, request_id: uuid.UUID, record: RelationReviewState | None
) -> ReviewStateData:
    if record is None:
        return {
            "analysis_id": str(analysis.pk),
            "request_id": str(request_id),
            "revision": 0,
            "confirmed_target_id": None,
            "excluded_target_ids": [],
        }
    excluded = record.excluded_target_ids
    try:
        valid = (
            isinstance(excluded, list)
            and len(excluded) <= 10000
            and all(
                isinstance(value, str) and str(uuid.UUID(value)) == value
                for value in excluded
            )
            and len(set(excluded)) == len(excluded)
            and str(record.confirmed_target_id) not in excluded
            and record.revision > 0
        )
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ApiProblem(500, "INTERNAL_ERROR", "保存的人工决定无法通过完整性校验。")
    return {
        "analysis_id": str(analysis.pk),
        "request_id": str(request_id),
        "revision": record.revision,
        "confirmed_target_id": str(record.confirmed_target_id)
        if record.confirmed_target_id
        else None,
        "excluded_target_ids": excluded,
    }


def current_review(analysis: Analysis, request_id: uuid.UUID) -> ReviewStateData:
    return state_data(
        analysis,
        request_id,
        RelationReviewState.objects.filter(
            analysis=analysis, request_id=request_id
        ).first(),
    )


def decisions(analysis: Analysis, pairs: list[tuple[str, str]]) -> list[ReviewDecision]:
    records = {
        str(record.request_id): record
        for record in RelationReviewState.objects.filter(
            analysis=analysis, request_id__in={request for request, _ in pairs}
        )
    }
    states = {
        request: state_data(analysis, uuid.UUID(request), records.get(request))
        for request in {request for request, _ in pairs}
    }
    return [decision(states[request], target) for request, target in pairs]


def decision(state: ReviewStateData, target_id: str) -> ReviewDecision:
    return {
        "request_id": state["request_id"],
        "target_id": target_id,
        "revision": state["revision"],
        "decision": "confirmed"
        if state["confirmed_target_id"] == target_id
        else "excluded"
        if target_id in state["excluded_target_ids"]
        else "undecided",
    }


def graph_decisions(analysis: Analysis, graph: GraphData) -> list[ReviewDecision]:
    return decisions(
        analysis,
        [
            (edge["source_id"], edge["target_id"])
            for edge in graph["edges"]
            if edge["relation"] == "candidate_match"
        ],
    )


def submit_review(
    analysis: Analysis,
    key: uuid.UUID,
    request_id: uuid.UUID,
    target_id: uuid.UUID,
    action: ReviewAction,
    expected_revision: int,
) -> tuple[RelationReview, ReviewStateData, bool]:
    retired_feature("relation_reviews")
