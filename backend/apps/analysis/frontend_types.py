"""前端解析与关联的内部协议类型。"""

from typing import Literal, TypedDict

from apps.analysis.types import Diagnostic, Evidence, SourceRef

PROTOCOL_VERSION = "typescript-analysis/1.0.0"
FRONTEND_RULE_VERSION = "typescript-react/1.1.0"
ASSOCIATION_RULE_VERSION = "method-path/1.0.0"


class FrontendFunction(TypedDict):
    id: str
    name: str
    source_ref: SourceRef
    entry_points: list[Evidence]


class FrontendRequest(TypedDict):
    id: str
    owner_id: str | None
    method: str | None
    original_path: str | None
    path: str | None
    resolution: Literal["static", "unknown_base", "dynamic", "external", "unsupported"]
    source_ref: SourceRef
    evidence: list[Evidence]


class FrontendRelation(TypedDict):
    source_id: str
    target_id: str
    relation: Literal[
        "direct_call", "contains_function", "contains_request", "callback_binding"
    ]
    evidence: list[Evidence]


class FrontendCoverage(TypedDict):
    source_files: int
    parsed_files: int
    syntax_failed_files: int
    function_count: int
    request_count: int
    complete: bool
    limitations: list[str]


class FrontendResult(TypedDict):
    protocol_version: str
    rule_version: str
    snapshot_id: str
    functions: list[FrontendFunction]
    requests: list[FrontendRequest]
    relations: list[FrontendRelation]
    diagnostics: list[Diagnostic]
    coverage: FrontendCoverage


class RequestMatch(TypedDict):
    request_id: str
    status: Literal["confirmed", "candidate", "unmatched"]
    reason: str
    endpoint_indices: list[int]
    evidence: list[Evidence]


class FrontendAnalysis(TypedDict):
    parser: FrontendResult
    association_rule_version: str
    matches: list[RequestMatch]
