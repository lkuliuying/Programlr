import type { Job } from '../shared/api/generated/schema';
import { requestJson } from '../shared/api/client';
import * as v from '../shared/api/validation';
import { parseSnapshot } from '../features/projects';
import { parseAnalysis, parseComparison } from '../features/analysis';
import { parseExplanation } from '../features/explanations';
import { parseRun, parseSystemRun } from '../features/labs';
import { getCheck } from '../features/jobs';
import type { WorkspaceSelection } from './workspace-location';

export async function resolveJobResult(
  job: Job,
  signal: AbortSignal,
): Promise<Partial<WorkspaceSelection> | { check: string }> {
  if (job.status !== 'succeeded' || !job.result_url) return v.invalid();
  if (job.kind === 'system_check') {
    const check = await getCheck(job.result_url, signal);
    if (check.job_id !== job.id || !job.result_url.endsWith(`/${check.id}/`))
      return v.invalid();
    return { check: job.result_url };
  }
  const raw = await requestJson(job.result_url, v.object, { signal });
  const id = v.uuid(raw.id);
  if (!job.result_url.endsWith(`/${id}/`)) return v.invalid();
  if (job.kind === 'import') {
    const snapshot = parseSnapshot(raw);
    if (snapshot.job_id !== job.id || snapshot.id !== job.snapshot_id)
      return v.invalid();
    return {
      project: snapshot.project_id,
      snapshot: snapshot.id,
      section: 'workbench',
    };
  }
  if (job.kind === 'snapshot_comparison') {
    const comparison = parseComparison(raw, id, v.uuid(raw.project_id));
    if (
      comparison.job_id !== job.id ||
      comparison.target_snapshot_id !== job.snapshot_id
    )
      return v.invalid();
    return {
      project: comparison.project_id,
      snapshot: comparison.base_snapshot_id,
      analysis: comparison.base_analysis_id,
      comparison: id,
      section: 'comparison',
    };
  }
  const snapshotId = v.uuid(raw.snapshot_id);
  const snapshot = await requestJson(
    `/api/v1/snapshots/${snapshotId}/`,
    parseSnapshot,
    { signal },
  );
  if (snapshot.id !== snapshotId) return v.invalid();
  if (job.kind === 'analysis') {
    const analysis = parseAnalysis(raw, snapshotId, id);
    if (analysis.job_id !== job.id || analysis.snapshot_id !== job.snapshot_id)
      return v.invalid();
    return {
      project: snapshot.project_id,
      snapshot: snapshotId,
      analysis: id,
      section: 'api',
    };
  }
  const selected = {
    snapshot: snapshotId,
    analysis: v.uuid(raw.analysis_id),
    endpoint: v.integer(raw.endpoint_index),
  };
  const analysis = await requestJson(
    `/api/v1/analyses/${selected.analysis}/`,
    (value) => parseAnalysis(value, snapshotId, selected.analysis),
    { signal },
  );
  if (selected.endpoint >= analysis.coverage.endpoint_count) return v.invalid();
  const location = {
    project: snapshot.project_id,
    snapshot: snapshotId,
    analysis: selected.analysis,
    endpoint: selected.endpoint,
  };
  if (job.kind === 'explanation') {
    const explanation = parseExplanation(raw, selected);
    if (
      explanation.job_id !== job.id ||
      explanation.snapshot_id !== job.snapshot_id
    )
      return v.invalid();
    return {
      ...location,
      explanation: id,
      panel: 'explanation',
      section: 'explanation',
    };
  }
  const system = job.result_url.startsWith('/api/v1/system-lab-runs/');
  const run = system ? parseSystemRun(raw, selected) : parseRun(raw, selected);
  if (run.job.id !== job.id) return v.invalid();
  return {
    ...location,
    ...(system ? { system_run: id } : { run: id }),
    panel: 'lab',
    section: 'labs',
  };
}
