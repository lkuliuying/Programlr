import { useSyncExternalStore } from 'react';
import type { SourceRef } from '../shared/api/generated/schema';

export const workspaceSections = [
  'workbench',
  'import',
  'source',
  'api',
  'graph',
  'comparison',
  'impact',
  'learning',
  'labs',
  'explanation',
  'system',
  'jobs',
] as const;
export type WorkspaceSection = (typeof workspaceSections)[number];

export type WorkspaceSelection = {
  project: string | null;
  snapshot: string | null;
  analysis: string | null;
  endpoint: number | null;
  node: string | null;
  job: string | null;
  preview: string | null;
  explanation: string | null;
  attempt: string | null;
  run: string | null;
  system_run: string | null;
  curriculum: string | null;
  goal: string | null;
  panel: 'source' | 'explanation' | 'learning' | 'lab' | null;
  comparison: string | null;
  change: string | null;
  candidates: boolean;
  reference: SourceRef | null;
  secondaryReference: SourceRef | null;
  section: WorkspaceSection | null;
  invalid: boolean;
};
export function readSelection(search: string): WorkspaceSelection {
  const params = new URLSearchParams(search);
  const candidates = params.get('candidates') === 'true';
  let invalid = false;
  const rawSection = params.get('section');
  const section =
    workspaceSections.find((value) => value === rawSection) ?? null;
  if (
    rawSection !== null &&
    (section === null || params.getAll('section').length !== 1)
  )
    invalid = true;
  if (
    params.has('candidates') &&
    (params.getAll('candidates').length !== 1 ||
      !['true', 'false'].includes(params.get('candidates') ?? ''))
  )
    invalid = true;
  const id = (key: string) => {
    const value = params.get(key);
    if (value === null) return null;
    if (
      params.getAll(key).length !== 1 ||
      !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(
        value,
      )
    ) {
      invalid = true;
      return null;
    }
    return value;
  };
  const project = id('project'),
    snapshot = id('snapshot'),
    analysis = id('analysis'),
    node = id('node'),
    job = id('job'),
    preview = id('preview'),
    explanation = id('explanation'),
    attempt = id('attempt'),
    run = id('run'),
    system_run = id('system_run'),
    curriculum = id('curriculum'),
    comparison = id('comparison'),
    change = id('change');
  const goal = params.get('goal');
  const rawPanel = params.get('panel');
  const panel =
    rawPanel === 'source' ||
    rawPanel === 'explanation' ||
    rawPanel === 'learning' ||
    rawPanel === 'lab'
      ? rawPanel
      : null;
  if (
    rawPanel !== null &&
    (panel === null || params.getAll('panel').length !== 1)
  )
    invalid = true;
  if (
    goal !== null &&
    (params.getAll('goal').length !== 1 ||
      !/^[a-z0-9][a-z0-9-]{0,79}$/.test(goal))
  )
    invalid = true;
  const raw = params.get('endpoint');
  const endpoint =
    raw !== null &&
    /^(0|[1-9][0-9]{0,3})$/.test(raw) &&
    params.getAll('endpoint').length === 1
      ? Number(raw)
      : null;
  if (
    (raw !== null && endpoint === null) ||
    (snapshot && !project) ||
    (analysis && !snapshot) ||
    (node && !analysis) ||
    (endpoint !== null && !analysis) ||
    (job && !project) ||
    (comparison && !project) ||
    (change && !comparison) ||
    ((preview ||
      explanation ||
      attempt ||
      run ||
      system_run ||
      curriculum ||
      goal ||
      panel) &&
      endpoint === null)
  )
    invalid = true;
  function readReference(suffix: string): SourceRef | null {
    const keys = ['file', 'start', 'end'].map((key) => key + suffix);
    if (keys.some((key) => params.has(key))) {
      const path = params.get('file' + suffix) ?? '',
        start = params.get('start' + suffix) ?? '',
        end = params.get('end' + suffix) ?? '';
      if (
        !snapshot ||
        !path ||
        /[\\:]/.test(path) ||
        [...path].some((char) => char.charCodeAt(0) < 32) ||
        path
          .split('/')
          .some((part) => !part || part === '.' || part === '..') ||
        !/^[1-9][0-9]{0,8}$/.test(start) ||
        !/^[1-9][0-9]{0,8}$/.test(end) ||
        Number(end) < Number(start) ||
        keys.some((key) => params.getAll(key).length !== 1)
      )
        invalid = true;
      else
        return {
          snapshot_id: snapshot,
          file_path: path,
          start_line: Number(start),
          end_line: Number(end),
        };
    }
    return null;
  }
  const reference = readReference('');
  const secondaryReference = readReference('2');
  return {
    project,
    snapshot,
    analysis,
    endpoint,
    node,
    job,
    preview,
    explanation,
    attempt,
    run,
    system_run,
    curriculum,
    goal,
    panel,
    comparison,
    change,
    candidates,
    reference,
    secondaryReference,
    section,
    invalid,
  };
}
function subscribe(callback: () => void) {
  window.addEventListener('popstate', callback);
  return () => window.removeEventListener('popstate', callback);
}
export function resolveWorkspaceSection(
  selection: WorkspaceSelection,
  view?: string | null,
): WorkspaceSection {
  if (selection.section) return selection.section;
  if (view === 'jobs') return 'jobs';
  if (selection.panel === 'learning')
    return selection.attempt || (!selection.curriculum && !selection.goal)
      ? 'labs'
      : 'learning';
  if (selection.panel)
    return selection.panel === 'lab' ? 'labs' : selection.panel;
  if (selection.reference) return 'source';
  if (selection.run || selection.system_run || selection.attempt) return 'labs';
  if (selection.curriculum || selection.goal) return 'learning';
  if (selection.preview || selection.explanation) return 'explanation';
  if (selection.comparison) return 'comparison';
  return 'workbench';
}
export function useWorkspaceLocation() {
  const search = useSyncExternalStore(subscribe, () => window.location.search);
  return {
    selection: readSelection(search),
    view: new URLSearchParams(search).get('view'),
    navigate: (selection: Partial<WorkspaceSelection>) => {
      const params = new URLSearchParams();
      for (const key of [
        'project',
        'snapshot',
        'analysis',
        'endpoint',
        'node',
        'job',
        'preview',
        'explanation',
        'attempt',
        'run',
        'system_run',
        'curriculum',
        'goal',
        'panel',
        'comparison',
        'change',
        'section',
      ] as const)
        if (selection[key] !== undefined && selection[key] !== null)
          params.set(key, String(selection[key]));
      if (selection.reference) {
        params.set('file', selection.reference.file_path);
        params.set('start', String(selection.reference.start_line));
        params.set('end', String(selection.reference.end_line));
      }
      if (selection.secondaryReference) {
        params.set('file2', selection.secondaryReference.file_path);
        params.set('start2', String(selection.secondaryReference.start_line));
        params.set('end2', String(selection.secondaryReference.end_line));
      }
      if (selection.candidates) params.set('candidates', 'true');
      window.history.pushState(
        null,
        '',
        params.size ? `?${params}` : window.location.pathname,
      );
      window.dispatchEvent(new PopStateEvent('popstate'));
    },
  };
}
