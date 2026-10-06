import { afterEach, expect, test, vi } from 'vitest';
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
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
const originalViewport = window.innerWidth;

function resizeEnvironment(initialWidth = 1000, viewport = 1280) {
  let width = initialWidth;
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: viewport,
  });
  vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockImplementation(
    function (this: HTMLElement) {
      return this.classList.contains('source-ide') ? width : 0;
    },
  );
  const observers: {
    callback: ResizeObserverCallback;
    target: Element | null;
    disconnect: ReturnType<typeof vi.fn>;
  }[] = [];
  class TestResizeObserver {
    record;
    constructor(callback: ResizeObserverCallback) {
      this.record = {
        callback,
        target: null as Element | null,
        disconnect: vi.fn(),
      };
      observers.push(this.record);
    }
    observe(target: Element) {
      this.record.target = target;
    }
    unobserve() {}
    disconnect() {
      this.record.disconnect();
    }
  }
  class TestPointerEvent extends MouseEvent {
    readonly pointerId: number;
    readonly isPrimary: boolean;
    constructor(type: string, options: PointerEventInit = {}) {
      super(type, options);
      this.pointerId = options.pointerId ?? 1;
      this.isPrimary = options.isPrimary ?? true;
    }
  }
  vi.stubGlobal('ResizeObserver', TestResizeObserver);
  vi.stubGlobal('PointerEvent', TestPointerEvent);
  return {
    observers,
    resize(
      nextWidth: number,
      nextViewport = window.innerWidth,
      observerOnly = false,
    ) {
      act(() => {
        width = nextWidth;
        window.innerWidth = nextViewport;
        if (!observerOnly) window.dispatchEvent(new Event('resize'));
        for (const record of observers)
          if (record.target?.classList.contains('source-ide'))
            record.callback([], {} as ResizeObserver);
      });
    },
  };
}

function resizableWorkspace() {
  const element = (
    <QueryClientProvider client={new QueryClient()}>
      <SourceWorkspace
        files={files}
        snapshotId={snapshot}
        reference={null}
        secondaryReference={null}
        onSource={vi.fn()}
        onSecondary={vi.fn()}
      />
    </QueryClientProvider>
  );
  const view = render(element);
  const handle = screen.getByRole('separator', { name: '调整项目文件树宽度' });
  const workspace = view.container.querySelector<HTMLElement>('.source-ide')!;
  const captured = new Set<number>();
  const capture = vi.fn((id: number) => captured.add(id));
  const release = vi.fn((id: number) => captured.delete(id));
  Object.assign(handle, {
    setPointerCapture: capture,
    hasPointerCapture: (id: number) => captured.has(id),
    releasePointerCapture: release,
  });
  return { view, handle, workspace, capture, release, captured, element };
}

function pointer(
  target: Node | Window,
  type: string,
  clientX: number,
  pointerId = 1,
  options: PointerEventInit = {},
) {
  fireEvent(
    target,
    new PointerEvent(type, {
      bubbles: true,
      cancelable: true,
      button: 0,
      clientX,
      pointerId,
      ...options,
    }),
  );
}

function expectTreeWidth(handle: HTMLElement, width: number) {
  expect(handle.getAttribute('aria-valuenow')).toBe(String(width));
  expect(
    handle
      .closest<HTMLElement>('.source-ide')
      ?.style.getPropertyValue('--source-tree-width'),
  ).toBe(`${width}px`);
}
function Harness({
  snapshotName,
  sourceFiles = files,
}: {
  snapshotName?: string;
  sourceFiles?: typeof files;
}) {
  const { selection, navigate } = useWorkspaceLocation();
  return (
    <SourceWorkspace
      files={sourceFiles}
      snapshotId={snapshot}
      snapshotName={snapshotName}
      reference={selection.reference}
      secondaryReference={selection.secondaryReference}
      onSource={(reference) => navigate({ ...selection, reference })}
      onSecondary={(secondaryReference) =>
        navigate({ ...selection, secondaryReference })
      }
      onCloseSource={(replacement, closeSecondary) =>
        navigate({
          ...selection,
          reference: replacement,
          ...(closeSecondary ? { secondaryReference: null } : {}),
        })
      }
    />
  );
}
function mockSourceRequests(sourceFiles = files) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      const file = sourceFiles.find((candidate) => path.includes(candidate.id));
      if (!file) throw new Error('测试请求没有匹配的源码文件');
      const parameters = new URL(path, 'http://local.test').searchParams;
      const start = Number(parameters.get('start_line'));
      const end = Number(parameters.get('end_line'));
      return new Response(
        JSON.stringify({
          ...file,
          start_line: start,
          end_line: end,
          content:
            Array.from(
              { length: end - start + 1 },
              (_, index) => `${file.file_path} ${start + index}`,
            ).join('\n') + '\n',
        }),
      );
    }),
  );
}

