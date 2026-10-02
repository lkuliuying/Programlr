import { requestJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import type {
  ComparisonImpact,
  Impact,
  ImpactSide,
  SnapshotComparison,
} from '../../../shared/api/generated/schema';
import {
  parseDiagnostic,
  parseGraphEdge,
  parseGraphNode,
} from './analysis-api';
import { parseDecision } from './review-api';

export function parseImpact(
  value: unknown,
  snapshot: string,
  analysis: string,
  candidates: boolean,
): Impact {
  const item = v.object(value);
  const result: Impact = {
    analysis_id: v.uuid(item.analysis_id),
    snapshot_id: v.uuid(item.snapshot_id),
    graph_version: v.oneOf(item.graph_version, [
      'analysis-graph/1.0.0',
      'analysis-graph/2.0.0',
    ]),
    rule_version: v.text(item.rule_version, 80),
    include_candidates: v.boolean(item.include_candidates),
    max_nodes: v.integer(item.max_nodes, 1, 1000),
    max_edges: v.integer(item.max_edges, 1, 2000),
    starts: v.list(item.starts, v.uuid, 1000),
    nodes: v.list(item.nodes, (x) => parseGraphNode(x, snapshot), 1000),
    edges: v.list(item.edges, (x) => parseGraphEdge(x, snapshot), 2000),
    relation_reviews: v.list(item.relation_reviews, parseDecision, 2000),
    results: v.list(
      item.results,
      (x) => {
        const e = v.object(x);
        return {
          node: parseGraphNode(e.node, snapshot),
          path_node_ids: v.list(e.path_node_ids, v.uuid, 1000),
          path_edge_ids: v.list(e.path_edge_ids, v.uuid, 1000),
          via_candidate: v.boolean(e.via_candidate),
        };
      },
      1000,
    ),
    visited_nodes: v.integer(item.visited_nodes, 0, 1000),
    visited_edges: v.integer(item.visited_edges, 0, 2000),
    truncated: v.boolean(item.truncated),
    truncation_reasons: v.list(
      item.truncation_reasons,
      (x) => v.oneOf(x, ['max_nodes', 'max_edges']),
      2,
    ),
    unmapped_files: v.list(item.unmapped_files, v.sourcePath),
    uncovered_files: v.list(item.uncovered_files, v.sourcePath),
    limitations: v.list(item.limitations, (x) => v.text(x)),
    diagnostics: v.list(
      item.diagnostics,
      (x) => parseDiagnostic(x, snapshot),
      20000,
    ),
    diagnostics_url: v.text(item.diagnostics_url),
  };
  const nodes = new Map(result.nodes.map((x) => [x.id, x])),
    edges = new Map(result.edges.map((x) => [x.id, x])),
    decisions = new Map(
      result.relation_reviews.map((x) => [`${x.request_id}:${x.target_id}`, x]),
    );
  if (
    result.snapshot_id !== snapshot ||
    result.analysis_id !== analysis ||
    result.include_candidates !== candidates ||
    result.diagnostics_url !== `/api/v1/analyses/${analysis}/diagnostics/` ||
    result.visited_nodes !== nodes.size ||
    nodes.size !== result.nodes.length ||
    result.visited_edges !== edges.size ||
    edges.size !== result.edges.length ||
    nodes.size > result.max_nodes ||
    edges.size > result.max_edges ||
    result.truncated !== !!result.truncation_reasons.length ||
    result.starts.some((x) => !nodes.has(x)) ||
    decisions.size !== result.relation_reviews.length ||
    result.relation_reviews.length !==
      result.edges.filter((x) => x.relation === 'candidate_match').length
  )
    return v.invalid();
  for (const edge of result.edges) {
    if (
      !nodes.has(edge.source_id) ||
      !nodes.has(edge.target_id) ||
      !edge.evidence.length
    )
      return v.invalid();
    if (edge.relation === 'candidate_match') {
      const choice = decisions.get(`${edge.source_id}:${edge.target_id}`);
      if (
        !choice ||
        choice.decision === 'excluded' ||
        (!candidates && choice.decision === 'undecided')
      )
        return v.invalid();
    }
  }
  if (
    new Set(result.results.map((x) => x.node.id)).size !== result.results.length
  )
    return v.invalid();
  for (const entry of result.results) {
    if (
      !['endpoint', 'frontend_function', 'frontend_request'].includes(
        entry.node.kind,
      ) ||
      JSON.stringify(entry.node) !== JSON.stringify(nodes.get(entry.node.id)) ||
      entry.path_node_ids.length !== entry.path_edge_ids.length + 1 ||
      entry.path_node_ids[0] !== entry.node.id ||
      !result.starts.includes(entry.path_node_ids.at(-1)!)
    )
      return v.invalid();
    let candidatePath = false;
    entry.path_edge_ids.forEach((id, i) => {
      const edge = edges.get(id);
      if (
        !edge ||
        edge.source_id !== entry.path_node_ids[i] ||
        edge.target_id !== entry.path_node_ids[i + 1]
      )
        return v.invalid();
      if (
        edge.relation === 'candidate_match' &&
        decisions.get(`${edge.source_id}:${edge.target_id}`)?.decision ===
          'undecided'
      )
        candidatePath = true;
    });
    if (entry.via_candidate !== candidatePath) return v.invalid();
  }
  return result;
}
export const getImpact = (
  snapshot: string,
  analysis: string,
  node: string,
  candidates: boolean,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/analyses/${analysis}/impact/?node_id=${node}&include_candidates=${candidates}`,
    (value) => parseImpact(value, snapshot, analysis, candidates),
    { signal },
  );
export function parseComparisonImpact(
  value: unknown,
  comparison: SnapshotComparison,
  change: string | null,
  candidates: boolean,
): ComparisonImpact {
  const item = v.object(value);
  function side(
    value: unknown,
    snapshot: string,
    analysis: string | null,
  ): ImpactSide {
    const e = v.object(value),
      result = {
        snapshot_id: v.uuid(e.snapshot_id),
        analysis_id: v.nullable(e.analysis_id, v.uuid),
        available: v.boolean(e.available),
        reason: v.nullable(e.reason, (x) => v.text(x)),
        changed_files: v.list(e.changed_files, v.sourcePath),
        impact: v.nullable(e.impact, (x) =>
          analysis
            ? parseImpact(x, snapshot, analysis, candidates)
            : v.invalid(),
        ),
      };
    if (
      result.snapshot_id !== snapshot ||
      result.analysis_id !== analysis ||
      result.available !== (result.impact !== null) ||
      result.available === (result.reason !== null)
    )
      return v.invalid();
    return result;
  }
  const result = {
    comparison_id: v.uuid(item.comparison_id),
    change_id: v.nullable(item.change_id, v.uuid),
    include_candidates: v.boolean(item.include_candidates),
    base: side(
      item.base,
      comparison.base_snapshot_id,
      comparison.base_analysis_id,
    ),
    target: side(
      item.target,
      comparison.target_snapshot_id,
      comparison.target_analysis_id,
    ),
    limitations: v.list(item.limitations, (x) => v.text(x)),
  };
  return result.comparison_id === comparison.id &&
    result.change_id === change &&
    result.include_candidates === candidates
    ? result
    : v.invalid();
}
export const getComparisonImpact = (
  comparison: SnapshotComparison,
  change: string | null,
  candidates: boolean,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/snapshot-comparisons/${comparison.id}/impact/?include_candidates=${candidates}${change ? `&change_id=${change}` : ''}`,
    (value) => parseComparisonImpact(value, comparison, change, candidates),
    { signal },
  );
