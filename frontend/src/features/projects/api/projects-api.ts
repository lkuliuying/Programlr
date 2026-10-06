import {
  requestJson,
  submitBody,
  submitJson,
  patchJson,
  ApiError,
} from '../../../shared/api/client';
import type {
  Project,
  Snapshot,
  SourceFile,
  SourceContent,
  SnapshotSearchResult,
} from '../../../shared/api/generated/schema';
import * as v from '../../../shared/api/validation';
import { parseJob } from '../../jobs';
import { archiveValidationMessage } from '../archive-validation';

export function parseProject(value: unknown): Project {
  const item = v.object(value);
  return {
    id: v.uuid(item.id),
    name: v.text(item.name, 200),
    created_at: v.date(item.created_at),
  };
}
export function parseSnapshot(value: unknown): Snapshot {
  const item = v.object(value),
    summary = v.object(item.summary);
  const name = v.text(item.name, 400);
  if ([...name].length > 200) return v.invalid();
  return {
    id: v.uuid(item.id),
    project_id: v.uuid(item.project_id),
    name,
    job_id: v.uuid(item.job_id),
    created_at: v.date(item.created_at),
    source_extensions: v.list(item.source_extensions, (value) =>
      v.text(value, 10),
    ),
    source_manifest_names: v.list(item.source_manifest_names ?? [], (value) =>
      v.text(value, 255),
    ),
    preparation_status: v.text(item.preparation_status ?? 'pending'),
    source_scan_id: v.nullable(item.source_scan_id ?? null, v.uuid),
    scan_job_id: v.nullable(item.scan_job_id ?? null, v.uuid),
    analysis_job_id: v.nullable(item.analysis_job_id ?? null, v.uuid),
    analysis_id: v.nullable(item.analysis_id ?? null, v.uuid),
    summary: {
      entries: v.integer(summary.entries),
      accepted: v.integer(summary.accepted),
      excluded: v.integer(summary.excluded),
      skipped: v.integer(summary.skipped),
      rejected: v.integer(summary.rejected),
      declared_bytes: v.integer(summary.declared_bytes),
      extracted_bytes: v.integer(summary.extracted_bytes),
      reasons: Object.fromEntries(
        Object.entries(v.object(summary.reasons)).map(([key, value]) => [
          key,
          v.integer(value),
        ]),
      ),
    },
  };
}
export function parseFile(value: unknown, snapshotId: string): SourceFile {
  const item = v.object(value);
  const result = {
    id: v.uuid(item.id),
    snapshot_id: v.uuid(item.snapshot_id),
    file_path: v.sourcePath(item.file_path),
    sha256: v.text(item.sha256, 64),
    size_bytes: v.integer(item.size_bytes),
    line_count: v.integer(item.line_count, 1),
    encoding: v.text(item.encoding),
  };
  return result.snapshot_id === snapshotId &&
    /^[a-f0-9]{64}$/.test(result.sha256) &&
    result.encoding === 'utf-8'
    ? result
    : v.invalid();
}
export const listProjects = (
  page: number,
  signal: AbortSignal,
  query?: string,
) =>
  requestJson(
    `/api/v1/projects/?page=${page}&page_size=20${query ? '&q=' + encodeURIComponent(query) : ''}`,
    (value) => v.page(value, '/api/v1/projects/', parseProject, ['q']),
    { signal },
  );
export const getProject = (id: string, signal: AbortSignal) =>
  requestJson(
    `/api/v1/projects/${id}/`,
    (value) => {
      const item = parseProject(value);
      return item.id === id ? item : v.invalid();
    },
    { signal },
  );
export const createProject = (name: string, key: string, signal: AbortSignal) =>
  submitJson('/api/v1/projects/', key, parseProject, { name }, signal);