function sourceLine(text: string) {
  return (_content: string, element: Element | null) =>
    element?.tagName === 'PRE' && element.textContent === text;
}

function renderWorkspace(
  props: Partial<Parameters<typeof SourceWorkspace>[0]> = {},
) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <SourceWorkspace
        files={files}
        snapshotId={snapshot}
        reference={null}
        secondaryReference={null}
        onSource={vi.fn()}
        onSecondary={vi.fn()}
        {...props}
      />
    </QueryClientProvider>,
  );
}

async function expectTooltip(
  trigger: HTMLElement,
  text: string,
  focus = false,
) {
  expect(trigger.getAttribute('title')).toBeNull();
  if (focus) act(() => trigger.focus());
  else fireEvent.mouseEnter(trigger);
  expect((await screen.findByRole('tooltip')).textContent).toBe(text);
  if (focus) act(() => trigger.blur());
  else fireEvent.mouseLeave(trigger);
  // jsdom不执行CSS动画，等待组件的1000ms兜底及移出延迟，仍要求提示完整销毁。
  await waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull(), {
    timeout: 2000,
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.innerWidth = originalViewport;
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
test('目录可折叠，独立路径筛选保持且固定操作携带原快照，不显示计数', () => {
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
  expect(screen.queryByText(/已接收源码/)).toBeNull();
  expect(screen.getByRole('button', { name: 'a.py' })).toBeTruthy();
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
test('紧凑目录去掉旧标题、筛选与计数，中文提示和折叠后定位均可用', async () => {
  resizeEnvironment();
  mockSourceRequests();
  const view = renderWorkspace({
    reference: {
      snapshot_id: snapshot,
      file_path: files[0]!.file_path,
      start_line: 1,
      end_line: 450,
    },
  });
  await screen.findByText(sourceLine('backend/a.py 1'));
  expect(screen.queryByRole('heading', { name: '项目文件' })).toBeNull();
  expect(screen.queryByLabelText('筛选当前快照文件')).toBeNull();
  expect(screen.queryByPlaceholderText('输入文件路径')).toBeNull();
  expect(screen.queryByText(/已接收源码/)).toBeNull();
  expect(
    view.container.querySelector('.file-tree-panel .panel-title'),
  ).toBeNull();
  const actions = view.container.querySelector<HTMLElement>(
    '.source-tree-actions',
  )!;
  const collapse = within(actions).getByRole('button', {
    name: '折叠全部目录',
  });
  const locate = within(actions).getByRole('button', {
    name: '定位当前文件',
  });
  await expectTooltip(collapse, '折叠全部目录');
  fireEvent.click(collapse);
  expect(screen.queryByRole('button', { name: 'a.py' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'b.tsx' })).toBeNull();
  expect(
    screen.getByRole('button', { name: /backend/, expanded: false }),
  ).toBeTruthy();
  await expectTooltip(locate, '定位当前文件', true);
  fireEvent.click(locate);
  expect(
    screen.getByRole('button', { name: 'a.py' }).getAttribute('aria-current'),
  ).toBe('true');
  expect(
    screen.getByRole('button', { name: /backend/, expanded: true }),
  ).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'b.tsx' })).toBeNull();
});

test('同名文件和标签以真实相对路径提供 Tooltip，切换仍绑定原文件', async () => {
  resizeEnvironment();
  const sameNameFiles = files.map((file, index) => ({
    ...file,
    file_path: index === 0 ? 'backend/a.py' : 'frontend/a.py',
  }));
  mockSourceRequests(sameNameFiles);
  window.history.replaceState(
    null,
    '',
    `/?project=${project}&snapshot=${snapshot}`,
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <Harness sourceFiles={sameNameFiles} />
    </QueryClientProvider>,
  );
  const treeButtons = screen.getAllByRole('button', { name: 'a.py' });
  expect(treeButtons).toHaveLength(2);
  for (const [index, button] of treeButtons.entries()) {
    const path = sameNameFiles[index]!.file_path;
    expect(button.getAttribute('aria-description')).toBe(path);
    await expectTooltip(button, path);
    fireEvent.click(button);
    await screen.findByText(sourceLine(`${path} 1`));
    expect(new URLSearchParams(window.location.search).get('file')).toBe(path);
  }
  const tabs = screen.getAllByRole('tab', { name: 'a.py' });
  expect(tabs).toHaveLength(2);
  for (const [index, tab] of tabs.entries()) {
    const path = sameNameFiles[index]!.file_path;
    expect(tab.getAttribute('aria-description')).toBe(path);
    await expectTooltip(tab, path, true);
  }
  fireEvent.click(tabs[0]!);
  expect(new URLSearchParams(window.location.search).get('file')).toBe(
    'backend/a.py',
  );
  expect(tabs[0]!.getAttribute('aria-selected')).toBe('true');
  await screen.findByText(sourceLine('backend/a.py 1'));
});

test('文件标签下直接保留代码区域，分屏、代码解读和快照信息入口可用', async () => {
  resizeEnvironment();
  mockSourceRequests();
  const reference = {
    snapshot_id: snapshot,
    file_path: files[0]!.file_path,
    start_line: 1,
    end_line: 450,
  };
  const onSecondary = vi.fn();
  const onExplain = vi.fn();
  const snapshotName = '源码信息完整快照名称'.repeat(20);
  const view = renderWorkspace({
    reference,
    snapshotName,
    onSecondary,
    onExplain,
  });
  await screen.findByText(sourceLine('backend/a.py 1'));
  const editorBar =
    view.container.querySelector<HTMLElement>('.source-editor-bar')!;
  expect(
    within(editorBar).getByRole('tablist', { name: '已打开文件' }),
  ).toBeTruthy();
  expect(editorBar.nextElementSibling?.classList.contains('code-pair')).toBe(
    true,
  );
  expect(view.container.querySelector('.source-toolbar')).toBeNull();
  expect(view.container.querySelector('.code-actions')).toBeNull();
  expect(screen.queryByRole('navigation', { name: '源码路径' })).toBeNull();
  expect(screen.queryByText('主源码窗口')).toBeNull();
  fireEvent.click(within(editorBar).getByRole('button', { name: '分屏浏览' }));
  expect(onSecondary).toHaveBeenCalledExactlyOnceWith(reference);
  fireEvent.click(within(editorBar).getByRole('button', { name: '代码解读' }));
  expect(onExplain).toHaveBeenCalledOnce();
  const information = within(editorBar).getByRole('button', {
    name: '查看源码信息',
  });
  await expectTooltip(information, `快照 ${snapshotName} · 只读`, true);
  expect(
    within(screen.getByRole('region', { name: '只读源码' })).getByText(
      `快照 ${snapshotName} · 只读`,
    ),
  ).toBeTruthy();
});

test.each([
  { mode: '桌面', viewport: 1280, selected: true, target: '当前文件' },
  { mode: '桌面', viewport: 1280, selected: false, target: '首个目录' },
  { mode: '窄屏', viewport: 390, selected: true, target: '当前文件' },
  { mode: '窄屏', viewport: 390, selected: false, target: '首个目录' },
])('$mode 打开文件树后聚焦本实例$target', async ({ viewport, selected }) => {
  resizeEnvironment(1000, viewport);
  mockSourceRequests();
  const first = renderWorkspace();
  const view = renderWorkspace({
    reference: selected
      ? {
          snapshot_id: snapshot,
          file_path: files[0]!.file_path,
          start_line: 1,
          end_line: 450,
        }
      : null,
  });
  if (selected)
    await within(view.container).findByText(sourceLine('backend/a.py 1'));
  const open = within(view.container).getByRole('button', {
    name: '从文件树打开文件',
  });
  act(() => open.focus());
  fireEvent.click(open);
  const target = view.container.querySelector<HTMLElement>(
    selected ? '.tree-file[aria-current="true"]' : '.tree-folder',
  )!;
  await waitFor(() => expect(document.activeElement).toBe(target));
  expect(first.container.contains(document.activeElement)).toBe(false);
  expect(
    view.container.querySelector('.file-tree-panel')?.getAttribute('data-open'),
  ).toBe('true');
  if (viewport < 768) {
    if (selected) fireEvent.keyDown(target, { key: 'Escape' });
    else
      fireEvent.click(
        within(view.container).getByRole('button', { name: 'a.py' }),
      );
    await waitFor(() => expect(document.activeElement).toBe(open));
    expect(
      view.container
        .querySelector('.file-tree-panel')
        ?.getAttribute('data-open'),
    ).toBe('false');
  }
});

test('空文件树可打开和关闭，不可用操作禁用且焦点留在本实例', async () => {
  resizeEnvironment(1000, 390);
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  const view = renderWorkspace({ files: [] });
  expect(screen.getByText('此快照没有可读源码。')).toBeTruthy();
  for (const name of ['折叠全部目录', '定位当前文件'])
    expect(screen.getByRole('button', { name })).toHaveProperty(
      'disabled',
      true,
    );
  const open = screen.getByRole('button', { name: '从文件树打开文件' });
  act(() => open.focus());
  fireEvent.click(open);
  const treePanel =
    view.container.querySelector<HTMLElement>('.file-tree-panel')!;
  await waitFor(() => expect(document.activeElement).toBe(treePanel));
  expect(treePanel.getAttribute('data-open')).toBe('true');
  expect(treePanel.tabIndex).toBe(-1);
  fireEvent.click(screen.getByRole('button', { name: '关闭项目结构' }));
  expect(treePanel.getAttribute('data-open')).toBe('false');
  expect(document.activeElement).toBe(open);
  expect(fetcher).not.toHaveBeenCalled();
});

test('同名文件的跨快照引用不会显示当前快照的源码依据', () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  render(
    <QueryClientProvider client={new QueryClient()}>
      <SourceWorkspace
        files={files}
        snapshotId={snapshot}
        reference={{
          snapshot_id: project,
          file_path: files[0]!.file_path,
          start_line: 1,
          end_line: 1,
        }}
        secondaryReference={null}
        analysisId={project}
        onSource={vi.fn()}
        onSecondary={vi.fn()}
      />
    </QueryClientProvider>,
  );
  expect(screen.getByRole('alert').textContent).toContain('引用失效');
  expect(screen.queryByText(/相关源码依据/)).toBeNull();
  expect(fetcher).not.toHaveBeenCalled();
});

