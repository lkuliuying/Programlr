import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
import type {
  Analysis,
  Project,
  Snapshot,
} from '../shared/api/generated/schema';
import { WorkbenchDashboard } from './WorkbenchDashboard';
import type { WorkbenchDashboardProps } from './WorkbenchDashboard';

const project: Project = {
  id: 'project',
  name: '真实学习项目',
  created_at: '2026-10-03T00:00:00Z',
};
const snapshot: Snapshot = {
  id: 'snapshot',
  project_id: project.id,
  job_id: 'import-job',
  name: '学习快照',
  created_at: project.created_at,
  source_extensions: ['.py', '.tsx'],
  source_manifest_names: [],
  preparation_status: 'pending',
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
    declared_bytes: 30,
    extracted_bytes: 30,
    reasons: {},
  },
};
const analysis: Analysis = {
  id: 'analysis',
  snapshot_id: snapshot.id,
  job_id: 'analysis-job',
  root_urlconf: 'config.urls',
  source_scan_id: null,
  rule_version: '1',
  created_at: project.created_at,
  frontend: null,
  coverage: {
    python_files: 1,
    parsed_files: 1,
    syntax_failed_files: 0,
    skipped_files: 0,
    endpoint_count: 0,
    diagnostic_count: 0,
    complete: true,
    limitations: [],
  },
};
function props(
  overrides: Partial<WorkbenchDashboardProps> = {},
): WorkbenchDashboardProps {
  return {
    recentContent: <p>已加载的最近项目</p>,
    learningContent: <p>已加载的课程进度</p>,
    metrics: [],
    onSection: vi.fn(),
    onCreateProject: vi.fn(),
    ...overrides,
  };
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test.each([
  ['首次进入', {}, '创建或打开项目', 0],
  ['仅项目', { project }, '导入源码 ZIP', 1],
  ['项目和快照', { project, snapshot }, '选择根路由并分析', 2],
  ['当前快照的已加载分析', { project, snapshot, analysis }, '继续阅读 API', 3],
  [
    '其他快照的分析',
    {
      project,
      snapshot,
      analysis: { ...analysis, snapshot_id: 'other-snapshot' },
    },
    '选择根路由并分析',
    2,
  ],
  [
    '其他项目的快照',
    {
      project,
      snapshot: { ...snapshot, project_id: 'other-project' },
      analysis,
    },
    '导入源码 ZIP',
    1,
  ],
] as const)(
  '%s 只由实际加载且关联的资源决定准备状态',
  (_, data, action, ready) => {
    render(<WorkbenchDashboard {...props(data)} />);
    const hero = screen.getByRole('region', { name: '项目探索入口' });
    expect(within(hero).getByRole('button', { name: action })).toHaveProperty(
      'disabled',
      false,
    );
    const preparation = screen.getByRole('region', { name: '项目准备步骤' });
    expect(within(preparation).queryAllByText('已选择')).toHaveLength(ready);
    expect(
      within(preparation).getByRole('button', { name: '导入源码快照' }),
    ).toHaveProperty('disabled', ready < 1);
    expect(
      within(preparation).getByRole('button', { name: '选择静态分析' }),
    ).toHaveProperty('disabled', ready < 2);
    expect(screen.getByText('已加载的最近项目')).toBeTruthy();
    expect(screen.getByText('已加载的课程进度')).toBeTruthy();
  },
);

test('加载中和读取失败不把旧分析显示为已准备，失败入口可以重新选择', () => {
  const data = props({ project, snapshot, analysis, loading: true });
  const view = render(<WorkbenchDashboard {...data} />);
  expect(screen.getByRole('status').textContent).toContain('正在读取');
  expect(screen.getByRole('button', { name: '创建或打开项目' })).toHaveProperty(
    'disabled',
    true,
  );
  expect(screen.queryAllByText('已选择')).toHaveLength(0);
  view.rerender(<WorkbenchDashboard {...data} loading={false} unavailable />);
  expect(screen.getByRole('alert').textContent).toContain('暂不可用');
  expect(screen.queryAllByText('已选择')).toHaveLength(0);
  fireEvent.click(screen.getByRole('button', { name: '重新选择项目' }));
  expect(data.onSection).toHaveBeenCalledExactlyOnceWith('import');
});

test('数据概览区分未读取和真实零值，拒绝负数与非有限值', () => {
  render(
    <WorkbenchDashboard
      {...props({
        metrics: [
          {
            key: 'unknown',
            label: '未读取指标',
            value: null,
            description: '当前快照',
          },
          { key: 'zero', label: '零值指标', value: 0, description: '当前分析' },
          {
            key: 'invalid',
            label: '非法指标',
            value: -1,
            description: '当前分析',
          },
          {
            key: 'infinite',
            label: '无穷指标',
            value: Infinity,
            description: '当前分析',
          },
        ],
      })}
    />,
  );
  const overview = screen.getByRole('region', { name: '数据概览' });
  expect(within(overview).getAllByText('未读取')).toHaveLength(3);
  expect(within(overview).getByText('0')).toBeTruthy();
  expect(overview.querySelectorAll('dt')).toHaveLength(4);
});

test('首页入口只通知已有导航和创建回调，不发请求，插槽与草稿保持单实例', () => {
  const fetch = vi.fn();
  vi.stubGlobal('fetch', fetch);
  const data = props({
    project,
    snapshot,
    analysis,
    recentContent: (
      <label>
        项目草稿
        <input defaultValue="" />
      </label>
    ),
  });
  const view = render(<WorkbenchDashboard {...data} />);
  const draft = screen.getByRole('textbox', { name: '项目草稿' });
  fireEvent.change(draft, { target: { value: '保留这段内容' } });
  fireEvent.click(screen.getByRole('button', { name: '继续阅读 API' }));
  fireEvent.click(screen.getByRole('button', { name: '浏览知识卡片' }));
  const quick = screen.getByRole('region', { name: '快捷入口' });
  for (const button of within(quick).getAllByRole('button'))
    fireEvent.click(button);
  fireEvent.click(screen.getByRole('button', { name: '全部项目' }));
  fireEvent.click(screen.getByRole('button', { name: '创建新项目' }));
  expect(data.onSection).toHaveBeenCalledTimes(7);
  expect(data.onSection).toHaveBeenNthCalledWith(1, 'api');
  expect(data.onSection).toHaveBeenNthCalledWith(2, 'learning');
  expect(data.onSection).toHaveBeenNthCalledWith(3, 'import');
  expect(data.onSection).toHaveBeenNthCalledWith(4, 'import');
  expect(data.onSection).toHaveBeenNthCalledWith(5, 'api');
  expect(data.onSection).toHaveBeenNthCalledWith(6, 'learning');
  expect(data.onSection).toHaveBeenNthCalledWith(7, 'import');
  expect(data.onCreateProject).toHaveBeenCalledExactlyOnceWith();
  view.rerender(<WorkbenchDashboard {...data} loading />);
  expect(screen.getByRole('textbox', { name: '项目草稿' })).toBe(draft);
  expect(draft).toHaveProperty('value', '保留这段内容');
  expect(fetch).not.toHaveBeenCalled();
  expect(screen.queryByRole('img')).toBeNull();
});
