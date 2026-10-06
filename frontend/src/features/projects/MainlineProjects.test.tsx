import { webcrypto } from 'node:crypto';
import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  MainlineImport,
  DeletionControl,
  MainlineProjects,
} from './MainlineProjects';
const projectId = '11111111-1111-4111-8111-111111111111';
const job = {
  id: '22222222-2222-4222-8222-222222222222',
  kind: 'import',
  status: 'queued',
  stage: 'queued',
  previous_job_id: null,
  snapshot_id: null,
  progress: null,
  error: null,
  result_url: null,
  created_at: '2026-10-03T00:00:00Z',
  updated_at: '2026-10-03T00:00:00Z',
};
const response = (value: unknown) => new Response(JSON.stringify(value));
function setup(element: React.ReactNode) {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    },
  });
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal('crypto', webcrypto);
  Object.defineProperty(Blob.prototype, 'arrayBuffer', {
    configurable: true,
    value: function (this: Blob) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsArrayBuffer(this);
      });
    },
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(<QueryClientProvider client={client}>{element}</QueryClientProvider>);
}
afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const owner = { id: projectId, name: '项目源码', created_at: job.created_at };
const snapshot = {
  id: '33333333-3333-4333-8333-333333333333',
  name: '版本一',
  project_id: projectId,
  job_id: job.id,
  created_at: job.created_at,
  source_extensions: ['.ts'],
  source_manifest_names: [],
  preparation_status: 'no_root',
  source_scan_id: null,
  scan_job_id: null,
  analysis_job_id: null,
  analysis_id: null,
  summary: {
    entries: 2,
    accepted: 2,
    excluded: 0,
    skipped: 0,
    rejected: 0,
    declared_bytes: 10,
    extracted_bytes: 10,
    reasons: {},
  },
};
const managementPage = {
  count: 1,
  next: null,
  previous: null,
  technologies: ['TypeScript'],
  results: [
    {
      project: owner,
      latest_snapshot: snapshot,
      snapshot_count: 1,
      last_imported_at: snapshot.created_at,
      technologies: [{ name: 'TypeScript', evidence_kind: 'language' }],
      root_count: 0,
      root_path: null,
    },
  ],
};

test('项目卡片查询真实技术与排序，展开不改URL，跨项目进入快照原子回调', async () => {
  const openSnapshot = vi.fn(),
    onProject = vi.fn();
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    expect(options.method ?? 'GET').toBe('GET');
    if (path.startsWith('/api/v1/projects/management/'))
      return response(managementPage);
    if (path === '/api/v1/projects/activity/')
      return response({ active: [], recent: [] });
    if (path.startsWith(`/api/v1/projects/${projectId}/snapshots/`))
      return response({
        count: 1,
        next: null,
        previous: null,
        results: [snapshot],
      });
    throw new Error(`未预期请求 ${path}`);
  });
  vi.stubGlobal('fetch', fetcher);
  setup(
    <MainlineProjects
      projectId={null}
      snapshotId={null}
      project={null}
      onProject={onProject}
      onSnapshot={vi.fn()}
      onSubmitted={vi.fn()}
      onDelete={vi.fn()}
      onOpenSnapshot={openSnapshot}
    />,
  );
  await screen.findByRole('button', { name: owner.name });
  expect(
    screen.getByText('TypeScript', {
      selector: '.project-technology-tags > span',
    }).textContent,
  ).toContain('语言');
  expect(screen.queryByText('React')).toBeNull();
  fireEvent.change(screen.getByLabelText('项目排序'), {
    target: { value: 'name' },
  });
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(([path]) => path.includes('ordering=name')),
    ).toBe(true),
  );
  fireEvent.change(screen.getByLabelText('项目技术'), {
    target: { value: 'TypeScript' },
  });
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(([path]) =>
        path.includes('technology=TypeScript'),
      ),
    ).toBe(true),
  );
  fireEvent.click(screen.getByRole('button', { name: owner.name }));
  await screen.findByText('版本一');
  expect(onProject).not.toHaveBeenCalled();
  fireEvent.click(screen.getAllByRole('button', { name: '进入工作区' })[0]!);
  expect(openSnapshot).toHaveBeenCalledWith(projectId, snapshot.id);
});

