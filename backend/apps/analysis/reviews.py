"""追加人工候选决定，不改写静态图或讲解所用证据。"""

import hashlib
import json
import uuid
from typing import Literal, TypedDict

from django.db import transaction

from apps.analysis.models import Analysis, RelationReview, RelationReviewState
from apps.analysis.services import read_graph
from apps.analysis.types import GraphData
from common.errors import ApiProblem, Conflict

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
    digest = hashlib.sha256(
        json.dumps(
            {
                "analysis_id": str(analysis.pk),
                "request_id": str(request_id),
                "target_id": str(target_id),
                "action": action,
                "expected_revision": expected_revision,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    with transaction.atomic():
        # 首次请求状态尚不存在时也使用同一归属锁，避免并发创建与幂等重放竞争。
        Analysis.objects.select_for_update().get(pk=analysis.pk)
        previous = RelationReview.objects.filter(
            analysis=analysis, idempotency_key=key
        ).first()
        if previous is not None:
            if previous.request_digest != digest:
                raise Conflict()
            return previous, current_review(analysis, request_id), False
        candidates = request_candidates(analysis, request_id)
        if str(target_id) not in candidates:
            raise ApiProblem(
                409, "RELATION_NOT_CANDIDATE", "只能处理当前分析已有的请求—接口候选。"
            )
        record = RelationReviewState.objects.filter(
            analysis=analysis, request_id=request_id
        ).first()
        state = state_data(analysis, request_id, record)
        if expected_revision != state["revision"]:
            raise ApiProblem(
                409,
                "RELATION_REVISION_CONFLICT",
                "该请求的人工决定已变更，请重新读取后判断。",
                {
                    "current_revision": state["revision"],
                },
            )
        if action not in {"confirm", "exclude", "reset"}:
            raise ApiProblem(400, "VALIDATION_ERROR", "人工决定动作无效。")
        excluded = set(state["excluded_target_ids"])
        confirmed = state["confirmed_target_id"]
        if action == "confirm":
            confirmed = str(target_id)
            excluded.discard(str(target_id))
        elif action == "exclude":
            excluded.add(str(target_id))
            if confirmed == str(target_id):
                confirmed = None
        else:
            excluded.discard(str(target_id))
            if confirmed == str(target_id):
                confirmed = None
        if record is None:
            record = RelationReviewState(analysis=analysis, request_id=request_id)
        record.revision = state["revision"] + 1
        record.confirmed_target_id = uuid.UUID(confirmed) if confirmed else None
        record.excluded_target_ids = sorted(excluded)
        record.save()
        review = RelationReview.objects.create(
            analysis=analysis,
            request_id=request_id,
            target_id=target_id,
            action=action,
            revision=record.revision,
            idempotency_key=key,
            request_digest=digest,
        )
        return review, state_data(analysis, request_id, record), True