test('文件标签与分屏独立跳行并写入 URL，源码始终作为文本', async () => {
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
  fireEvent.change(within(secondary).getByRole('spinbutton'), {
    target: { value: '201' },
  });
  fireEvent.click(within(secondary).getByRole('button', { name: '跳转' }));
  await screen.findByText(/frontend\/b.tsx 201:/);
  expect(new URLSearchParams(window.location.search).get('start2')).toBe('201');
  expect(within(primary).getByText(/backend\/a.py 1:/)).toBeTruthy();
  fireEvent.change(within(primary).getByRole('spinbutton'), {
    target: { value: '201' },
  });
  fireEvent.click(within(primary).getByRole('button', { name: '跳转' }));
  await screen.findByText(/backend\/a.py 201:/);
  expect(new URLSearchParams(window.location.search).get('start')).toBe('201');
  expect(screen.getByText(/frontend\/b.tsx 201:/)).toBeTruthy();
  expect(document.querySelector('.source-lines script')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '关闭固定源码' }));
  expect(new URLSearchParams(window.location.search).has('file2')).toBe(false);
  expect(screen.getByText(/backend\/a.py 201:/)).toBeTruthy();
  expect(screen.getAllByRole('tab')).toHaveLength(2);
  fireEvent.click(
    screen.getByRole('button', { name: '关闭文件 backend/a.py' }),
  );
  expect(screen.getAllByRole('tab')).toHaveLength(1);
  expect(new URLSearchParams(window.location.search).get('file')).toBe(
    'frontend/b.tsx',
  );
  fireEvent.click(
    screen.getByRole('button', { name: '关闭文件 frontend/b.tsx' }),
  );
  expect(screen.queryAllByRole('tab')).toHaveLength(0);
  expect(new URLSearchParams(window.location.search).has('file')).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'a.py' }));
  await screen.findByText(/backend\/a.py 1:/);
  fireEvent.click(screen.getByRole('button', { name: '分屏浏览' }));
  expect(new URLSearchParams(window.location.search).get('file2')).toBe(
    'backend/a.py',
  );
  fireEvent.click(
    screen.getByRole('button', { name: '关闭文件 backend/a.py' }),
  );
  expect(new URLSearchParams(window.location.search).has('file')).toBe(false);
  expect(new URLSearchParams(window.location.search).has('file2')).toBe(false);
});

