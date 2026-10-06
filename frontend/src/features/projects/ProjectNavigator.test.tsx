import { useState } from 'react';
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
import { ProjectNavigator } from './ProjectNavigator';

const firstProject = '00000000-0000-0000-0000-000000000001';
const secondProject = '00000000-0000-0000-0000-000000000002';
const snapshot = '00000000-0000-0000-0000-000000000003';

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

test('紧凑项目与快照记录保持选择、真实文件数及创建草稿，没有隐式写入', async () => {
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    expect(options.method ?? 'GET').toBe('GET');
    const results =
      path === '/api/v1/projects/?page=1&page_size=20'
        ? [
            {
              id: firstProject,
              name: '任务簿项目',
              created_at: '2026-10-03T00:00:00Z',
            },
            {
              id: secondProject,
              name: '另一个项目',
              created_at: '2026-10-03T00:00:00Z',
            },
          ]
        : path.includes(firstProject)
          ? [
              {
                id: snapshot,
                name: '真实源码基线',
                project_id: firstProject,
                job_id: '00000000-0000-0000-0000-000000000004',
                created_at: '2026-10-03T00:00:00Z',
                source_extensions: ['.py'],
                summary: {
                  entries: 9,
                  accepted: 9,
                  excluded: 0,
                  skipped: 0,
                  rejected: 0,
                  declared_bytes: 100,
                  extracted_bytes: 100,
                  reasons: {},
                },
              },
            ]
          : [];
    return new Response(
      JSON.stringify({
        count: results.length,
        next: null,
        previous: null,
        results,
      }),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  const onSnapshot = vi.fn();
  function Harness() {
    const [project, setProject] = useState<string | null>(firstProject);
    const [selected, setSelected] = useState<string | null>(null);
    return (
      <ProjectNavigator
        projectId={project}
        snapshotId={selected}
        onProject={(id) => {
          setProject(id);
          setSelected(null);
        }}
        onSnapshot={(id) => {
          setSelected(id);
          onSnapshot(id);
        }}
      />
    );
  }
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <Harness />
    </QueryClientProvider>,
  );
  const projectButton = await screen.findByRole('button', {
    name: '任务簿项目',
  });
  expect(projectButton.getAttribute('aria-current')).toBe('true');
  const name = screen.getByRole('textbox', { name: '项目名称' });
  fireEvent.change(name, { target: { value: '还未创建的草稿' } });
  const snapshotButton = await screen.findByRole('button', {
    name: /真实源码基线.*9 个文件/,
  });
  expect(
    within(screen.getByRole('table', { name: '快照清单' })).getByText(
      '9 个文件',
    ),
  ).toBeTruthy();
  fireEvent.click(snapshotButton);
  expect(onSnapshot).toHaveBeenCalledWith(snapshot);
  expect(snapshotButton.getAttribute('aria-current')).toBe('true');
  fireEvent.click(screen.getByRole('button', { name: '另一个项目' }));
  await screen.findByText('尚未导入快照。');
  expect(name).toHaveProperty('value', '还未创建的草稿');
  expect(
    screen
      .getByRole('button', { name: '另一个项目' })
      .getAttribute('aria-current'),
  ).toBe('true');
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
});
