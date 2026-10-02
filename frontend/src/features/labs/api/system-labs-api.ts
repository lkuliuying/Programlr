import type {
  SystemLab,
  SystemLabRun,
  SystemLabInputRequest,
} from '../../../shared/api/generated/schema';
import { requestJson, submitJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import { parseJob } from '../../jobs';
import type { LabSelection } from './labs-api';

export function parseSystemLab(raw: unknown): SystemLab {
  const item = v.object(raw),
    cases = v.list(
      item.cases,
      (raw) => {
        const entry = v.object(raw);
        return {
          id: v.oneOf(entry.id, ['first', 'second']),
          title: v.text(entry.title),
          prediction_label: v.text(entry.prediction_label),
        };
      },
      2,
    );
  if (
    cases.length !== 2 ||
    cases[0].id !== 'first' ||
    cases[1].id !== 'second' ||
    item.example_version !== 'system-labs/1.0.0' ||
    !/^[a-f0-9]{64}$/.test(v.text(item.program_digest, 64))
  )
    return v.invalid();
  return {
    id: v.oneOf(item.id, ['container-network', 'subprocess-lifecycle']),
    version: v.text(item.version, 20),
    title: v.text(item.title),
    example_version: v.text(item.example_version),
    program_digest: v.text(item.program_digest, 64),
    description: v.text(item.description),
    cases,
    applicable: v.boolean(item.applicable),
    applicability_reason: v.text(item.applicability_reason),
  };
}

export function parseSystemRun(
  raw: unknown,
  selected: LabSelection,
): SystemLabRun {
  const item = v.object(raw),
    id = v.uuid(item.id),
    job = parseJob(item.job),
    definition = parseSystemLab(item.definition),
    prediction = v.object(item.predictions);
  if (
    item.lab_id !== definition.id ||
    job.kind !== 'lab' ||
    job.snapshot_id !== null ||
    item.snapshot_id !== selected.snapshot ||
    item.analysis_id !== selected.analysis ||
    item.endpoint_index !== selected.endpoint ||
    (job.status === 'succeeded' &&
      job.result_url !== `/api/v1/system-lab-runs/${id}/`)
  )
    return v.invalid();
  const observations = v.list(
    item.observations,
    (raw) => {
      const entry = v.object(raw);
      const result = {
        case_id: v.oneOf(entry.case_id, ['first', 'second']),
        status: v.oneOf(entry.status, ['observed', 'unavailable', 'invalid']),
        hostname: v.nullable(entry.hostname, v.text),
        addresses: v.list(entry.addresses, (value) => v.text(value, 45), 8),
        connected: v.nullable(entry.connected, v.boolean),
        pid: v.nullable(entry.pid, (value) => v.integer(value, 1)),
        return_code: v.nullable(entry.return_code, (value) =>
          v.integer(value, -255, 255),
        ),
        stdout: v.text(entry.stdout, 4096),
        timed_out: v.boolean(entry.timed_out),
        reaped: v.nullable(entry.reaped, v.boolean),
        error_code: v.nullable(entry.error_code, v.text),
        elapsed_ms: v.integer(entry.elapsed_ms, 0, 15000),
        observed_at: v.date(entry.observed_at),
      };
      if (
        definition.id === 'container-network' &&
        result.status === 'observed' &&
        (result.hostname !==
          (result.case_id === 'first' ? 'localhost' : 'task-board-api') ||
          result.connected === null ||
          (result.connected &&
            (!result.addresses.length || result.error_code !== null)))
      )
        return v.invalid();
      if (
        definition.id === 'subprocess-lifecycle' &&
        result.status === 'observed' &&
        (result.hostname !== null ||
          result.connected !== null ||
          result.pid === null ||
          result.reaped !== true ||
          result.error_code !== null ||
          (result.case_id === 'first'
            ? result.timed_out || result.return_code !== 0
            : !result.timed_out || result.return_code !== -9))
      )
        return v.invalid();
      return result;
    },
    2,
  );
  if (
    observations.some(
      (item, index) => item.case_id !== (index === 0 ? 'first' : 'second'),
    )
  )
    return v.invalid();
  const cleanupRaw = v.object(item.cleanup),
    cleanup = {
      status: v.oneOf(cleanupRaw.status, [
        'pending',
        'completed',
        'unconfirmed',
      ]),
      error_code: v.nullable(cleanupRaw.error_code, v.text),
    };
  if (
    cleanup.status === 'completed' &&
    (cleanup.error_code !== null ||
      observations.some((item) => item.reaped === false))
  )
    return v.invalid();
  if (
    job.status === 'succeeded' &&
    (observations.length !== 2 ||
      cleanup.status !== 'completed' ||
      observations.some(
        (item) => item.status !== 'observed' || item.reaped !== true,
      ) ||
      (definition.id === 'container-network' &&
        observations[1].connected !== true))
  )
    return v.invalid();
  return {
    id,
    job,
    snapshot_id: selected.snapshot,
    analysis_id: selected.analysis,
    endpoint_index: selected.endpoint,
    lab_id: definition.id,
    definition,
    predictions: {
      first: v.boolean(prediction.first),
      second: v.boolean(prediction.second),
    },
    observations,
    cleanup,
    created_at: v.date(item.created_at),
  };
}
const query = (selected: LabSelection) =>
  `analysis_id=${selected.analysis}&endpoint_index=${selected.endpoint}`;
export const listSystemLabs = (selected: LabSelection, signal: AbortSignal) =>
  requestJson(
    `/api/v1/system-labs/?${query(selected)}`,
    (raw) => v.page(raw, '/api/v1/system-labs/', parseSystemLab),
    { signal },
  );
export const listSystemRuns = (
  selected: LabSelection,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/system-lab-runs/?${query(selected)}&page=${page}&page_size=10`,
    (raw) =>
      v.page(raw, '/api/v1/system-lab-runs/', (item) =>
        parseSystemRun(item, selected),
      ),
    { signal },
  );
export const getSystemRun = (
  id: string,
  selected: LabSelection,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/system-lab-runs/${id}/`,
    (raw) => {
      const result = parseSystemRun(raw, selected);
      return result.id === id ? result : v.invalid();
    },
    { signal },
  );
export const getSystemRunForJob = (
  selected: LabSelection,
  jobId: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/system-lab-runs/?${query(selected)}&job_id=${jobId}`,
    (raw) => {
      const page = v.page(raw, '/api/v1/system-lab-runs/', (item) =>
        parseSystemRun(item, selected),
      );
      if (page.count > 1 || page.results.some((item) => item.job.id !== jobId))
        return v.invalid();
      return page.results.at(0) ?? null;
    },
    { signal },
  );
export const submitSystemRun = (
  body: SystemLabInputRequest & { lab_id: string },
  key: string,
  signal: AbortSignal,
) => {
  const { lab_id, ...input } = body;
  return submitJson(
    `/api/v1/system-labs/${lab_id}/runs/`,
    key,
    parseJob,
    input,
    signal,
  );
};
