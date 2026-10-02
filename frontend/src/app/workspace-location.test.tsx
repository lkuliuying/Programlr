import { afterEach, expect, test } from 'vitest';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import {
  readSelection,
  resolveWorkspaceSection,
  useWorkspaceLocation,
} from './workspace-location';

const project = '00000000-0000-0000-0000-000000000001',
  snapshot = '00000000-0000-0000-0000-000000000002',
  analysis = '00000000-0000-0000-0000-000000000003';
const base = `?project=${project}&snapshot=${snapshot}`;
afterEach(cleanup);
test('主次源码使用相同路径与行号约束，拒绝重复和缺失归属参数', () => {
  for (const suffix of ['', '2'])
    for (const fields of [
      `file${suffix}=../bad.py&start${suffix}=1&end${suffix}=2`,
      `file${suffix}=C%3A%5Cbad.py&start${suffix}=1&end${suffix}=2`,
      `file${suffix}=a.py&start${suffix}=0&end${suffix}=2`,
      `file${suffix}=a.py&start${suffix}=3&end${suffix}=2`,
      `file${suffix}=a.py&start${suffix}=1&end${suffix}=2&file${suffix}=b.py`,
      `file${suffix}=a.py&start${suffix}=1`,
    ])
      expect(readSelection(`${base}&${fields}`).invalid).toBe(true);
  expect(readSelection('?file2=a.py&start2=1&end2=2').invalid).toBe(true);
  expect(readSelection(`${base}&section=unknown`).invalid).toBe(true);
  expect(readSelection(`${base}&section=source&section=api`).invalid).toBe(
    true,
  );
});
test('旧资源链接与任务入口兼容，显式功能选择优先于旧面板', () => {
  expect(resolveWorkspaceSection(readSelection(base))).toBe('workbench');
  expect(resolveWorkspaceSection(readSelection(base), 'jobs')).toBe('jobs');
  expect(
    resolveWorkspaceSection(
      readSelection(`${base}&analysis=${analysis}&endpoint=0&panel=lab`),
    ),
  ).toBe('labs');
  expect(
    resolveWorkspaceSection(
      readSelection(
        `${base}&analysis=${analysis}&endpoint=0&panel=lab&section=source`,
      ),
    ),
  ).toBe('source');
  expect(
    resolveWorkspaceSection(readSelection(`${base}&file=a.py&start=1&end=2`)),
  ).toBe('source');
});
test('旧作答和练习入口归练习页，课程归知识页，显式源码面板保持原归属', () => {
  const context = `${base}&analysis=${analysis}&endpoint=0`;
  expect(
    resolveWorkspaceSection(readSelection(`${context}&panel=learning`)),
  ).toBe('labs');
  expect(
    resolveWorkspaceSection(
      readSelection(`${context}&panel=learning&goal=create-task`),
    ),
  ).toBe('learning');
  expect(
    resolveWorkspaceSection(
      readSelection(`${context}&panel=learning&attempt=${analysis}`),
    ),
  ).toBe('labs');
  expect(
    resolveWorkspaceSection(readSelection(`${context}&attempt=${analysis}`)),
  ).toBe('labs');
  expect(
    resolveWorkspaceSection(
      readSelection(`${context}&attempt=${analysis}&panel=source`),
    ),
  ).toBe('source');
  expect(
    resolveWorkspaceSection(
      readSelection(`${context}&attempt=${analysis}&section=learning`),
    ),
  ).toBe('learning');
});
test('两个源码位置序列化、关闭、浏览器后退与前进恢复，不丢失原有选择', async () => {
  window.history.replaceState(null, '', '/' + base);
  const { result } = renderHook(useWorkspaceLocation);
  const first = {
    snapshot_id: snapshot,
    file_path: 'backend/a.py',
    start_line: 201,
    end_line: 400,
  };
  const second = {
    snapshot_id: snapshot,
    file_path: 'frontend/b.tsx',
    start_line: 401,
    end_line: 600,
  };
  act(() =>
    result.current.navigate({
      ...result.current.selection,
      section: 'source',
      reference: first,
      secondaryReference: second,
    }),
  );
  const saved = window.location.search;
  expect(readSelection(saved).secondaryReference).toEqual(second);
  expect(readSelection(saved).reference).toEqual(first);
  act(() =>
    result.current.navigate({
      ...result.current.selection,
      secondaryReference: null,
    }),
  );
  expect(result.current.selection.secondaryReference).toBeNull();
  act(() => window.history.back());
  await waitFor(() =>
    expect(result.current.selection.secondaryReference).toEqual(second),
  );
  expect(result.current.selection.reference).toEqual(first);
  act(() => window.history.forward());
  await waitFor(() =>
    expect(result.current.selection.secondaryReference).toBeNull(),
  );
});
