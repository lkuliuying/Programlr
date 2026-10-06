import {
  deleteJson,
  requestJson,
  submitBody,
  submitJson,
} from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import type {
  Snapshot,
  RootCandidate,
  DeletionPreview,
  ProjectSummary,
  ProjectManagementPage,
  ProjectActivity,
  ProjectActivityItem,
} from '../../../shared/api/generated/schema';
export type { DeletionPreview } from '../../../shared/api/generated/schema';
import { parseJob } from '../../jobs';
import { parseProject, parseSnapshot } from './projects-api';
import { folderBody, type FolderSelection } from '../folder-validation';

export type ProjectOrdering = 'recent_import' | 'created' | 'name';
export function parseProjectSummary(raw: unknown): ProjectSummary {
  const item = v.object(raw),
    project = parseProject(item.project),
    snapshot = v.nullable(item.latest_snapshot, parseSnapshot);
  if (snapshot && snapshot.project_id !== project.id) return v.invalid();
  return {
    project,
    snapshot_count: v.integer(item.snapshot_count),
    latest_snapshot: snapshot,
    last_imported_at: v.nullable(item.last_imported_at, v.date),
    technologies: v.list(
      item.technologies,
      (raw) => {
        const tag = v.object(raw);
        return {
          name: v.text(tag.name, 100),
          evidence_kind: v.oneOf(tag.evidence_kind, [
            'language',
            'declaration',
            'usage',
          ]),
        };
      },
      100,
    ),
    root_count: v.nullable(item.root_count, v.integer),
    root_path: v.nullable(item.root_path, v.sourcePath),
  };
}
export const listProjectManagement = (
  page: number,
  signal: AbortSignal,
  query = '',
  technology = '',
  ordering: ProjectOrdering = 'recent_import',
) =>
  requestJson(
    `/api/v1/projects/management/?${new URLSearchParams({ page: String(page), page_size: '10', q: query, technology, ordering })}`,
    (value): ProjectManagementPage => ({
      ...v.page(value, '/api/v1/projects/management/', parseProjectSummary, [
        'q',
        'technology',
        'ordering',
      ]),
      technologies: v.list(
        v.object(value).technologies,
        (value) => v.text(value, 100),
        100,
      ),
    }),
    { signal },
  );

export const getProjectActivity = (signal: AbortSignal) =>
  requestJson(
    '/api/v1/projects/activity/',
    (raw): ProjectActivity => {
      const value = v.object(raw);
      const parse = (raw: unknown): ProjectActivityItem => {
        const item = v.object(raw),
          project = parseProject(item.project),
          snapshot = v.nullable(item.snapshot, parseSnapshot);
        if (snapshot && snapshot.project_id !== project.id) return v.invalid();
        return {
          project,
          snapshot,
          status: v.oneOf(item.status, [
            'importing',
            'scanning',
            'needs_root',
            'no_root',
            'analyzing',
            'ready',
            'failed',
            'pending',
          ]),
          root_count: v.nullable(item.root_count, v.integer),
          endpoint_count: v.nullable(item.endpoint_count, v.integer),
          stages: v.list(
            item.stages,
            (raw) => {
              const stage = v.object(raw),
                job = parseJob(stage.job),
                kind = v.oneOf(stage.kind, [
                  'import',
                  'source_scan',
                  'analysis',
                ]);
              if (
                job.kind !== kind ||
                (snapshot && job.snapshot_id && job.snapshot_id !== snapshot.id)
              )
                return v.invalid();
              return {
                kind,
                job,
                events: v.list(
                  stage.events,
                  (raw) => {
                    const event = v.object(raw);
                    return {
                      at: v.date(event.at),
                      result: v.text(event.result, 100),
                      stage: v.text(event.stage, 100),
                      error_code: v.text(event.error_code, 100),
                    };
                  },
                  10000,
                ),
              };
            },
            3,
          ),
        };
      };
      return {
        active: v.list(value.active, parse, 5),
        recent: v.list(value.recent, parse, 5),
      };
    },
    { signal },
  );