test('分隔条提供关联区域与尺寸信息，只接受主指针且捕获后可在条外拖动', () => {
  resizeEnvironment();
  const { handle, workspace, capture, release } = resizableWorkspace();
  const bodyStyle = document.body.getAttribute('style');
  expectTreeWidth(handle, 260);
  expect(handle.getAttribute('aria-orientation')).toBe('vertical');
  expect(handle.getAttribute('aria-valuemin')).toBe('180');
  expect(handle.getAttribute('aria-valuemax')).toBe('480');
  expect(handle.tabIndex).toBe(0);
  for (const id of handle.getAttribute('aria-controls')!.split(' '))
    expect(document.getElementById(id)).toBeTruthy();
  pointer(handle, 'pointerdown', 260, 4, { button: 2 });
  pointer(handle, 'pointerdown', 260, 4, { isPrimary: false });
  expect(capture).not.toHaveBeenCalled();
  pointer(handle, 'pointerdown', 260, 4);
  expect(document.activeElement).toBe(handle);
  expect(capture).toHaveBeenCalledWith(4);
  expect(workspace.dataset.treeResizing).toBe('true');
  pointer(document.body, 'pointermove', 410, 4);
  expectTreeWidth(handle, 410);
  pointer(window, 'pointermove', 100, 5);
  pointer(window, 'pointerup', 100, 5);
  pointer(window, 'pointercancel', 100, 5);
  expectTreeWidth(handle, 410);
  expect(workspace.dataset.treeResizing).toBe('true');
  pointer(window, 'pointermove', 900, 4);
  expectTreeWidth(handle, 480);
  pointer(window, 'pointermove', -100, 4);
  expectTreeWidth(handle, 180);
  pointer(window, 'pointerup', 300, 4);
  expectTreeWidth(handle, 300);
  expect(workspace.dataset.treeResizing).toBe('false');
  expect(release).toHaveBeenCalledExactlyOnceWith(4);
  pointer(window, 'pointermove', 900, 4);
  expectTreeWidth(handle, 300);
  expect(document.body.getAttribute('style')).toBe(bodyStyle);
});