test('创建空白项目是显式幂等POST，导入弹窗关闭与重开保留草稿', async () => {
  const onProject = vi.fn();
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (path.startsWith('/api/v1/projects/management/'))
      return response({ ...managementPage, count: 0, results: [] });
    if (path === '/api/v1/projects/activity/')
      return response({ active: [], recent: [] });
    if (path === '/api/v1/csrf/') return response({ csrf_token: 'test-token' });
    if (path === '/api/v1/projects/') {
      expect(options.method).toBe('POST');
      expect(JSON.parse(String(options.body))).toEqual({ name: '空白项目' });
      expect(
        (options.headers as Record<string, string>)['Idempotency-Key'],
      ).toMatch(/^[0-9a-f-]{36}$/);
      return response({ ...owner, name: '空白项目' });
    }
    throw new Error(`未预期请求 ${path}`);
  });
  vi.stubGlobal('fetch', fetcher);
  setup(
    <MainlineProjects
      projectId={null}
      snapshotId={null}
      project={null}
      onProject={onProject}
      onSnapshot={vi.fn()}
      onSubmitted={vi.fn()}
      onDelete={vi.fn()}
    />,
  );
  await screen.findByText('还没有项目');
  fireEvent.click(screen.getByRole('button', { name: /新建项目/ }));
  const create = screen.getByRole('dialog', { name: '新建空白项目' });
  fireEvent.change(within(create).getByLabelText('项目名称'), {
    target: { value: '空白项目' },
  });
  expect(
    fetcher.mock.calls.some(([, options]) => options.method === 'POST'),
  ).toBe(false);
  fireEvent.click(within(create).getByRole('button', { name: '创建项目' }));
  await waitFor(() => expect(onProject).toHaveBeenCalledWith(projectId));
  fireEvent.click(screen.getByRole('button', { name: '上传 ZIP 压缩包' }));
  const importing = screen.getByRole('dialog', { name: '导入项目源码' });
  fireEvent.change(within(importing).getByLabelText('项目名称'), {
    target: { value: '未提交草稿' },
  });
  fireEvent.click(
    within(importing).getByRole('button', { name: '关闭导入项目源码' }),
  );
  fireEvent.click(screen.getByRole('button', { name: '上传 ZIP 压缩包' }));
  expect(
    within(screen.getByRole('dialog', { name: '导入项目源码' })).getByLabelText(
      '项目名称',
    ),
  ).toHaveProperty('value', '未提交草稿');
});
test('默认项目名取ZIP名称，可编辑，一次表单依序创建并导入', async () => {
  const submitted = vi.fn();
  const keys: string[] = [];
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (path === '/api/v1/csrf/') return response({ csrf_token: 'test-token' });
    keys.push((options.headers as Record<string, string>)['Idempotency-Key']);
    if (path === '/api/v1/projects/') {
      expect(JSON.parse(String(options.body))).toEqual({ name: '自定名称' });
      return response({
        id: projectId,
        name: '自定名称',
        created_at: job.created_at,
      });
    }
    expect(path).toBe(`/api/v1/projects/${projectId}/imports/`);
    expect(options.body).toBeInstanceOf(FormData);
    return response(job);
  });
  vi.stubGlobal('fetch', fetcher);
  setup(<MainlineImport project={null} onSubmitted={submitted} />);
  fireEvent.change(screen.getByLabelText('选择源码 ZIP'), {
    target: { files: [new File(['zip'], 'my-project.zip')] },
  });
  expect(screen.getByLabelText('项目名称')).toHaveProperty(
    'value',
    'my-project',
  );
  fireEvent.change(screen.getByLabelText('项目名称'), {
    target: { value: '自定名称' },
  });
  fireEvent.click(screen.getByRole('button', { name: '导入并自动识别' }));
  await waitFor(() => expect(submitted).toHaveBeenCalledOnce());
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
});
test('目录采用原相对路径清单，未知文件被排除，既有项目只导入不再创建', async () => {
  const submitted = vi.fn();
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (path === '/api/v1/csrf/') return response({ csrf_token: 'test-token' });
    expect(path).toBe(`/api/v1/projects/${projectId}/folder-imports/`);
    expect((options.body as FormData).getAll('files')).toHaveLength(1);
    expect((options.body as FormData).get('manifest')).toBeInstanceOf(File);
    return response(job);
  });
  vi.stubGlobal('fetch', fetcher);
  setup(
    <MainlineImport
      project={{ id: projectId, name: '原项目', created_at: job.created_at }}
      onSubmitted={submitted}
    />,
  );
  fireEvent.click(screen.getByRole('button', { name: '源码文件夹' }));
  const source = new File(['pass'], 'views.py'),
    secret = new File(['fixture'], '.env');
  Object.defineProperty(source, 'webkitRelativePath', {
    value: 'repo/app/views.py',
  });
  Object.defineProperty(secret, 'webkitRelativePath', { value: 'repo/.env' });
  fireEvent.change(screen.getByLabelText('选择源码目录'), {
    target: { files: [source, secret] },
  });
  expect(screen.getByRole('status').textContent).toContain('排除 1');
  fireEvent.click(screen.getByRole('button', { name: '导入并自动识别' }));
  await waitFor(() => expect(submitted).toHaveBeenCalledOnce());
  expect(
    fetcher.mock.calls.filter(([path]) => path === '/api/v1/projects/'),
  ).toHaveLength(0);
});
test('删除先只读预览，确认之前零DELETE；确认后提交摘要与幂等键', async () => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    },
  });
  const onJob = vi.fn();
  const digest = 'a'.repeat(64);
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (path === '/api/v1/csrf/') return response({ csrf_token: 'test-token' });
    if (path.endsWith('/deletion-preview/'))
      return response({
        target_type: 'project',
        target_id: projectId,
        project_id: projectId,
        object_name: '原项目',
        scope: {
          snapshots: 1,
          files: 2,
          analyses: 0,
          source_scans: 0,
          explanations: 0,
          attempts: 0,
          lab_runs: 0,
          comparisons: 0,
        },
        receiving: false,
        confirmation_digest: digest,
        can_delete: true,
        busy_jobs: [],
      });
    expect(options.method).toBe('DELETE');
    expect(JSON.parse(String(options.body))).toEqual({
      confirmation_digest: digest,
    });
    expect(
      (options.headers as Record<string, string>)['Idempotency-Key'],
    ).toMatch(/^[0-9a-f-]{36}$/);
    return response({ ...job, kind: 'delete' });
  });
  vi.stubGlobal('fetch', fetcher);
  setup(<DeletionControl kind="project" id={projectId} onJob={onJob} />);
  fireEvent.click(screen.getByRole('button', { name: '删除项目' }));
  const submit = await screen.findByRole('button', { name: '提交永久删除' });
  expect(submit).toHaveProperty('disabled', true);
  expect(
    fetcher.mock.calls.some(([, options]) => options.method === 'DELETE'),
  ).toBe(false);
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(submit);
  await waitFor(() => expect(onJob).toHaveBeenCalledOnce());
});
