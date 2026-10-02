import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { Snapshot, SourceFile } from '../shared/api/generated/schema';
import { WorkbenchPage } from './WorkspaceModulePages';

const project = {
  id: 'project',
  name: '任务簿学习',
  created_at: '2026-10-02T00:00:00Z',
};
const snapshot: Snapshot = {
  id: 'snapshot',
  project_id: project.id,
  job_id: 'job',
  name: '第一次导入',
  created_at: project.created_at,
  source_extensions: ['.py', '.tsx'],
  summary: {
    entries: 2,
    accepted: 2,
    excluded: 0,
    skipped: 0,
    rejected: 0,
    declared_bytes: 2,
    extracted_bytes: 2,
    reasons: {},
  },
};
const files: SourceFile[] = ['backend/views.py', 'frontend/TaskBoard.tsx'].map(
  (file_path, index) => ({
    id: String(index),
    snapshot_id: snapshot.id,
    file_path,
    sha256: 'a'.repeat(64),
    size_bytes: 1,
    line_count: 1,
    encoding: 'utf-8',
  }),
);
afterEach(cleanup);

test('首次进入只显示可执行的准备步骤，不展示空统计或假完成状态', () => {
  const navigate = vi.fn();
  render(
    <WorkbenchPage
      active
      project={undefined}
      snapshot={undefined}
      files={undefined}
      analysis={null}
      onSection={navigate}
    />,
  );
  expect(screen.queryByText('已接收源码')).toBeNull();
  expect(screen.getByRole('button', { name: '导入源码快照' })).toHaveProperty(
    'disabled',
    true,
  );
  expect(screen.getByRole('button', { name: '选择静态分析' })).toHaveProperty(
    'disabled',
    true,
  );
  expect(screen.getAllByText('当前步骤')).toHaveLength(1);
  expect(navigate).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '创建或打开项目' }));
  expect(navigate).toHaveBeenLastCalledWith('import');
  fireEvent.click(screen.getByRole('button', { name: '先浏览知识卡片' }));
  expect(navigate).toHaveBeenLastCalledWith('learning');
});

test('仅有项目时引导导入，不提前开放分析步骤', () => {
  const navigate = vi.fn();
  render(
    <WorkbenchPage
      active
      project={project}
      snapshot={undefined}
      files={undefined}
      analysis={null}
      onSection={navigate}
    />,
  );
  expect(screen.getByRole('heading', { name: project.name })).toBeTruthy();
  expect(screen.getByRole('button', { name: '导入源码快照' })).toHaveProperty(
    'disabled',
    false,
  );
  expect(screen.getByRole('button', { name: '选择静态分析' })).toHaveProperty(
    'disabled',
    true,
  );
  fireEvent.click(screen.getByRole('button', { name: '导入源码 ZIP' }));
  expect(navigate).toHaveBeenCalledWith('import');
});

test.each([null, 'analysis'])(
  '快照就绪后显示真实摘要，分析选择为 %s 时只导航不自动提交',
  (analysis) => {
    const navigate = vi.fn();
    render(
      <WorkbenchPage
        active
        project={project}
        snapshot={snapshot}
        files={files}
        analysis={analysis}
        onSection={navigate}
      />,
    );
    expect(screen.getByText(snapshot.name)).toBeTruthy();
    expect(screen.getByText('已接收源码')).toBeTruthy();
    expect(screen.queryByText('未读取')).toBeNull();
    expect(navigate).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole('button', {
        name: analysis ? '继续阅读 API' : '选择根路由并分析',
      }),
    );
    expect(navigate).toHaveBeenLastCalledWith('api');
    fireEvent.click(screen.getByRole('button', { name: '打开源码阅读' }));
    expect(navigate).toHaveBeenLastCalledWith('source');
  },
);

test.each(['loading', 'unavailable'] as const)(
  '%s 时不把读取中的或无效的资源当成首次使用',
  (state) => {
    render(
      <WorkbenchPage
        active
        project={undefined}
        snapshot={undefined}
        files={undefined}
        analysis={null}
        onSection={vi.fn()}
        loading={state === 'loading'}
        unavailable={state === 'unavailable'}
      />,
    );
    expect(screen.queryByRole('button', { name: '创建或打开项目' })).toBeNull();
    expect(screen.queryByRole('region', { name: '项目准备步骤' })).toBeNull();
    if (state === 'loading')
      expect(screen.getByRole('status').textContent).toContain('读取完成后');
    else
      expect(screen.getByRole('button', { name: '重新选择项目' })).toBeTruthy();
  },
);