export const importArchive = (
  projectId: string,
  file: File,
  key: string,
  signal: AbortSignal,
) => {
  const error = archiveValidationMessage(file);
  if (error) throw new ApiError(error, 400);
  const body = new FormData();
  body.append('archive', file);
  return submitBody(
    `/api/v1/projects/${projectId}/imports/`,
    key,
    (value) => {
      const job = parseJob(value);
      return job.kind === 'import' ? job : v.invalid();
    },
    body,
    signal,
  );
};
export const listSnapshots = (
  projectId: string,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/projects/${projectId}/snapshots/?page=${page}&page_size=20`,
    (value) =>
      v.page(value, `/api/v1/projects/${projectId}/snapshots/`, (item) => {
        const result = parseSnapshot(item);
        return result.project_id === projectId ? result : v.invalid();
      }),
    { signal },
  );
export const searchSnapshots = (
  page: number,
  signal: AbortSignal,
  query: string,
) =>
  requestJson(
    `/api/v1/snapshots/?page=${page}&page_size=20&q=${encodeURIComponent(query)}`,
    (value) =>
      v.page(
        value,
        '/api/v1/snapshots/',
        (raw): SnapshotSearchResult => {
          const item = v.object(raw),
            snapshot = parseSnapshot(item.snapshot),
            project = parseProject(item.project);
          return snapshot.project_id === project.id
            ? { snapshot, project }
            : v.invalid();
        },
        ['q'],
      ),
    { signal },
  );
export const getSnapshot = (
  id: string,
  projectId: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/snapshots/${id}/`,
    (value) => {
      const item = parseSnapshot(value);
      return item.id === id && item.project_id === projectId
        ? item
        : v.invalid();
    },
    { signal },
  );

export const renameSnapshot = (
  snapshot: Snapshot,
  name: string,
  signal: AbortSignal,
) => {
  const normalized = name.trim();
  if (
    !normalized ||
    [...normalized].length > 200 ||
    [...name].some(
      (char) =>
        char.charCodeAt(0) < 32 ||
        (char.charCodeAt(0) >= 127 && char.charCodeAt(0) <= 159),
    )
  )
    throw new ApiError('快照名称须为 1–200 个字符，且不能包含控制字符。', 400);
  return patchJson(
    `/api/v1/snapshots/${snapshot.id}/`,
    (value) => {
      const result = parseSnapshot(value);
      return result.id === snapshot.id &&
        result.project_id === snapshot.project_id &&
        result.name === normalized
        ? result
        : v.invalid();
    },
    { name: normalized },
    signal,
  );
};

export async function listFiles(
  snapshotId: string,
  signal: AbortSignal,
): Promise<SourceFile[]> {
  const path = `/api/v1/snapshots/${snapshotId}/files/`,
    files: SourceFile[] = [];
  let count: number | undefined;
  for (let index = 1; index <= 20; index++) {
    const page = await requestJson(
      `${path}?page=${index}&page_size=100`,
      (value) => v.page(value, path, (item) => parseFile(item, snapshotId)),
      { signal },
    );
    if (page.count > 2000 || (count !== undefined && count !== page.count))
      return v.invalid();
    count = page.count;
    files.push(...page.results);
    if (!page.next) {
      if (
        files.length !== count ||
        new Set(files.map((file) => file.id)).size !== count ||
        new Set(files.map((file) => file.file_path)).size !== count
      )
        return v.invalid();
      return files;
    }
    if (!page.results.length) return v.invalid();
  }
  return v.invalid();
}
export function getSource(
  file: SourceFile,
  start: number,
  end: number,
  signal: AbortSignal,
) {
  if (start < 1 || end < start || end > file.line_count || end - start >= 500)
    throw new ApiError('源码引用行范围无效。', 0);
  return requestJson(
    `/api/v1/snapshots/${file.snapshot_id}/files/${file.id}/content/?start_line=${start}&end_line=${end}`,
    (value): SourceContent => {
      const item = v.object(value),
        metadata = parseFile(value, file.snapshot_id);
      if (
        metadata.id !== file.id ||
        metadata.file_path !== file.file_path ||
        metadata.sha256 !== file.sha256 ||
        metadata.line_count !== file.line_count ||
        metadata.size_bytes !== file.size_bytes ||
        item.start_line !== start ||
        item.end_line !== end
      )
        return v.invalid();
      const content = v.text(item.content, 1024 * 1024);
      const lines = content.replace(/\n$/, '').split('\n');
      if (lines.length !== end - start + 1) return v.invalid();
      return { ...metadata, start_line: start, end_line: end, content };
    },
    { signal },
  );
}