test('分隔条方向键支持步长与动态上下界，不拦截其他导航键', () => {
  resizeEnvironment(700);
  const { handle } = resizableWorkspace();
  expect(handle.getAttribute('aria-valuemax')).toBe('368');
  fireEvent.keyDown(handle, { key: 'ArrowRight' });
  expectTreeWidth(handle, 270);
  fireEvent.keyDown(handle, { key: 'ArrowRight', shiftKey: true });
  expectTreeWidth(handle, 310);
  fireEvent.keyDown(handle, { key: 'ArrowLeft' });
  expectTreeWidth(handle, 300);
  fireEvent.keyDown(handle, { key: 'ArrowLeft', shiftKey: true });
  expectTreeWidth(handle, 260);
  fireEvent.keyDown(handle, { key: 'Home' });
  expectTreeWidth(handle, 180);
  fireEvent.keyDown(handle, { key: 'ArrowLeft' });
  expectTreeWidth(handle, 180);
  fireEvent.keyDown(handle, { key: 'End' });
  expectTreeWidth(handle, 368);
  fireEvent.keyDown(handle, { key: 'ArrowRight' });
  expectTreeWidth(handle, 368);
  const navigation = new KeyboardEvent('keydown', {
    key: 'Tab',
    bubbles: true,
    cancelable: true,
  });
  fireEvent(handle, navigation);
  expect(navigation.defaultPrevented).toBe(false);
});

