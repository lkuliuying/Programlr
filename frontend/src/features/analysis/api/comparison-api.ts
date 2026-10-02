import { requestJson, submitJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import type {
  AnalysisVersion,
  ComparisonFile,
  ComparisonFileDetail,
  ComparisonHistory,
  ComparisonInputRequest,
  FileSummary,
  SnapshotComparison,
} from '../../../shared/api/generated/schema';
import { parseJob } from '../../jobs';
import { parseEvidence } from './analysis-api';

const kinds = ['added', 'deleted', 'modified', 'unchanged'] as const;
const semanticKinds = [...kinds, 'ambiguous'] as const;
const hash = (value: unknown) => {
  const result = v.text(value, 64);
  return /^[a-f0-9]{64}$/.test(result) ? result : v.invalid();
};
export function parseSummary(value: unknown): FileSummary {
  const item = v.object(value);
  return {
    added: v.integer(item.added, 0, 10000),
    deleted: v.integer(item.deleted, 0, 10000),
    modified: v.integer(item.modified, 0, 10000),
    unchanged: v.integer(item.unchanged, 0, 10000),
  };
}
export function parseComparisonInput(
  value: unknown,
): Required<ComparisonInputRequest> {
  const item = v.object(value);
  if (
    Object.keys(item).some(
      (key) =>
        ![
          'base_snapshot_id',
          'target_snapshot_id',
          'base_analysis_id',
          'target_analysis_id',
        ].includes(key),
    )
  )
    return v.invalid();
  const result = {
    base_snapshot_id: v.uuid(item.base_snapshot_id),
    target_snapshot_id: v.uuid(item.target_snapshot_id),
    base_analysis_id: v.nullable(item.base_analysis_id, v.uuid),
    target_analysis_id: v.nullable(item.target_analysis_id, v.uuid),
  };
  return (result.base_analysis_id === null) ===
    (result.target_analysis_id === null)
    ? result
    : v.invalid();
}
function version(
  value: unknown,
  snapshot: string,
  analysis: string | null,
): AnalysisVersion | null {
  if (value === null) return analysis === null ? null : v.invalid();
  const item = v.object(value),
    result = {
      analysis_id: v.uuid(item.analysis_id),
      snapshot_id: v.uuid(item.snapshot_id),
      root_urlconf: v.sourcePath(item.root_urlconf),
      rule_version: v.text(item.rule_version, 80),
      graph_version: v.nullable(item.graph_version, (x) => v.text(x, 80)),
      frontend_rule_version: v.nullable(item.frontend_rule_version, (x) =>
        v.text(x, 80),
      ),
      association_rule_version: v.nullable(item.association_rule_version, (x) =>
        v.text(x, 80),
      ),
    };
  return result.snapshot_id === snapshot && result.analysis_id === analysis
    ? result
    : v.invalid();
}
export function parseComparison(
  value: unknown,
  id: string,
  project: string,
): SnapshotComparison {
  const item = v.object(value),
    input = parseComparisonInput({
      base_snapshot_id: item.base_snapshot_id,
      target_snapshot_id: item.target_snapshot_id,
      base_analysis_id: item.base_analysis_id,
      target_analysis_id: item.target_analysis_id,
    });
  const result: SnapshotComparison = {
    id: v.uuid(item.id),
    project_id: v.uuid(item.project_id),
    job_id: v.uuid(item.job_id),
    ...input,
    comparison_version: v.oneOf(item.comparison_version, [
      'snapshot-comparison/1.0.0',
    ]),
    created_at: v.date(item.created_at),
    summary: parseSummary(item.summary),
    comparability: v.oneOf(item.comparability, [
      'comparable',
      'files_only',
      'incomparable',
    ]),
    comparison_notes: v.list(item.comparison_notes, (x) => v.text(x), 20),
    base_version: version(
      item.base_version,
      input.base_snapshot_id,
      input.base_analysis_id,
    ),
    target_version: version(
      item.target_version,
      input.target_snapshot_id,
      input.target_analysis_id,
    ),
    interfaces: v.list(
      item.interfaces,
      (x) => {
        const e = v.object(x);
        return {
          method: v.text(e.method, 10),
          path: v.text(e.path, 8192),
          path_kind: v.oneOf(e.path_kind, ['django_path', 'router_regex']),
          change_type: v.oneOf(e.change_type, semanticKinds),
          base_indices: v.list(e.base_indices, (x) => v.integer(x, 0, 9999)),
          target_indices: v.list(e.target_indices, (x) =>
            v.integer(x, 0, 9999),
          ),
          changed_fields: v.list(
            e.changed_fields,
            (x) =>
              v.oneOf(x, [
                'action',
                'view',
                'serializer',
                'model',
                'relations',
              ]),
            5,
          ),
          base_evidence: v.list(e.base_evidence, (x) =>
            parseEvidence(x, input.base_snapshot_id),
          ),
          target_evidence: v.list(e.target_evidence, (x) =>
            parseEvidence(x, input.target_snapshot_id),
          ),
        };
      },
      20000,
    ),
    relations: v.list(
      item.relations,
      (x) => {
        const e = v.object(x);
        return {
          relation: v.text(e.relation, 80),
          source_name: v.text(e.source_name),
          target_name: v.text(e.target_name),
          change_type: v.oneOf(e.change_type, semanticKinds),
          base_edge_ids: v.list(e.base_edge_ids, v.uuid),
          target_edge_ids: v.list(e.target_edge_ids, v.uuid),
          base_evidence: v.list(e.base_evidence, (x) =>
            parseEvidence(x, input.base_snapshot_id),
          ),
          target_evidence: v.list(e.target_evidence, (x) =>
            parseEvidence(x, input.target_snapshot_id),
          ),
        };
      },
      60000,
    ),
    evidence: v.list(
      item.evidence,
      (x) => {
        const e = v.object(x);
        return {
          explanation_id: v.uuid(e.explanation_id),
          preview_id: v.uuid(e.preview_id),
          analysis_id: v.uuid(e.analysis_id),
          endpoint_index: v.integer(e.endpoint_index, 0, 9999),
          warning: v.nullable(e.warning, (x) => v.text(x)),
          references: v.list(
            e.references,
            (x) => {
              const ref = v.object(x),
                result = {
                  source_ref: v.sourceRef(
                    ref.source_ref,
                    input.base_snapshot_id,
                  ),
                  target_ref: v.nullable(ref.target_ref, (x) =>
                    v.sourceRef(x, input.target_snapshot_id),
                  ),
                  applicability: v.oneOf(ref.applicability, [
                    'unchanged',
                    'review',
                    'deleted',
                    'unknown',
                  ]),
                };
              return result.target_ref && result.applicability !== 'unchanged'
                ? v.invalid()
                : result;
            },
            480,
          ),
        };
      },
      200,
    ),
  };
  if (
    result.id !== id ||
    result.project_id !== project ||
    (result.comparability !== 'comparable' &&
      (result.interfaces.length || result.relations.length))
  )
    return v.invalid();
  if (
    result.comparability === 'comparable' &&
    (!result.base_version ||
      !result.target_version ||
      [
        'root_urlconf',
        'rule_version',
        'graph_version',
        'frontend_rule_version',
        'association_rule_version',
      ].some(
        (key) =>
          result.base_version![key as keyof AnalysisVersion] !==
          result.target_version![key as keyof AnalysisVersion],
      ))
  )
    return v.invalid();
  return result;
}
export function parseComparisonFile(
  value: unknown,
  comparison: SnapshotComparison,
): ComparisonFile {
  const item = v.object(value),
    result = {
      id: v.uuid(item.id),
      file_path: v.sourcePath(item.file_path),
      change_type: v.oneOf(item.change_type, kinds),
      base_ref: v.nullable(item.base_ref, (x) =>
        v.sourceRef(x, comparison.base_snapshot_id),
      ),
      target_ref: v.nullable(item.target_ref, (x) =>
        v.sourceRef(x, comparison.target_snapshot_id),
      ),
      base_sha256: v.nullable(item.base_sha256, hash),
      target_sha256: v.nullable(item.target_sha256, hash),
    };
  if (
    [result.base_ref, result.target_ref].some(
      (ref) => ref && ref.file_path !== result.file_path,
    ) ||
    (result.base_ref === null) !== (result.base_sha256 === null) ||
    (result.target_ref === null) !== (result.target_sha256 === null)
  )
    return v.invalid();
  const expected = !result.base_ref
    ? 'added'
    : !result.target_ref
      ? 'deleted'
      : result.base_sha256 === result.target_sha256
        ? 'unchanged'
        : 'modified';
  return result.change_type === expected &&
    (result.base_ref || result.target_ref)
    ? result
    : v.invalid();
}
function history(value: unknown, project: string): ComparisonHistory {
  const item = v.object(value),
    result = {
      id: v.uuid(item.id),
      project_id: v.uuid(item.project_id),
      job_id: v.uuid(item.job_id),
      job_status: v.oneOf(item.job_status, [
        'queued',
        'running',
        'succeeded',
        'failed',
      ]),
      created_at: v.date(item.created_at),
      summary: v.nullable(item.summary, parseSummary),
      ...parseComparisonInput({
        base_snapshot_id: item.base_snapshot_id,
        target_snapshot_id: item.target_snapshot_id,
        base_analysis_id: item.base_analysis_id,
        target_analysis_id: item.target_analysis_id,
      }),
    };
  return result.project_id === project ? result : v.invalid();
}
export const listComparisons = (
  project: string,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/projects/${project}/snapshot-comparisons/?page=${page}&page_size=10`,
    (value) =>
      v.page(value, `/api/v1/projects/${project}/snapshot-comparisons/`, (x) =>
        history(x, project),
      ),
    { signal },
  );
export const submitComparison = (
  project: string,
  input: Required<ComparisonInputRequest>,
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    `/api/v1/projects/${project}/snapshot-comparisons/`,
    key,
    (value) => {
      const job = parseJob(value);
      return job.kind === 'snapshot_comparison' &&
        job.snapshot_id === input.target_snapshot_id
        ? job
        : v.invalid();
    },
    input,
    signal,
  );
export const getComparison = (
  id: string,
  project: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/snapshot-comparisons/${id}/`,
    (value) => parseComparison(value, id, project),
    { signal },
  );
export const listComparisonFiles = (
  comparison: SnapshotComparison,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/snapshot-comparisons/${comparison.id}/files/?page=${page}&page_size=20`,
    (value) =>
      v.page(
        value,
        `/api/v1/snapshot-comparisons/${comparison.id}/files/`,
        (x) => parseComparisonFile(x, comparison),
      ),
    { signal },
  );
export const getComparisonFile = (
  comparison: SnapshotComparison,
  id: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/snapshot-comparisons/${comparison.id}/files/${id}/`,
    (value): ComparisonFileDetail => {
      const item = v.object(value),
        result = {
          ...parseComparisonFile(value, comparison),
          diff: v.text(item.diff, 512 * 1024),
          base_ranges: v.list(
            item.base_ranges,
            (x) => v.sourceRef(x, comparison.base_snapshot_id),
            20000,
          ),
          target_ranges: v.list(
            item.target_ranges,
            (x) => v.sourceRef(x, comparison.target_snapshot_id),
            20000,
          ),
        };
      if (
        result.id !== id ||
        [...result.base_ranges, ...result.target_ranges].some(
          (ref) =>
            ref.file_path !== result.file_path ||
            ref.end_line >
              (ref.snapshot_id === comparison.base_snapshot_id
                ? (result.base_ref?.end_line ?? 0)
                : (result.target_ref?.end_line ?? 0)),
        )
      )
        return v.invalid();
      return result;
    },
    { signal },
  );
