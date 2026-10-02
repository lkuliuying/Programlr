from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

RULE_VERSION = "python-drf/1.1.0"
MAX_AST_NODES = 500_000
MAX_RESULTS = 10_000
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
PARSER_TIMEOUT_SECONDS = 60
GRAPH_VERSION = "analysis-graph/2.0.0"
LEGACY_GRAPH_VERSION = "analysis-graph/1.0.0"
MAX_GRAPH_NODES = 40_000
MAX_GRAPH_EDGES = 30_000
MAX_GRAPH_BYTES = 32 * 1024 * 1024
DEFAULT_GRAPH_NODES = 200
DEFAULT_GRAPH_EDGES = 400
MAX_QUERY_NODES = 1_000
MAX_QUERY_EDGES = 2_000


@dataclass(frozen=True)
class Source:
    file_path: str
    content: str


class SourceRef(TypedDict):
    snapshot_id: str
    file_path: str
    start_line: int
    end_line: int


class Symbol(TypedDict):
    name: str
    source_ref: SourceRef


class Evidence(TypedDict):
    kind: Literal["source_fact", "static_inference", "framework_rule"]
    rule: str
    source_ref: SourceRef | None


class Endpoint(TypedDict):
    method: str
    path: str
    path_kind: Literal["django_path", "router_regex"]
    action: str
    view: Symbol | None
    serializer: Symbol | None
    model: Symbol | None
    evidence: list[Evidence]


class Diagnostic(TypedDict):
    code: str
    message: str
    severity: Literal["warning"]
    source_ref: SourceRef | None


class Coverage(TypedDict):
    python_files: int
    parsed_files: int
    syntax_failed_files: int
    skipped_files: int
    endpoint_count: int
    diagnostic_count: int
    complete: bool
    limitations: list[str]


class AnalysisResult(TypedDict):
    rule_version: str
    coverage: Coverage
    endpoints: list[Endpoint]
    diagnostics: list[Diagnostic]


class GraphEndpoint(TypedDict):
    index: int
    method: str
    path: str
    path_kind: Literal["django_path", "router_regex"]
    action: str
    is_candidate: bool


GraphSymbolKind = Literal["view", "serializer", "model"]
GraphRelation = Literal[
    "route_view",
    "serializer_class",
    "meta_model",
    "direct_call",
    "contains_function",
    "contains_request",
    "callback_binding",
    "method_path_match",
    "candidate_match",
]


class GraphRequest(TypedDict):
    method: str | None
    original_path: str | None
    path: str | None
    status: Literal["confirmed", "candidate", "unmatched"]
    reason: str


class GraphNode(TypedDict):
    id: str
    kind: Literal[
        "endpoint",
        "view",
        "serializer",
        "model",
        "frontend_function",
        "frontend_request",
    ]
    name: str
    source_ref: SourceRef | None
    evidence: list[Evidence]
    endpoint: GraphEndpoint | None
    request: NotRequired[GraphRequest]


class GraphEdge(TypedDict):
    id: str
    source_id: str
    target_id: str
    relation: GraphRelation
    evidence: list[Evidence]


class GraphData(TypedDict):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


@dataclass(frozen=True)
class GraphQuery:
    root_node_id: str | None = None
    algorithm: Literal["bfs", "dfs"] = "bfs"
    max_nodes: int = DEFAULT_GRAPH_NODES
    max_edges: int = DEFAULT_GRAPH_EDGES
    endpoint_index: int | None = None


class GraphSelection(GraphData):
    graph_version: NotRequired[str]
    total_nodes: int
    total_edges: int
    returned_nodes: int
    returned_edges: int
    truncated: bool
    truncation_reasons: list[str]


class AnalysisFailed(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__("静态分析未能生成可靠结果。")
