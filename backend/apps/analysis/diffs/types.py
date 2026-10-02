from typing import Literal, TypedDict

from apps.analysis.types import Endpoint, Evidence, GraphData, SourceRef

COMPARISON_VERSION = "snapshot-comparison/1.0.0"
MAX_FILES = 10_000
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_CHANGED_BYTES = 32 * 1024 * 1024
MAX_FILE_LINES = 20_000
MAX_INPUT_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_FILE_DIFF_BYTES = 512 * 1024
TIMEOUT_SECONDS = 60
FILE_CHANGE_TYPES = ("added", "deleted", "modified", "unchanged")
SEMANTIC_CHANGE_TYPES = (*FILE_CHANGE_TYPES, "ambiguous")
FileChangeType = Literal["added", "deleted", "modified", "unchanged"]
SemanticChangeType = Literal["added", "deleted", "modified", "unchanged", "ambiguous"]


class FileInput(TypedDict):
    file_path: str
    base_ref: SourceRef | None
    target_ref: SourceRef | None
    base_sha256: str | None
    target_sha256: str | None
    base_content: str | None
    target_content: str | None


class FileChange(TypedDict):
    id: str
    file_path: str
    change_type: FileChangeType
    base_ref: SourceRef | None
    target_ref: SourceRef | None
    base_sha256: str | None
    target_sha256: str | None
    diff: str
    base_ranges: list[SourceRef]
    target_ranges: list[SourceRef]


class FileSummary(TypedDict):
    added: int
    deleted: int
    modified: int
    unchanged: int


class AnalysisVersion(TypedDict):
    analysis_id: str
    snapshot_id: str
    root_urlconf: str
    rule_version: str
    graph_version: str | None
    frontend_rule_version: str | None
    association_rule_version: str | None


class AnalysisInput(TypedDict):
    version: AnalysisVersion
    graph: GraphData | None
    endpoints: list[Endpoint]


class EndpointChange(TypedDict):
    method: str
    path: str
    path_kind: str
    change_type: SemanticChangeType
    base_indices: list[int]
    target_indices: list[int]
    changed_fields: list[str]
    base_evidence: list[Evidence]
    target_evidence: list[Evidence]


class RelationChange(TypedDict):
    relation: str
    source_name: str
    target_name: str
    change_type: SemanticChangeType
    base_edge_ids: list[str]
    target_edge_ids: list[str]
    base_evidence: list[Evidence]
    target_evidence: list[Evidence]


class SavedEvidence(TypedDict):
    explanation_id: str
    preview_id: str
    analysis_id: str
    endpoint_index: int
    source_refs: list[SourceRef]
    valid: bool


class ReferenceApplicability(TypedDict):
    source_ref: SourceRef
    target_ref: SourceRef | None
    applicability: Literal["unchanged", "review", "deleted", "unknown"]


class ExplanationApplicability(TypedDict):
    explanation_id: str
    preview_id: str
    analysis_id: str
    endpoint_index: int
    references: list[ReferenceApplicability]
    warning: str | None


class ComparisonInput(TypedDict):
    comparison_id: str
    base_snapshot_id: str
    target_snapshot_id: str
    files: list[FileInput]
    base_analysis: AnalysisInput | None
    target_analysis: AnalysisInput | None
    evidence: list[SavedEvidence]


class ComparisonData(TypedDict):
    comparison_version: str
    summary: FileSummary
    files: list[FileChange]
    comparability: Literal["comparable", "files_only", "incomparable"]
    comparison_notes: list[str]
    base_version: AnalysisVersion | None
    target_version: AnalysisVersion | None
    interfaces: list[EndpointChange]
    relations: list[RelationChange]
    evidence: list[ExplanationApplicability]


class ComparisonFailed(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__("快照对比未能生成可靠结果。")
