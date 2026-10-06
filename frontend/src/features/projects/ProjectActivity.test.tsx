import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
  act,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectActivity, ProjectActivitySidebar } from './ProjectActivity';
import { getProjectActivity, listProjectManagement } from './api/mainline-api';
import { searchSnapshots } from './api/projects-api';

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test('窄屏状态侧栏按需读取并恢复焦点，断点切换保留同一内容且关闭后停止轮询', async () => {
  vi.useFakeTimers();
  vi.stubGlobal('innerWidth', 1279);
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
  const fetcher = vi.fn(async () => reply({ active: [], recent: [] }));
  vi.stubGlobal('fetch', fetcher);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <ProjectActivitySidebar active onOpenSnapshot={vi.fn()} />
    </QueryClientProvider>,
  );
  const content = document.querySelector('.project-management-aside');
  const trigger = screen.getByRole('button', { name: '导入状态与帮助' });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(6000);
  });
  expect(fetcher).not.toHaveBeenCalled();
  trigger.focus();
  fireEvent.click(trigger);
  const drawer = screen.getByRole('dialog', { name: '导入状态与帮助' });
  expect(document.activeElement).toBe(
    within(drawer).getByRole('button', { name: '关闭' }),
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10);
  });
  expect(fetcher).toHaveBeenCalledOnce();
  const help = within(drawer)
    .getByText('支持哪些源码与项目？')
    .closest('details')!;
  fireEvent.click(within(drawer).getByText('支持哪些源码与项目？'));
  expect(help.open).toBe(true);
  fireEvent(drawer, new Event('cancel', { cancelable: true }));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(16000);
  });
  expect(fetcher).toHaveBeenCalledOnce();
  expect(document.activeElement).toBe(trigger);
  expect(screen.queryByRole('dialog')).toBeNull();
  fireEvent.click(trigger);
  expect(help.open).toBe(true);
  act(() => {
    vi.stubGlobal('innerWidth', 1280);
    fireEvent(window, new Event('resize'));
  });
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(document.querySelector('.project-management-aside')).toBe(content);
  expect(document.querySelectorAll('.project-management-aside')).toHaveLength(
    1,
  );
  expect(help.open).toBe(true);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(5100);
  });
  expect(fetcher.mock.calls.length).toBeGreaterThan(1);
  const calls = fetcher.mock.calls.length;
  act(() => {
    vi.stubGlobal('innerWidth', 1279);
    fireEvent(window, new Event('resize'));
  });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(16000);
  });
  expect(fetcher).toHaveBeenCalledTimes(calls);
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(document.querySelector('.project-management-aside')).toBe(content);
});

test('离开项目管理后停止活动轮询，返回时恢复读取', async () => {
  vi.useFakeTimers();
  const fetcher = vi.fn(async () => reply({ active: [], recent: [] }));
  vi.stubGlobal('fetch', fetcher);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={client}>
      <ProjectActivity active={false} onOpenSnapshot={vi.fn()} />
    </QueryClientProvider>,
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(6000);
  });
  expect(fetcher).not.toHaveBeenCalled();
  view.rerender(
    <QueryClientProvider client={client}>
      <ProjectActivity active onOpenSnapshot={vi.fn()} />
    </QueryClientProvider>,
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10);
  });
  expect(fetcher).toHaveBeenCalledOnce();
  view.rerender(
    <QueryClientProvider client={client}>
      <ProjectActivity active={false} onOpenSnapshot={vi.fn()} />
    </QueryClientProvider>,
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(16000);
  });
  expect(fetcher).toHaveBeenCalledOnce();
});
const project = {
  id: '11111111-1111-4111-8111-111111111111',
  name: '状态项目',
  created_at: '2026-10-04T00:00:00Z',
};
const job = {
  id: '22222222-2222-4222-8222-222222222222',
  kind: 'source_scan',
  status: 'succeeded',
  stage: 'completed',
  snapshot_id: '33333333-3333-4333-8333-333333333333',
  previous_job_id: null,
  parent_job_id: null,
  progress: null,
  result_deleted: false,
  result_deleted_at: null,
  source_kind: '',
  result_url: '/api/v1/source-scans/66666666-6666-4666-8666-666666666666/',
  error: null,
  created_at: project.created_at,
  updated_at: project.created_at,
};
const snapshot = {
  id: job.snapshot_id,
  name: '候选版本',
  project_id: project.id,
  job_id: job.id,
  created_at: project.created_at,
  preparation_status: 'needs_root',
  source_scan_id: null,
  scan_job_id: job.id,
  analysis_job_id: null,
  analysis_id: null,
  source_extensions: ['.py'],
  source_manifest_names: [],
  summary: {
    entries: 1,
    accepted: 1,
    excluded: 0,
    skipped: 0,
    rejected: 0,
    declared_bytes: 1,
    extracted_bytes: 1,
    reasons: {},
  },
};
const item = {
  project,
  snapshot,
  status: 'needs_root',
  root_count: 2,
  endpoint_count: null,
  stages: [
    {
      kind: 'source_scan',
      job,
      events: [
        {
          at: project.created_at,
          result: 'succeeded',
          stage: 'completed',
          error_code: '',
        },
      ],
    },
  ],
};
const reply = (value: unknown) => new Response(JSON.stringify(value));

test('根选择保持待处理，无根完成明确只读能力，执行记录取服务端时间', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      reply({
        active: [item],
        recent: [
          {
            ...item,
            status: 'no_root',
            root_count: 0,
            snapshot: {
              ...snapshot,
              id: '44444444-4444-4444-8444-444444444444',
              name: '无根版本',
            },
            stages: [],
          },
        ],
      }),
    ),
  );
  const onOpenSnapshot = vi.fn();
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <ProjectActivity onOpenSnapshot={onOpenSnapshot} />
    </QueryClientProvider>,
  );
  await screen.findByText('等待选择根路由');
  expect(screen.getByText(/发现 2 个候选根/)).toBeTruthy();
  expect(screen.getByText('源码与知识已可阅读；未执行接口分析。')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: /选择根路由/ }));
  expect(onOpenSnapshot).toHaveBeenCalledWith(project.id, snapshot.id);
  const activity = screen.getByLabelText('导入状态和帮助');
  expect(within(activity).queryByText(/68%|100%|最近成功率/)).toBeNull();
  fireEvent.click(screen.getAllByText('查看执行记录')[0]!);
  expect(screen.getByText(/2026\/10\/04/)).toBeTruthy();
});

test('项目投影与全局快照搜索校验嵌套归属和分页链接', async () => {
  const signal = new AbortController().signal;
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      reply({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            project,
            snapshot: {
              ...snapshot,
              project_id: '55555555-5555-4555-8555-555555555555',
            },
          },
        ],
      }),
    ),
  );
  await expect(searchSnapshots(1, signal, '候选')).rejects.toThrow(
    '响应结构或资源归属无效',
  );
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      reply({
        count: 1,
        next: '/api/v1/other/?page=2&page_size=10',
        previous: null,
        technologies: [],
        results: [],
      }),
    ),
  );
  await expect(listProjectManagement(1, signal)).rejects.toThrow(
    '响应结构或资源归属无效',
  );
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      reply({
        active: [
          {
            ...item,
            stages: [
              {
                ...item.stages[0],
                job: { ...job, kind: 'delete', result_url: null },
              },
            ],
          },
        ],
        recent: [],
      }),
    ),
  );
  await expect(getProjectActivity(signal)).rejects.toThrow(
    '响应结构或资源归属无效',
  );
});