test.each([
  'pointercancel',
  'Escape',
  'lostpointercapture',
  'blur',
  'visibilitychange',
])('%s 取消拖拽、恢复起始偏好并阻止后续指针更新', (reason) => {
  resizeEnvironment();
  const { handle, workspace, release } = resizableWorkspace();
  fireEvent.keyDown(handle, { key: 'End' });
  pointer(handle, 'pointerdown', 480);
  pointer(window, 'pointermove', 380);
  expectTreeWidth(handle, 380);
  if (reason === 'Escape') fireEvent.keyDown(handle, { key: 'Escape' });
  else if (reason === 'blur') fireEvent(window, new Event('blur'));
  else if (reason === 'visibilitychange') {
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(true);
    fireEvent(document, new Event('visibilitychange'));
  } else
    pointer(reason === 'lostpointercapture' ? handle : window, reason, 380);
  expectTreeWidth(handle, 480);
  expect(workspace.dataset.treeResizing).toBe('false');
  expect(release).toHaveBeenCalledExactlyOnceWith(1);
  pointer(window, 'pointermove', 200);
  pointer(window, 'pointerup', 200);
  expectTreeWidth(handle, 480);
});

test('容器变小约束目录并给代码留空间，放大恢复用户偏好；拖拽中也服从新上限', () => {
  const environment = resizeEnvironment();
  const { handle, workspace } = resizableWorkspace();
  fireEvent.keyDown(handle, { key: 'End' });
  environment.resize(600, 1280, true);
  expect(handle.getAttribute('aria-valuemax')).toBe('268');
  expectTreeWidth(handle, 268);
  environment.resize(1000);
  expectTreeWidth(handle, 480);
  pointer(handle, 'pointerdown', 480);
  pointer(window, 'pointermove', 380);
  environment.resize(600);
  expect(workspace.dataset.treeResizing).toBe('true');
  pointer(window, 'pointermove', 450);
  expectTreeWidth(handle, 268);
  pointer(window, 'pointercancel', 450);
  environment.resize(1000);
  expectTreeWidth(handle, 480);
});

test.each(['隐藏', '手机', '极窄容器'])(
  '%s 时取消拖拽并复用覆盖树，恢复后保留尺寸与目录节点',
  (mode) => {
    const environment = resizeEnvironment();
    const { handle, workspace } = resizableWorkspace();
    const tree = workspace.querySelector('.file-tree')!;
    fireEvent.keyDown(handle, { key: 'End' });
    pointer(handle, 'pointerdown', 480);
    pointer(window, 'pointermove', 350);
    environment.resize(
      mode === '隐藏' ? 0 : mode === '极窄容器' ? 400 : 1000,
      mode === '手机' ? 767 : 1280,
    );
    expect(workspace.dataset.treeResizing).toBe('false');
    expect(handle.getAttribute('aria-disabled')).toBe('true');
    expect(handle.tabIndex).toBe(-1);
    expect(workspace.dataset.treeOverlay).toBe(
      mode === '隐藏' ? 'false' : 'true',
    );
    pointer(window, 'pointermove', 200);
    environment.resize(1000, 1280);
    expectTreeWidth(handle, 480);
    expect(handle.tabIndex).toBe(0);
    expect(workspace.querySelector('.file-tree')).toBe(tree);
  },
);

test('卸载中释放捕获并清理观察器和所有新增监听', () => {
  const environment = resizeEnvironment();
  const added = vi.spyOn(window, 'addEventListener');
  const removed = vi.spyOn(window, 'removeEventListener');
  const documentAdded = vi.spyOn(document, 'addEventListener');
  const documentRemoved = vi.spyOn(document, 'removeEventListener');
  const { handle, view, release } = resizableWorkspace();
  pointer(handle, 'pointerdown', 260);
  pointer(window, 'pointermove', 350);
  view.unmount();
  expect(release).toHaveBeenCalledExactlyOnceWith(1);
  const observer = environment.observers.find((record) =>
    record.target?.classList.contains('source-ide'),
  )!;
  expect(observer.disconnect).toHaveBeenCalledOnce();
  for (const [name, callback] of added.mock.calls)
    if (
      [
        'resize',
        'pointermove',
        'pointerup',
        'pointercancel',
        'keydown',
        'blur',
      ].includes(name)
    )
      expect(
        removed.mock.calls.some(
          ([removedName, removedCallback]) =>
            removedName === name && removedCallback === callback,
        ),
      ).toBe(true);
  const visibilityCallback = documentAdded.mock.calls.find(
    ([name]) => name === 'visibilitychange',
  )![1];
  expect(documentRemoved).toHaveBeenCalledWith(
    'visibilitychange',
    visibilityCallback,
  );
  pointer(window, 'pointermove', 400);
  expect(handle.getAttribute('aria-valuenow')).toBe('350');
});

