import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useWorkspaceLocation } from '../../app/workspace-location';
import { FileTree, SourceWorkspace } from './SourceWorkspace';
import { highlightSource } from './source-highlight';
const project = '00000000-0000-0000-0000-000000000001',
  snapshot = '00000000-0000-0000-0000-000000000002';
const files = ['backend/a.py', 'frontend/b.tsx'].map((path, i) => ({
  id: `00000000-0000-0000-0000-00000000000${i + 3}`,
  snapshot_id: snapshot,
  file_path: path,
  sha256: 'a'.repeat(64),
  size_bytes: 600,
  line_count: 450,
  encoding: 'utf-8',
}));
function Harness({ snapshotName }: { snapshotName?: string }) {
  const { selection, navigate } = useWorkspaceLocation();
  return (
    <SourceWorkspace
      files={files}
      snapshotId={snapshot}
      snapshotName={snapshotName}
      search=""
      reference={selection.reference}
      secondaryReference={selection.secondaryReference}
      onSource={(reference) => navigate({ ...selection, reference })}
      onSecondary={(secondaryReference) =>
        navigate({ ...selection, secondaryReference })
      }
    />
  );
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test('着色保留原始空行、空白、字符串与注释，不解析 HTML', () => {
  for (const text of [
    '',
    '    ',
    '  const value = "<img src=x onerror=alert(1)>"; // 同行注释',
    'def task(): # 源码注释',
    '    return "原始字符串"',
  ]) {
    const view = render(<pre>{highlightSource(text, 'entry.tsx')}</pre>);
    expect(view.container.textContent).toBe(text);
    expect(view.container.querySelector('img')).toBeNull();
    view.unmount();
  }
});
test('目录可折叠，路径筛选显示数量且固定操作携带原快照', () => {
  const onOpen = vi.fn(),
    onPin = vi.fn();
  const view = render(
    <FileTree
      files={files}
      search=""
      selected={undefined}
      onOpen={onOpen}
      onPin={onPin}
    />,
  );
  fireEvent.click(
    screen.getByRole('button', { name: /backend/, expanded: true }),
  );
  expect(screen.queryByRole('button', { name: 'a.py' })).toBeNull();
  view.rerender(
    <FileTree
      files={files}
      search="BACKEND"
      selected={undefined}
      onOpen={onOpen}
      onPin={onPin}
    />,
  );
  expect(screen.getByText('已接收源码 · 1/2')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'b.tsx' })).toBeNull();
  fireEvent.click(
    screen.getByRole('button', { name: '在第二窗口打开 backend/a.py' }),
  );
  expect(onPin).toHaveBeenCalledWith({
    snapshot_id: snapshot,
    file_path: 'backend/a.py',
    start_line: 1,
    end_line: 450,
  });
  view.rerender(
    <FileTree
      files={files}
      search="missing"
      selected={undefined}
      onOpen={onOpen}
      onPin={onPin}
    />,
  );
  expect(screen.getByText('没有匹配的文件。')).toBeTruthy();
});
test('文件树固定和关闭，双窗口独立分段并写入 URL，源码始终作为文本', async () => {
  const snapshotName = '双源码学习快照'.repeat(20);
  window.history.replaceState(
    null,
    '',
    `/?project=${project}&snapshot=${snapshot}`,
  );
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      const file = files.find((file) => path.includes(file.id))!;
      const params = new URL(path, 'http://local.test').searchParams,
        start = Number(params.get('start_line')),
        end = Number(params.get('end_line'));
      return new Response(
        JSON.stringify({
          ...file,
          start_line: start,
          end_line: end,
          content:
            Array.from({ length: end - start + 1 }, (_, i) =>
              i === 0
                ? `${file.file_path} ${start}: <script>文本</script>`
                : `const row = ${start + i}`,
            ).join('\n') + '\n',
        }),
      );
    }),
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <Harness snapshotName={snapshotName} />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'a.py' }));
  await screen.findByText(/backend\/a.py 1:/);
  fireEvent.click(
    screen.getByRole('button', { name: '在第二窗口打开 frontend/b.tsx' }),
  );
  await screen.findByText(/frontend\/b.tsx 1:/);
  const primary = screen.getByRole('region', { name: '只读源码' }),
    secondary = screen.getByRole('region', { name: '固定只读源码' });
  for (const panel of [primary, secondary]) {
    expect(within(panel).getByText(`快照 ${snapshotName} · 只读`)).toBeTruthy();
    expect(panel.querySelector('.source-meta')?.textContent).not.toContain(
      snapshot.slice(0, 8),
    );
  }
  fireEvent.click(within(secondary).getByRole('button', { name: '下一段' }));
  await screen.findByText(/frontend\/b.tsx 201:/);
  expect(new URLSearchParams(window.location.search).get('start2')).toBe('201');
  expect(within(primary).getByText(/backend\/a.py 1:/)).toBeTruthy();
  fireEvent.click(within(primary).getByRole('button', { name: '下一段' }));
  await screen.findByText(/backend\/a.py 201:/);
  expect(new URLSearchParams(window.location.search).get('start')).toBe('201');
  expect(screen.getByText(/frontend\/b.tsx 201:/)).toBeTruthy();
  expect(document.querySelector('.source-lines script')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '关闭固定源码' }));
  expect(new URLSearchParams(window.location.search).has('file2')).toBe(false);
  expect(screen.getByText(/backend\/a.py 201:/)).toBeTruthy();
});
