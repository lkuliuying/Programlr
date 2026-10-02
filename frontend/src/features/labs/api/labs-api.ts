import type {
  Lab,
  LabInputRequest,
  LabRun,
  Predictions,
} from '../../../shared/api/generated/schema';
import { requestJson, submitJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import { parseJob } from '../../jobs';

export type LabSelection = {
  snapshot: string;
  analysis: string;
  endpoint: number;
};
export const cases = ['normal', 'missing', 'empty', 'whitespace'] as const;
export function parseLab(raw: unknown): Lab {
  const item = v.object(raw);
  const parsed = {
    id: v.oneOf(item.id, ['request-validation']),
    version: v.text(item.version, 20),
    title: v.text(item.title, 200),
    example_version: v.text(item.example_version, 80),
    description: v.text(item.description),
    cases: v.list(
      item.cases,
      (raw) => {
        const item = v.object(raw);
        return {
          id: v.oneOf(item.id, cases),
          title: v.text(item.title, 80),
          input: Object.fromEntries(
            Object.entries(v.object(item.input)).map(([key, value]) => [
              key,
              v.text(value, 200),
            ]),
          ),
        };
      },
      4,
    ),
    applicable: v.boolean(item.applicable),
    applicability_reason: v.text(item.applicability_reason),
  };
  if (
    parsed.cases.length !== 4 ||
    new Set(parsed.cases.map((item) => item.id)).size !== 4
  )
    return v.invalid();
  return parsed;
}
function predictions(raw: unknown): Predictions {
  const item = v.object(raw);
  const decode = (raw: unknown) => {
    const item = v.object(raw);
    return {
      status: v.integer(item.status, 100, 599),
      writes: v.integer(item.writes, 0, 1),
    };
  };
  return {
    normal: decode(item.normal),
    missing: decode(item.missing),
    empty: decode(item.empty),
    whitespace: decode(item.whitespace),
  };
}
export function parseRun(raw: unknown, selected: LabSelection): LabRun {
  const item = v.object(raw),
    id = v.uuid(item.id),
    job = parseJob(item.job);
  if (
    job.kind !== 'lab' ||
    job.snapshot_id !== null ||
    item.snapshot_id !== selected.snapshot ||
    item.analysis_id !== selected.analysis ||
    item.endpoint_index !== selected.endpoint
  )
    return v.invalid();
  if (
    job.status === 'succeeded' &&
    job.result_url !== `/api/v1/lab-runs/${id}/`
  )
    return v.invalid();
  const observations = v.list(
    item.observations,
    (raw) => {
      const entry = v.object(raw),
        response = v.object(entry.response),
        caseId = v.oneOf(entry.case_id, cases);
      if (entry.request_path !== `/internal/labs/runs/${id}/cases/${caseId}/`)
        return v.invalid();
      return {
        case_id: caseId,
        input: Object.fromEntries(
          Object.entries(v.object(entry.input)).map(([key, value]) => [
            key,
            v.text(value, 200),
          ]),
        ),
        request_path: v.text(entry.request_path),
        response: {
          status: v.integer(response.status, 100, 599),
          body: v.object(response.body),
        },
        before_count: v.integer(entry.before_count, 0, 4),
        after_count: v.nullable(entry.after_count, (value) =>
          v.integer(value, 0, 4),
        ),
        elapsed_ms: v.integer(entry.elapsed_ms, 0, 120000),
        observed_at: v.text(entry.observed_at, 40),
      };
    },
    4,
  );
  const cleanup = v.object(item.cleanup);
  if (Object.keys(cleanup).length) {
    v.oneOf(cleanup.status, ['completed', 'unconfirmed', 'pending']);
    v.nullable(cleanup.error_code, (value) => v.text(value, 80));
    if (cleanup.status === 'completed') {
      const observation = v.object(cleanup.observation);
      if (
        observation.id !== id ||
        observation.closed !== true ||
        observation.record_count !== 0
      )
        return v.invalid();
    }
  }
  return {
    id,
    job,
    snapshot_id: selected.snapshot,
    analysis_id: selected.analysis,
    endpoint_index: selected.endpoint,
    definition: parseLab(item.definition),
    predictions: predictions(item.predictions),
    observations,
    cleanup: {
      status: v.text(cleanup.status, 40),
      observation: v.nullable(cleanup.observation, v.object),
      error_code: v.nullable(cleanup.error_code, v.text),
    },
    created_at: v.date(item.created_at),
  };
}
const query = (selected: LabSelection) =>
  `analysis_id=${selected.analysis}&endpoint_index=${selected.endpoint}`;
export const getLab = (selected: LabSelection, signal: AbortSignal) =>
  requestJson(`/api/v1/labs/request-validation/?${query(selected)}`, parseLab, {
    signal,
  });
export const listRuns = (
  selected: LabSelection,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/lab-runs/?${query(selected)}&page=${page}&page_size=10`,
    (value) =>
      v.page(value, '/api/v1/lab-runs/', (item) => parseRun(item, selected)),
    { signal },
  );
export const getRun = (
  id: string,
  selected: LabSelection,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/lab-runs/${id}/`,
    (raw) => {
      const result = parseRun(raw, selected);
      return result.id === id ? result : v.invalid();
    },
    { signal },
  );
export const getRunForJob = (
  selected: LabSelection,
  jobId: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/lab-runs/?${query(selected)}&job_id=${jobId}`,
    (raw) => {
      const result = v.page(raw, '/api/v1/lab-runs/', (item) =>
        parseRun(item, selected),
      );
      if (
        result.count > 1 ||
        result.results.some((run) => run.job.id !== jobId)
      )
        return v.invalid();
      return result.results.at(0) ?? null;
    },
    { signal },
  );
export const submitRun = (
  body: LabInputRequest,
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    '/api/v1/labs/request-validation/runs/',
    key,
    parseJob,
    body,
    signal,
  );