export type PreparedSnapshot = Snapshot & {
  preparation_status:
    | 'pending'
    | 'scanning'
    | 'needs_root'
    | 'no_root'
    | 'analyzing'
    | 'ready'
    | 'failed';
  source_scan_id: string | null;
  scan_job_id: string | null;
  analysis_job_id: string | null;
  analysis_id: string | null;
};
export const getPreparedSnapshot = (
  snapshotId: string,
  projectId: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/snapshots/${snapshotId}/`,
    (raw): PreparedSnapshot => {
      const value = v.object(raw),
        snapshot = parseSnapshot(value);
      if (snapshot.id !== snapshotId || snapshot.project_id !== projectId)
        return v.invalid();
      return {
        ...snapshot,
        preparation_status: v.oneOf(value.preparation_status, [
          'pending',
          'scanning',
          'needs_root',
          'no_root',
          'analyzing',
          'ready',
          'failed',
        ]),
        source_scan_id: v.nullable(value.source_scan_id, v.uuid),
        scan_job_id: v.nullable(value.scan_job_id, v.uuid),
        analysis_job_id: v.nullable(value.analysis_job_id, v.uuid),
        analysis_id: v.nullable(value.analysis_id, v.uuid),
      };
    },
    { signal },
  );

export const importFolder = (
  projectId: string,
  folder: FolderSelection,
  key: string,
  signal: AbortSignal,
) =>
  submitBody(
    `/api/v1/projects/${projectId}/folder-imports/`,
    key,
    parseJob,
    folderBody(folder),
    signal,
  );
export const retryFolder = (
  jobId: string,
  folder: FolderSelection,
  key: string,
  signal: AbortSignal,
) =>
  submitBody(
    `/api/v1/jobs/${jobId}/folder-retries/`,
    key,
    parseJob,
    folderBody(folder),
    signal,
  );
export const scanSnapshot = (
  snapshotId: string,
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    `/api/v1/snapshots/${snapshotId}/source-scans/`,
    key,
    parseJob,
    {},
    signal,
  );

export const getSourceScan = (
  scanId: string,
  snapshotId: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/source-scans/${scanId}/`,
    (raw) => {
      const item = v.object(raw);
      if (v.uuid(item.id) !== scanId || v.uuid(item.snapshot_id) !== snapshotId)
        return v.invalid();
      return {
        id: scanId,
        scan_version: v.text(item.scan_version),
        diagnostics: v.list(item.diagnostics, (raw) => {
          const diagnostic = v.object(raw);
          return {
            code: v.text(diagnostic.code),
            message: v.text(diagnostic.message),
            source_ref: v.nullable(diagnostic.source_ref ?? null, (ref) =>
              v.sourceRef(ref, snapshotId),
            ),
          };
        }),
        root_candidates: v.list(
          item.root_candidates,
          (raw): RootCandidate => {
            const root = v.object(raw);
            return {
              file_path: v.sourcePath(root.file_path),
              module: v.text(root.module),
              reason: v.text(root.reason),
              source_refs: v.list(root.source_refs, (value) =>
                v.sourceRef(value, snapshotId),
              ),
            };
          },
          2000,
        ),
      };
    },
    { signal },
  );

const targetPath = (kind: 'project' | 'snapshot', id: string) =>
  `/api/v1/${kind === 'project' ? 'projects' : 'snapshots'}/${id}/`;
export const getDeletionPreview = (
  kind: 'project' | 'snapshot',
  id: string,
  signal: AbortSignal,
) =>
  requestJson(
    targetPath(kind, id) + 'deletion-preview/',
    (raw): DeletionPreview => {
      const item = v.object(raw);
      if (item.target_type !== kind || v.uuid(item.target_id) !== id)
        return v.invalid();
      const digest = v.text(item.confirmation_digest, 64);
      if (!/^[0-9a-f]{64}$/.test(digest)) return v.invalid();
      return {
        target_type: kind,
        target_id: id,
        project_id: v.uuid(item.project_id),
        object_name: v.text(item.object_name, 200),
        confirmation_digest: digest,
        can_delete: v.boolean(item.can_delete),
        receiving: v.boolean(item.receiving),
        busy_jobs: v.list(item.busy_jobs, parseJob),
        scope: (() => {
          const scope = v.object(item.scope);
          return {
            snapshots: v.integer(scope.snapshots),
            files: v.integer(scope.files),
            analyses: v.integer(scope.analyses),
            source_scans: v.integer(scope.source_scans),
            explanations: v.integer(scope.explanations),
            attempts: v.integer(scope.attempts),
            lab_runs: v.integer(scope.lab_runs),
            comparisons: v.integer(scope.comparisons),
          };
        })(),
      };
    },
    { signal },
  );
export const deleteTarget = (
  preview: DeletionPreview,
  key: string,
  signal: AbortSignal,
) =>
  deleteJson(
    targetPath(preview.target_type, preview.target_id),
    key,
    parseJob,
    { confirmation_digest: preview.confirmation_digest },
    signal,
  );
