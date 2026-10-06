import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { SourceRef } from '../shared/api/generated/schema';
import { WorkspacePage } from './WorkspacePage';
const state = vi.hoisted(() => ({
  project: '11111111-1111-4111-8111-111111111111',
  snapshot: '22222222-2222-4222-8222-222222222222',
  analysis: '33333333-3333-4333-8333-333333333333',
  scan: '44444444-4444-4444-8444-444444444444',
  job: '55555555-5555-4555-8555-555555555555',
  preparation: 'ready',
  analysisReady: true,
  getProject: vi.fn(),
  getSnapshot: vi.fn(),
  scanSnapshot: vi.fn(),
  submitAnalysis: vi.fn(),
  getJob: vi.fn(),
  logProps: vi.fn(),
  snapshotNameForm: vi.fn(),
}));
const source = (): SourceRef => ({
  snapshot_id: state.snapshot,
  file_path: 'app/views.py',
  start_line: 8,
  end_line: 12,
});
vi.mock('../features/projects', () => ({
  getProject: (...args: unknown[]) => state.getProject(...args),
  listFiles: vi.fn(async () => []),
  snapshotDisplayName: () => '导入快照',
  SnapshotNameForm: ({ snapshot }: { snapshot: { id: string } }) => {
    state.snapshotNameForm(snapshot);
    return <button>命名当前快照</button>;
  },
  SourceWorkspace: ({
    reference,
    secondaryReference,
    onSecondary,
  }: {
    reference: SourceRef | null;
    secondaryReference: SourceRef | null;
    onSecondary: (ref: SourceRef) => void;
  }) => (
    <section aria-label="双源码">
      <span>{reference?.file_path}</span>
      <span>{secondaryReference?.file_path}</span>
      <button onClick={() => onSecondary(source())}>固定源码</button>
    </section>
  ),
}));
vi.mock('../features/projects/api/mainline-api', () => ({
  getPreparedSnapshot: (...args: unknown[]) => state.getSnapshot(...args),
  scanSnapshot: (...args: unknown[]) => state.scanSnapshot(...args),
  getSourceScan: vi.fn(async () => ({
    scan_version: '1',
    root_candidates: [
      {
        file_path: 'root/urls.py',
        module: 'root.urls',
        reason: '独立根候选',
        source_refs: [],
      },
    ],
  })),
}));
vi.mock('../features/projects/MainlineProjects', () => ({
  MainlineProjects: () => (
    <label>
      导入草稿
      <input defaultValue="未提交名称" />
    </label>
  ),
}));
vi.mock('../features/analysis', () => ({
  getAnalysis: vi.fn(async () => ({
    id: state.analysis,
    snapshot_id: state.snapshot,
  })),
  AnalysisBrowser: ({
    onEndpoint,
    onSource,
  }: {
    onEndpoint: (endpoint: number) => void;
    onSource: (ref: SourceRef) => void;
  }) => (
    <section aria-label="接口面板">
      <button onClick={() => onEndpoint(0)}>选择接口</button>
      <button onClick={() => onSource(source())}>定位处理器</button>
    </section>
  ),
}));
vi.mock('../features/analysis/api/analysis-api', () => ({
  submitAnalysis: (...args: unknown[]) => state.submitAnalysis(...args),
}));
vi.mock('../features/analysis/RelationsPanel', () => ({
  RelationsPanel: () => <p>共享关系图</p>,
}));
vi.mock('../features/learning/SnapshotKnowledge', () => ({
  SnapshotKnowledge: () => <p>快照知识</p>,
}));
vi.mock('../features/explanations', () => ({
  ExplanationPanel: () => (
    <label>
      讲解草稿
      <input defaultValue="保留预览选择" />
    </label>
  ),
}));
vi.mock('../features/jobs', () => ({
  getJob: (...args: unknown[]) => state.getJob(...args),
}));
vi.mock('../features/jobs/MainlineTask', () => ({
  MainlineTask: () => <p>当前操作</p>,
}));
vi.mock('../features/jobs/OperationLogs', () => ({
  OperationLogs: (props: { jobId: string | null }) => {
    state.logProps(props);
    return <p>日志任务 {props.jobId}</p>;
  },
}));
vi.mock('./WorkspaceSearch', () => ({
  WorkspaceSearch: () => <input aria-label="全局搜索" />,
}));
function open(search = '') {
  window.history.replaceState(null, '', '/' + search);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <WorkspacePage />
    </QueryClientProvider>,
  );
  return client;
}
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  state.preparation = 'ready';
  state.analysisReady = true;
  state.getProject.mockResolvedValue({
    id: state.project,
    name: '项目',
    created_at: '2026-10-03T00:00:00Z',
  });
  state.getSnapshot.mockImplementation(async () => ({
    id: state.snapshot,
    project_id: state.project,
    name: '',
    job_id: state.job,
    created_at: '2026-10-03T00:00:00Z',
    source_extensions: ['.py'],
    summary: { accepted: 2 },
    preparation_status: state.preparation,
    source_scan_id: state.scan,
    scan_job_id: null,
    analysis_job_id: null,
    analysis_id: state.analysisReady ? state.analysis : null,
  }));
  state.getJob.mockResolvedValue({
    id: state.job,
    kind: 'delete',
    status: 'succeeded',
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const context = () => `?project=${state.project}&snapshot=${state.snapshot}`;

test.each([
  { label: '普通项目名', name: '项目' },
  {
    label: '长项目名',
    name: '用于核对完整标题与单行布局的长项目名称'.repeat(20),
  },
])('源码面板以$label作为唯一标题，不挂载快照命名', async ({ name }) => {
  state.getProject.mockResolvedValue({
    id: state.project,
    name,
    created_at: '2026-10-03T00:00:00Z',
  });
  open(context() + '&section=source');
  const heading = await screen.findByRole('heading', { level: 1, name });
  const header = heading.closest('header')!;
  expect(heading.getAttribute('title')).toBe(name);
  expect(heading.textContent).toBe(name);
  expect(header.children).toHaveLength(1);
  expect(within(header).getAllByRole('heading')).toEqual([heading]);
  expect(within(header).queryByText(/导入快照/)).toBeNull();
  expect(within(header).queryByRole('status')).toBeNull();
  expect(within(header).queryByRole('heading', { name: '源码' })).toBeNull();
  expect(screen.queryByRole('button', { name: '命名当前快照' })).toBeNull();
  expect(state.snapshotNameForm).not.toHaveBeenCalled();
});

test.each([
  ['api', '接口'],
  ['graph', '关系'],
  ['learning', '知识'],
  ['explanation', '讲解'],
])(
  '%s 面板保留快照、状态与命名，返回源码后移除命名入口',
  async (section, label) => {
    open(context() + `&section=${section}`);
    const heading = await screen.findByRole('heading', {
      level: 1,
      name: label,
    });
    const header = heading.closest('header')!;
    expect(within(header).getByText('项目 / 导入快照')).toBeTruthy();
    expect(within(header).getByRole('status').textContent).toBe(
      '自动识别完成 · 2 个文件',
    );
    expect(
      within(header).getByRole('button', { name: '命名当前快照' }),
    ).toBeTruthy();
    expect(state.snapshotNameForm).toHaveBeenCalledWith(
      expect.objectContaining({ id: state.snapshot }),
    );
    fireEvent.click(
      within(screen.getByRole('navigation', { name: '工作区面板' })).getByRole(
        'button',
        { name: '源码' },
      ),
    );
    expect(
      await screen.findByRole('heading', { level: 1, name: '项目' }),
    ).toBeTruthy();
    expect(screen.queryByRole('button', { name: '命名当前快照' })).toBeNull();
  },
);

test('操作日志不继承工作区项目筛选上下文', () => {
  open(context() + '&section=jobs');
  expect(state.logProps).toHaveBeenCalled();
  expect(state.logProps.mock.calls.at(-1)?.[0]).not.toHaveProperty('projectId');
});
test('仅三个主入口，无课程、通知、练习和独立检查入口；切换保留草稿', () => {
  open();
  const nav = screen.getByRole('navigation', { name: '主分类导航' });
  expect(
    within(nav)
      .getAllByRole('button')
      .map((button) => button.textContent?.trim()),
  ).toEqual(['项目管理', '项目工作区', '操作日志']);
  expect(screen.queryByRole('textbox', { name: '全局搜索' })).toBeNull();
  expect(document.querySelector('.app-header input')).toBeNull();
  const draft = screen.getByLabelText('导入草稿');
  fireEvent.change(draft, { target: { value: '我的项目' } });
  fireEvent.click(within(nav).getByRole('button', { name: '操作日志' }));
  fireEvent.click(within(nav).getByRole('button', { name: '项目管理' }));
  expect(screen.getByLabelText('导入草稿')).toBe(draft);
  expect(draft).toHaveProperty('value', '我的项目');
});
test('唯一根已发布分析自动恢复，无需用户再次选择；接口与双源码 URL 联动', async () => {
  open(context() + '&section=source');
  await waitFor(() =>
    expect(new URLSearchParams(window.location.search).get('analysis')).toBe(
      state.analysis,
    ),
  );
  fireEvent.click(await screen.findByRole('button', { name: '接口' }));
  fireEvent.click(await screen.findByRole('button', { name: '选择接口' }));
  expect(new URLSearchParams(window.location.search).get('endpoint')).toBe('0');
  fireEvent.click(screen.getByRole('button', { name: '定位处理器' }));
  expect(new URLSearchParams(window.location.search).get('file')).toBe(
    'app/views.py',
  );
  fireEvent.click(screen.getByRole('button', { name: '固定源码' }));
  expect(new URLSearchParams(window.location.search).get('file2')).toBe(
    'app/views.py',
  );
});
test('无根也能进入知识；讲解单实例切换保留草稿，不自动模型提交', async () => {
  state.preparation = 'no_root';
  state.analysisReady = false;
  open(context() + '&section=source');
  expect(
    await screen.findByText(/当前规则未发现可静态确定的 Django 根路由/),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: '知识' }));
  expect(screen.getByText('快照知识')).toBeTruthy();
  expect(state.submitAnalysis).not.toHaveBeenCalled();
});
test('多根只展示有依据的候选，显式选择时才提交接口分析', async () => {
  state.preparation = 'needs_root';
  state.analysisReady = false;
  open(context() + '&section=source');
  expect(await screen.findByText('独立根候选')).toBeTruthy();
  expect(state.submitAnalysis).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '选择此根路由' }));
  await waitFor(() =>
    expect(state.submitAnalysis).toHaveBeenCalledWith(
      state.snapshot,
      'root/urls.py',
      expect.any(String),
      expect.any(AbortSignal),
    ),
  );
});
test.each(['labs', 'comparison', 'impact', 'system'])(
  '旧 %s 链接明确退役，保持旧 URL 不跳无关模块',
  (section) => {
    open(`?section=${section}`);
    expect(screen.getByRole('heading', { name: '此功能已退役' })).toBeTruthy();
    expect(new URLSearchParams(window.location.search).get('section')).toBe(
      section,
    );
  },
);
test('旧课程 URL 显示退役说明；非法引用不能触发源对象请求', () => {
  open(`?section=learning&course=${state.scan}`);
  expect(screen.getByRole('heading', { name: '此功能已退役' })).toBeTruthy();
});
test('删除成功清除当前选择与源码缓存，日志任务仍可读取且不导航循环', async () => {
  const client = open(context() + `&job=${state.job}&section=jobs`);
  client.setQueryData(['projects', 'files', state.snapshot], ['不能保留']);
  await waitFor(() =>
    expect(
      new URLSearchParams(window.location.search).get('snapshot'),
    ).toBeNull(),
  );
  expect(new URLSearchParams(window.location.search).get('job')).toBe(
    state.job,
  );
  expect(
    client.getQueryData(['projects', 'files', state.snapshot]),
  ).toBeUndefined();
  expect(await screen.findByText(`日志任务 ${state.job}`)).toBeTruthy();
});
test('无效地址明确拒绝，并保留项目管理恢复入口', () => {
  open('?project=bad&snapshot=bad');
  expect(screen.getByRole('heading', { name: '工作区地址无效' })).toBeTruthy();
  expect(state.getProject).not.toHaveBeenCalled();
});