test('捕获失败不创建拖拽会话，键盘仍可继续调整', () => {
  resizeEnvironment();
  const { handle, capture, workspace } = resizableWorkspace();
  capture.mockImplementationOnce(() => {
    throw new DOMException('Pointer inactive');
  });
  pointer(handle, 'pointerdown', 260);
  pointer(window, 'pointermove', 400);
  expect(workspace.dataset.treeResizing).toBe('false');
  expectTreeWidth(handle, 260);
  fireEvent.keyDown(handle, { key: 'ArrowRight' });
  expectTreeWidth(handle, 270);
});

test('目录调整保留正在浏览的源码节点、滚动位置与会话宽度', async () => {
  const environment = resizeEnvironment();
  window.history.replaceState(
    null,
    '',
    `/?project=${project}&snapshot=${snapshot}&file=${encodeURIComponent(files[0]!.file_path)}&start=1&end=450`,
  );
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      const file = files.find((file) => path.includes(file.id))!;
      const params = new URL(path, 'http://local.test').searchParams;
      const start = Number(params.get('start_line')),
        end = Number(params.get('end_line'));
      return new Response(
        JSON.stringify({
          ...file,
          start_line: start,
          end_line: end,
          content:
            Array.from(
              { length: end - start + 1 },
              (_, i) => `const retainedRow = ${start + i}`,
            ).join('\n') + '\n',
        }),
      );
    }),
  );
  const view = render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <Harness />
    </QueryClientProvider>,
  );
  await screen.findByText(
    (_text, element) =>
      element?.tagName === 'PRE' &&
      element.textContent === 'const retainedRow = 1',
  );
  const handle = screen.getByRole('separator', { name: '调整项目文件树宽度' });
  const captured = new Set<number>();
  Object.assign(handle, {
    setPointerCapture: (id: number) => captured.add(id),
    hasPointerCapture: (id: number) => captured.has(id),
    releasePointerCapture: (id: number) => captured.delete(id),
  });
  const source = view.container.querySelector<HTMLElement>('.source-lines')!;
  const firstLine = source.querySelector('pre')!;
  source.scrollTop = 207;
  source.scrollLeft = 41;
  pointer(handle, 'pointerdown', 260);
  pointer(window, 'pointermove', 350);
  pointer(window, 'pointerup', 360);
  expect(view.container.querySelector('.source-lines')).toBe(source);
  expect(source.querySelector('pre')).toBe(firstLine);
  expect(source.scrollTop).toBe(207);
  expect(source.scrollLeft).toBe(41);
  environment.resize(400);
  environment.resize(1000);
  expect(view.container.querySelector('.source-lines')).toBe(source);
  expect(source.scrollTop).toBe(207);
  expect(source.scrollLeft).toBe(41);
  fireEvent.click(screen.getByRole('button', { name: 'b.tsx' }));
  await screen.findByText(
    (_text, element) =>
      element?.tagName === 'PRE' &&
      element.textContent === 'const retainedRow = 1',
  );
  expectTreeWidth(handle, 360);
});

test('快照父节点重建时目录宽度回到默认值', () => {
  resizeEnvironment();
  const props = {
    files,
    snapshotId: snapshot,
    reference: null,
    secondaryReference: null,
    onSource: vi.fn(),
    onSecondary: vi.fn(),
  };
  const view = render(<SourceWorkspace key={snapshot} {...props} />);
  fireEvent.keyDown(screen.getByRole('separator'), { key: 'End' });
  expectTreeWidth(screen.getByRole('separator'), 480);
  view.rerender(
    <SourceWorkspace
      key={project}
      {...props}
      snapshotId={project}
      files={[]}
    />,
  );
  expectTreeWidth(screen.getByRole('separator'), 260);
});
