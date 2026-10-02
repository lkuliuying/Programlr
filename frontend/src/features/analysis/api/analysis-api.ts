import { requestJson, submitJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import type {
  Analysis,
  Coverage,
  Diagnostic,
  Endpoint,
  Evidence,
  FrontendSummary,
  Graph,
  GraphNode,
  GraphEdge,
  GraphRequest,
} from '../../../shared/api/generated/schema';
import { parseJob } from '../../jobs';
import { parseDecision } from './review-api';

const methods = [
  'GET',
  'POST',
  'PUT',
  'PATCH',
  'DELETE',
  'HEAD',
  'OPTIONS',
  'TRACE',
] as const;
const statuses = ['confirmed', 'candidate', 'unmatched'] as const;
export function parseEvidence(value: unknown, snapshot: string): Evidence {
  const item = v.object(value);
  return {
    kind: v.oneOf(item.kind, [
      'source_fact',
      'static_inference',
      'framework_rule',
    ]),
    rule: v.text(item.rule),
    source_ref: v.nullable(item.source_ref, (item) =>
      v.sourceRef(item, snapshot),
    ),
  };
}
function parseCoverage(value: unknown): Coverage {
  const item = v.object(value);
  return {
    python_files: v.integer(item.python_files),
    parsed_files: v.integer(item.parsed_files),
    syntax_failed_files: v.integer(item.syntax_failed_files),
    skipped_files: v.integer(item.skipped_files),
    endpoint_count: v.integer(item.endpoint_count),
    diagnostic_count: v.integer(item.diagnostic_count),
    complete: v.boolean(item.complete),
    limitations: v.list(item.limitations, (value) => v.text(value)),
  };
}
function parseFrontend(value: unknown): FrontendSummary {
  const item = v.object(value),
    coverage = v.object(item.coverage);
  return {
    protocol_version: v.text(item.protocol_version),
    rule_version: v.text(item.rule_version),
    association_rule_version: v.text(item.association_rule_version),
    confirmed: v.integer(item.confirmed),
    candidate: v.integer(item.candidate),
    unmatched: v.integer(item.unmatched),
    coverage: {
      source_files: v.integer(coverage.source_files),
      parsed_files: v.integer(coverage.parsed_files),
      syntax_failed_files: v.integer(coverage.syntax_failed_files),
      function_count: v.integer(coverage.function_count),
      request_count: v.integer(coverage.request_count),
      complete: v.boolean(coverage.complete),
      limitations: v.list(coverage.limitations, (value) => v.text(value)),
    },
  };
}
export function parseAnalysis(
  value: unknown,
  snapshotId: string,
  id: string,
): Analysis {
  const item = v.object(value);
  const result = {
    id: v.uuid(item.id),
    job_id: v.uuid(item.job_id),
    snapshot_id: v.uuid(item.snapshot_id),
    root_urlconf: v.sourcePath(item.root_urlconf),
    rule_version: v.text(item.rule_version),
    coverage: parseCoverage(item.coverage),
    frontend: v.nullable(item.frontend, parseFrontend),
    created_at: v.date(item.created_at),
  };
  return result.id === id && result.snapshot_id === snapshotId
    ? result
    : v.invalid();
}
export function parseEndpoint(value: unknown, snapshot: string): Endpoint {
  const item = v.object(value);
  const symbol = (value: unknown) => {
    const item = v.object(value);
    return {
      name: v.text(item.name),
      source_ref: v.sourceRef(item.source_ref, snapshot),
    };
  };
  return {
    index: v.integer(item.index),
    method: v.oneOf(item.method, methods),
    path: v.text(item.path),
    path_kind: v.oneOf(item.path_kind, ['django_path', 'router_regex']),
    action: v.text(item.action),
    view: v.nullable(item.view, symbol),
    serializer: v.nullable(item.serializer, symbol),
    model: v.nullable(item.model, symbol),
    evidence: v.list(item.evidence, (item) => parseEvidence(item, snapshot)),
    frontend_available: v.boolean(item.frontend_available),
    frontend_links: v.list(item.frontend_links, (value) => {
      const link = v.object(value);
      const relationReview = v.nullable(link.relation_review, parseDecision);
      if (
        (link.status === 'candidate') !== (relationReview !== null) ||
        (relationReview && relationReview.request_id !== link.request_id)
      )
        return v.invalid();
      return {
        request_id: v.uuid(link.request_id),
        method: v.nullable(link.method, (value) => v.oneOf(value, methods)),
        path: v.nullable(link.path, (value) => v.text(value)),
        status: v.oneOf(link.status, statuses),
        reason: v.text(link.reason),
        source_ref: v.sourceRef(link.source_ref, snapshot),
        relation_review: relationReview,
      };
    }),
  };
}
export function parseDiagnostic(value: unknown, snapshot: string): Diagnostic {
  const item = v.object(value);
  return {
    code: v.text(item.code),
    message: v.text(item.message),
    severity: v.oneOf(item.severity, ['warning']),
    source_ref: v.nullable(item.source_ref, (item) =>
      v.sourceRef(item, snapshot),
    ),
  };
}
export function parseGraph(
  value: unknown,
  snapshot: string,
  analysisId: string,
  endpoint: number | null,
): Graph {
  const item = v.object(value);
  const nodes = v.list(
    item.nodes,
    (value) => parseGraphNode(value, snapshot),
    1000,
  );
  const edges = v.list(
    item.edges,
    (value) => parseGraphEdge(value, snapshot),
    2000,
  );
  const result: Graph = {
    analysis_id: v.uuid(item.analysis_id),
    snapshot_id: v.uuid(item.snapshot_id),
    graph_version: v.oneOf(item.graph_version, [
      'analysis-graph/1.0.0',
      'analysis-graph/2.0.0',
    ]),
    rule_version: v.text(item.rule_version),
    root_node_id: v.nullable(item.root_node_id, v.uuid),
    endpoint_index: v.nullable(item.endpoint_index, (value) =>
      v.integer(value),
    ),
    algorithm: v.oneOf(item.algorithm, ['bfs', 'dfs']),
    nodes,
    edges,
    relation_reviews: v.list(item.relation_reviews, parseDecision, 2000),
    coverage: parseCoverage(item.coverage),
    diagnostics_url: v.text(item.diagnostics_url),
    total_nodes: v.integer(item.total_nodes),
    total_edges: v.integer(item.total_edges),
    returned_nodes: v.integer(item.returned_nodes),
    returned_edges: v.integer(item.returned_edges),
    truncated: v.boolean(item.truncated),
    truncation_reasons: v.list(item.truncation_reasons, (value) =>
      v.oneOf(value, ['max_nodes', 'max_edges']),
    ),
  };
  const ids = new Set(nodes.map((node) => node.id));
  if (
    result.analysis_id !== analysisId ||
    result.snapshot_id !== snapshot ||
    result.endpoint_index !== endpoint ||
    result.diagnostics_url !== `/api/v1/analyses/${analysisId}/diagnostics/` ||
    nodes.length !== result.returned_nodes ||
    edges.length !== result.returned_edges ||
    nodes.length > result.total_nodes ||
    edges.length > result.total_edges ||
    ids.size !== nodes.length ||
    new Set(edges.map((edge) => edge.id)).size !== edges.length ||
    result.relation_reviews.length !==
      edges.filter((edge) => edge.relation === 'candidate_match').length ||
    new Set(
      result.relation_reviews.map(
        (item) => `${item.request_id}:${item.target_id}`,
      ),
    ).size !== result.relation_reviews.length ||
    result.relation_reviews.some(
      (item) =>
        !edges.some(
          (edge) =>
            edge.relation === 'candidate_match' &&
            edge.source_id === item.request_id &&
            edge.target_id === item.target_id,
        ),
    ) ||
    edges.some(
      (edge) =>
        !ids.has(edge.source_id) ||
        !ids.has(edge.target_id) ||
        !edge.evidence.length,
    )
  )
    return v.invalid();
  return result;
}
export function parseGraphNode(value: unknown, snapshot: string): GraphNode {
  const request = (value: unknown): GraphRequest => {
    const item = v.object(value);
    return {
      method: v.nullable(item.method, (value) => v.oneOf(value, methods)),
      original_path: v.nullable(item.original_path, (value) => v.text(value)),
      path: v.nullable(item.path, (value) => v.text(value)),
      status: v.oneOf(item.status, statuses),
      reason: v.text(item.reason),
    };
  };
  const node = v.object(value);
  return {
    id: v.uuid(node.id),
    kind: v.oneOf(node.kind, [
      'endpoint',
      'view',
      'serializer',
      'model',
      'frontend_function',
      'frontend_request',
    ]),
    name: v.text(node.name),
    source_ref: v.nullable(node.source_ref, (value) =>
      v.sourceRef(value, snapshot),
    ),
    evidence: v.list(node.evidence, (value) => parseEvidence(value, snapshot)),
    request:
      node.request === undefined ? null : v.nullable(node.request, request),
    endpoint: v.nullable(node.endpoint, (value) => {
      const endpoint = v.object(value);
      return {
        index: v.integer(endpoint.index),
        method: v.oneOf(endpoint.method, methods),
        path: v.text(endpoint.path),
        path_kind: v.oneOf(endpoint.path_kind, ['django_path', 'router_regex']),
        action: v.text(endpoint.action),
        is_candidate: v.boolean(endpoint.is_candidate),
      };
    }),
  };
}
export function parseGraphEdge(value: unknown, snapshot: string): GraphEdge {
  const edge = v.object(value);
  return {
    id: v.uuid(edge.id),
    source_id: v.uuid(edge.source_id),
    target_id: v.uuid(edge.target_id),
    relation: v.oneOf(edge.relation, [
      'route_view',
      'serializer_class',
      'meta_model',
      'direct_call',
      'contains_function',
      'contains_request',
      'callback_binding',
      'method_path_match',
      'candidate_match',
    ] as const),
    evidence: v.list(edge.evidence, (value) => parseEvidence(value, snapshot)),
  };
}
export const getAnalysis = (
  snapshot: string,
  id: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/analyses/${id}/`,
    (value) => parseAnalysis(value, snapshot, id),
    { signal },
  );
export const listEndpoints = (
  snapshot: string,
  id: string,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/analyses/${id}/endpoints/?page=${page}&page_size=20`,
    (value) =>
      v.page(value, `/api/v1/analyses/${id}/endpoints/`, (value) =>
        parseEndpoint(value, snapshot),
      ),
    { signal },
  );
export const listDiagnostics = (
  snapshot: string,
  id: string,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/analyses/${id}/diagnostics/?page=${page}&page_size=20`,
    (value) =>
      v.page(value, `/api/v1/analyses/${id}/diagnostics/`, (value) =>
        parseDiagnostic(value, snapshot),
      ),
    { signal },
  );
export const getGraph = (
  snapshot: string,
  id: string,
  endpoint: number | null,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/analyses/${id}/graph/?max_nodes=100&max_edges=200${endpoint === null ? '' : `&endpoint_index=${endpoint}`}`,
    (value) => parseGraph(value, snapshot, id, endpoint),
    { signal },
  );
export const submitAnalysis = (
  snapshot: string,
  root: string,
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    `/api/v1/snapshots/${snapshot}/analyses/`,
    key,
    (value) => {
      const job = parseJob(value);
      return job.kind === 'analysis' && job.snapshot_id === snapshot
        ? job
        : v.invalid();
    },
    { root_urlconf: root },
    signal,
  );
