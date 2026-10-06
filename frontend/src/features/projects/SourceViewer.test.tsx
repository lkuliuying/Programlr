import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SourceViewer } from './SourceViewer';
import { parseFile } from './api/projects-api';
import type { SourceRef } from '../../shared/api/generated/schema';

const snapshot = '00000000-0000-0000-0000-000000000001';
const file = {
  id: '00000000-0000-0000-0000-000000000002',
  snapshot_id: snapshot,
  file_path: 'entry.ts',
  sha256: 'a'.repeat(64),
  line_count: 300,
  size_bytes: 600,
  encoding: 'utf-8',
};
const reference = {
  snapshot_id: snapshot,
  file_path: 'entry.ts',
  start_line: 1,
  end_line: 300,
};
function show(ref: SourceRef, snapshotName?: string) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <SourceViewer
        files={[file]}
        snapshotId={snapshot}
        snapshotName={snapshotName}
        reference={ref}
      />
    </QueryClientProvider>,
  );
}

function sourceResponse(source: typeof file, path: string) {
  const parameters = new URL(path, 'http://local.test').searchParams;
  const start = Number(parameters.get('start_line'));
  const end = Number(parameters.get('end_line'));
  return new Response(
    JSON.stringify({
      ...source,
      start_line: start,
      end_line: end,
      content:
        Array.from(
          { length: end - start + 1 },
          (_, index) => `第 ${start + index} 行`,
        ).join('\n') + '\n',
    }),
  );
}

function minimapRect(button: HTMLElement, top = 100, height = 200) {
  return vi
    .spyOn(button, 'getBoundingClientRect')
    .mockReturnValue(new DOMRect(0, top, 80, height));
}

const originalViewportDescriptors = [
  'clientHeight',
  'scrollHeight',
  'scrollTop',
].map(
  (key) =>
    [key, Object.getOwnPropertyDescriptor(HTMLElement.prototype, key)] as const,
);

function clampedSourceViewport(lineCount: number, initialHeight: number) {
  let height = initialHeight;
  const positions = new WeakMap<HTMLElement, number>();
  const observers: {
    callback: ResizeObserverCallback;
    target: Element | null;
  }[] = [];
  class TestResizeObserver {
    record;
    constructor(callback: ResizeObserverCallback) {
      this.record = { callback, target: null as Element | null };
      observers.push(this.record);
    }
    observe(target: Element) {
      this.record.target = target;
    }
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal('ResizeObserver', TestResizeObserver);
  vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockImplementation(
    function (this: HTMLElement) {
      return this.classList.contains('source-lines') ? height : 0;
    },
  );
  vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(
    function (this: HTMLElement) {
      return this.classList.contains('source-lines') ? lineCount * 23 : 0;
    },
  );
  vi.spyOn(HTMLElement.prototype, 'scrollTop', 'get').mockImplementation(
    function (this: HTMLElement) {
      return positions.get(this) ?? 0;
    },
  );
  // 只模拟源码容器的浏览器滚动边界，不将这些数值当作CSS显隐验证。
  vi.spyOn(HTMLElement.prototype, 'scrollTop', 'set').mockImplementation(
    function (this: HTMLElement, value: number) {
      positions.set(
        this,
        this.classList.contains('source-lines')
          ? Math.max(0, Math.min(value, this.scrollHeight - this.clientHeight))
          : value,
      );
    },
  );
  return {
    resize(nextHeight: number) {
      act(() => {
        height = nextHeight;
        for (const observer of observers)
          if (observer.target?.classList.contains('source-lines'))
            observer.callback([], {} as ResizeObserver);
      });
    },
  };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  // 同一继承属性分别监视读写时，按原描述符清除可能残留的原型覆盖。
  for (const [key, descriptor] of originalViewportDescriptors)
    if (descriptor)
      Object.defineProperty(HTMLElement.prototype, key, descriptor);
    else Reflect.deleteProperty(HTMLElement.prototype, key);
  vi.unstubAllGlobals();
});
test('越界、缺失文件和跨快照来源不读取任何源码', () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  for (const bad of [
    { ...reference, end_line: 301 },
    { ...reference, file_path: 'missing.ts' },
    { ...reference, snapshot_id: file.id },
  ]) {
    const view = show(bad, '相同显示名称不能替代 UUID 归属');
    expect(screen.getByRole('alert').textContent).toContain('引用失效');
    view.unmount();
  }
  expect(fetcher).not.toHaveBeenCalled();
  expect(() =>
    parseFile({ ...file, snapshot_id: file.id }, snapshot),
  ).toThrow();
});
test('源码按 200 行连续读取，滚动不重复请求已加载块且缩略图注明范围', async () => {
  const paths: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      paths.push(path);
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
              (_, index) => `第 ${start + index} 行`,
            ).join('\n') + '\n',
        }),
      );
    }),
  );
  show(reference);
  await screen.findByText('第 1 行');
  fireEvent.scroll(screen.getByLabelText('entry.ts 源码行'), {
    target: { scrollTop: 200 * 23 },
  });
  await screen.findByText('第 201 行');
  expect(screen.getByText('第 1 行')).toBeTruthy();
  expect(screen.getByLabelText('源码缩略图，仅已加载行 1–300')).toBeTruthy();
  expect(screen.queryByRole('button', { name: '下一段' })).toBeNull();
  expect(paths.map((path) => path.split('?')[1])).toEqual([
    'start_line=1&end_line=200',
    'start_line=201&end_line=300',
  ]);
});
test('缩略图按顶部、中间、底部坐标定位，越界和零高度都限制在已加载范围', async () => {
  const fetcher = vi.fn(async (path: string) => sourceResponse(file, path));
  const onVisibleLine = vi.fn();
  const onPosition = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  render(
    <SourceViewer
      files={[file]}
      snapshotId={snapshot}
      reference={reference}
      onVisibleLine={onVisibleLine}
      onPosition={onPosition}
    />,
  );
  await screen.findByLabelText('源码缩略图，仅已加载行 1–300');
  const area = screen.getByLabelText('entry.ts 源码行');
  const button = screen.getByRole('button', { name: '定位已加载源码' });
  const rectangle = minimapRect(button);
  expect(fetcher).toHaveBeenCalledTimes(2);
  for (const { clientY, height, line } of [
    { clientY: 100, height: 200, line: 1 },
    { clientY: 200, height: 200, line: 150 },
    { clientY: 300, height: 200, line: 300 },
    { clientY: 50, height: 200, line: 1 },
    { clientY: 400, height: 200, line: 300 },
    { clientY: 999, height: 0, line: 1 },
  ]) {
    rectangle.mockReturnValue(new DOMRect(0, 100, 80, height));
    await act(async () => {
      fireEvent.click(button, { clientY });
    });
    expect(area.scrollTop).toBe((line - 1) * 23);
    expect(onVisibleLine).toHaveBeenLastCalledWith(line);
    expect(fetcher).toHaveBeenCalledTimes(2);
  }
  expect(onPosition).not.toHaveBeenCalled();
});

test('缩略图点击已加载块之间的空隙只定位现有块，不请求空隙或远处源码', async () => {
  const large = { ...file, line_count: 1000 };
  const fetcher = vi.fn(async (path: string) => {
    const start = Number(
      new URL(path, 'http://local.test').searchParams.get('start_line'),
    );
    return start === 201
      ? new Response('{}', { status: 503 })
      : sourceResponse(large, path);
  });
  const onVisibleLine = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  render(
    <SourceViewer
      files={[large]}
      snapshotId={snapshot}
      reference={{ ...reference, end_line: 3 }}
      onVisibleLine={onVisibleLine}
    />,
  );
  await screen.findByText('第 1 行');
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  const area = screen.getByLabelText('entry.ts 源码行');
  fireEvent.scroll(area, { target: { scrollTop: 400 * 23 } });
  await screen.findByLabelText('源码缩略图，仅已加载行 1–800');
  const requestedStarts = () =>
    fetcher.mock.calls.map(([path]) =>
      Number(new URL(path, 'http://local.test').searchParams.get('start_line')),
    );
  expect(requestedStarts()).toEqual([1, 201, 401, 601]);
  expect(screen.queryByText('第 300 行')).toBeNull();
  expect(screen.getByText('第 401 行')).toBeTruthy();
  const button = screen.getByRole('button', { name: '定位已加载源码' });
  minimapRect(button);
  onVisibleLine.mockClear();
  await act(async () => {
    fireEvent.click(button, { clientY: 175 });
  });
  expect(area.scrollTop).toBe(400 * 23);
  expect(onVisibleLine).toHaveBeenLastCalledWith(401);
  expect(requestedStarts()).toEqual([1, 201, 401, 601]);
});

test('主副源码缩略图使用各自点击坐标、滚动容器与回调', async () => {
  const secondaryFile = {
    ...file,
    id: '00000000-0000-0000-0000-000000000003',
    file_path: 'secondary.ts',
  };
  const fetcher = vi.fn(async (path: string) =>
    sourceResponse(
      path.includes(secondaryFile.id) ? secondaryFile : file,
      path,
    ),
  );
  const onPrimaryLine = vi.fn();
  const onSecondaryLine = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  render(
    <>
      <SourceViewer
        files={[file]}
        snapshotId={snapshot}
        reference={reference}
        windowLabel="主源码"
        onVisibleLine={onPrimaryLine}
      />
      <SourceViewer
        files={[secondaryFile]}
        snapshotId={snapshot}
        reference={{ ...reference, file_path: secondaryFile.file_path }}
        windowLabel="副源码"
        onVisibleLine={onSecondaryLine}
      />
    </>,
  );
  const primary = within(screen.getByRole('region', { name: '主源码' }));
  const secondary = within(screen.getByRole('region', { name: '副源码' }));
  await primary.findByLabelText('源码缩略图，仅已加载行 1–300');
  await secondary.findByLabelText('源码缩略图，仅已加载行 1–300');
  const primaryArea = primary.getByLabelText('entry.ts 源码行');
  const secondaryArea = secondary.getByLabelText('secondary.ts 源码行');
  const primaryButton = primary.getByRole('button', { name: '定位已加载源码' });
  const secondaryButton = secondary.getByRole('button', {
    name: '定位已加载源码',
  });
  minimapRect(primaryButton, 50, 100);
  minimapRect(secondaryButton, 450, 200);
  expect(fetcher).toHaveBeenCalledTimes(4);
  await act(async () => {
    fireEvent.click(primaryButton, { clientY: 125 });
  });
  expect(primaryArea.scrollTop).toBe(224 * 23);
  expect(secondaryArea.scrollTop).toBe(0);
  expect(onPrimaryLine).toHaveBeenLastCalledWith(225);
  expect(onSecondaryLine).not.toHaveBeenCalled();
  await act(async () => {
    fireEvent.click(secondaryButton, { clientY: 500 });
  });
  expect(secondaryArea.scrollTop).toBe(74 * 23);
  expect(primaryArea.scrollTop).toBe(224 * 23);
  expect(onSecondaryLine).toHaveBeenLastCalledWith(75);
  expect(onPrimaryLine).toHaveBeenCalledTimes(1);
  expect(fetcher).toHaveBeenCalledTimes(4);
});

test('短文件初始化和缩略图点击按实际滚动上限反馈完整可见行', async () => {
  const shortFile = { ...file, line_count: 14 };
  clampedSourceViewport(14, 20 * 23);
  const fetcher = vi.fn(async (path: string) =>
    sourceResponse(shortFile, path),
  );
  const onVisibleLine = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  render(
    <SourceViewer
      files={[shortFile]}
      snapshotId={snapshot}
      reference={{ ...reference, start_line: 7, end_line: 14 }}
      onVisibleLine={onVisibleLine}
    />,
  );
  await screen.findByLabelText('源码缩略图，仅已加载行 1–14');
  const area = screen.getByLabelText('entry.ts 源码行');
  expect(area.scrollTop).toBe(0);
  expect(screen.getByText('第 1–14 行 / 共 14 行')).toBeTruthy();
  const button = screen.getByRole('button', { name: '定位已加载源码' });
  minimapRect(button);
  for (const clientY of [200, 300]) {
    await act(async () => {
      fireEvent.click(button, { clientY });
    });
    expect(area.scrollTop).toBe(0);
    expect(onVisibleLine).toHaveBeenLastCalledWith(1);
    expect(screen.getByText('第 1–14 行 / 共 14 行')).toBeTruthy();
  }
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test('长文件末尾点击反馈实际首行，显式跳行仍传递原请求引用', async () => {
  clampedSourceViewport(300, 10 * 23);
  const fetcher = vi.fn(async (path: string) => sourceResponse(file, path));
  const onVisibleLine = vi.fn();
  const onPosition = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  render(
    <SourceViewer
      files={[file]}
      snapshotId={snapshot}
      reference={reference}
      onVisibleLine={onVisibleLine}
      onPosition={onPosition}
    />,
  );
  await screen.findByLabelText('源码缩略图，仅已加载行 1–300');
  const area = screen.getByLabelText('entry.ts 源码行');
  const button = screen.getByRole('button', { name: '定位已加载源码' });
  minimapRect(button);
  await act(async () => {
    fireEvent.click(button, { clientY: 300 });
  });
  expect(area.scrollTop).toBe((300 - 10) * 23);
  expect(onVisibleLine).toHaveBeenLastCalledWith(291);
  expect(screen.getByText('第 291–300 行 / 共 300 行')).toBeTruthy();
  expect(onPosition).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole('spinbutton'), {
    target: { value: '300' },
  });
  fireEvent.click(screen.getByRole('button', { name: '跳转' }));
  expect(area.scrollTop).toBe((300 - 10) * 23);
  expect(onPosition).toHaveBeenCalledExactlyOnceWith({
    ...reference,
    start_line: 300,
    end_line: 300,
  });
  expect(onVisibleLine).toHaveBeenLastCalledWith(291);
  expect(fetcher).toHaveBeenCalledTimes(2);
});

test('初始隐藏的源码首次显示恢复目标，后续尺寸变化保持当前滚动', async () => {
  const viewport = clampedSourceViewport(300, 0);
  const fetcher = vi.fn(async (path: string) => sourceResponse(file, path));
  vi.stubGlobal('fetch', fetcher);
  render(
    <SourceViewer
      files={[file]}
      snapshotId={snapshot}
      reference={{ ...reference, start_line: 201, end_line: 205 }}
    />,
  );
  await screen.findByText('第 201 行');
  const area = screen.getByLabelText('entry.ts 源码行');
  expect(area.scrollTop).toBe(0);
  viewport.resize(10 * 23);
  expect(area.scrollTop).toBe(200 * 23);
  expect(screen.getByText('第 201–210 行 / 共 300 行')).toBeTruthy();
  fireEvent.scroll(area, { target: { scrollTop: 220 * 23 } });
  viewport.resize(12 * 23);
  expect(area.scrollTop).toBe(220 * 23);
  expect(screen.getByText('第 221–232 行 / 共 300 行')).toBeTruthy();
  expect(
    fetcher.mock.calls.map(([path]) =>
      new URL(path, 'http://local.test').searchParams.get('start_line'),
    ),
  ).toEqual(['201']);
});

test('源码响应摘要或文件身份不符时明确失败', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            ...file,
            sha256: 'b'.repeat(64),
            start_line: 1,
            end_line: 1,
            content: '错误内容\n',
          }),
        ),
    ),
  );
  show({ ...reference, end_line: 1 }, '名称正确但摘要错误');
  expect((await screen.findByRole('alert')).textContent).toContain(
    '资源归属无效',
  );
  expect(screen.queryByText('错误内容')).toBeNull();
});

test('源码元数据完整显示长名称作为文本，省略或空名兼容未命名状态且不展示短编号', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      const parameters = new URL(path, 'http://local.test').searchParams;
      const start = Number(parameters.get('start_line')),
        end = Number(parameters.get('end_line'));
      return new Response(
        JSON.stringify({
          ...file,
          start_line: start,
          end_line: end,
          content:
            Array.from({ length: end - start + 1 }, (_, index) =>
              index === 0 && start === 1 ? 'const task = 1;' : '',
            ).join('\n') + '\n',
        }),
      );
    }),
  );
  const longName =
    '创建任务请求校验基线'.repeat(14) + '<img src=x onerror=alert(1)>';
  for (const name of [undefined, '', longName]) {
    const view = show({ ...reference, end_line: 1 }, name);
    await screen.findByText('task', { exact: false });
    expect(screen.getByLabelText('entry.ts 源码行').textContent).toContain(
      'const task = 1;',
    );
    const metadata = view.container.querySelector('.source-meta small');
    expect(metadata?.textContent).toBe(`快照 ${name || '未命名快照'} · 只读`);
    expect(metadata?.getAttribute('title')).toBe(name || '未命名快照');
    expect(metadata?.textContent).not.toContain(snapshot.slice(0, 8));
    expect(view.container.querySelector('img')).toBeNull();
    view.unmount();
  }
});

test('远处引用直接读取目标块，连续双向滚动最多保留千行且缩略图不预扫文件', async () => {
  const large = { ...file, line_count: 5000 };
  const starts: number[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      const query = new URL(path, 'http://local.test').searchParams;
      const start = Number(query.get('start_line')),
        end = Number(query.get('end_line'));
      starts.push(start);
      expect(end - start + 1).toBeLessThanOrEqual(200);
      return new Response(
        JSON.stringify({
          ...large,
          start_line: start,
          end_line: end,
          content:
            Array.from(
              { length: end - start + 1 },
              (_, index) => `source ${start + index}`,
            ).join('\n') + '\n',
        }),
      );
    }),
  );
  const result = render(
    <SourceViewer
      files={[large]}
      snapshotId={snapshot}
      reference={{ ...reference, start_line: 2001, end_line: 2005 }}
    />,
  );
  await screen.findByText('source 2001');
  expect(starts[0]).toBe(2001);
  expect(starts).not.toContain(1);
  const area = screen.getByLabelText('entry.ts 源码行');
  for (const line of [2201, 2401, 2601, 2801, 3001, 2201]) {
    fireEvent.scroll(area, { target: { scrollTop: (line - 1) * 23 } });
    await screen.findByText(`source ${line}`);
    expect(
      result.container.querySelectorAll('[data-line]').length,
    ).toBeLessThanOrEqual(1000);
  }
  await waitFor(() => expect(starts).toContain(2001));
  expect(starts.every((line) => line >= 2001)).toBe(true);
  expect(result.container.querySelector('[data-line="1"]')).toBeNull();
});

test('源码请求失败可原位重试，卸载中止尚未完成的请求', async () => {
  const fetcher = vi.fn(async (path: string) => {
    if (fetcher.mock.calls.length === 1)
      return new Response('{}', { status: 503 });
    const parameters = new URL(path, 'http://local.test').searchParams;
    const start = Number(parameters.get('start_line')),
      end = Number(parameters.get('end_line'));
    return new Response(
      JSON.stringify({
        ...file,
        start_line: start,
        end_line: end,
        content:
          Array.from(
            { length: end - start + 1 },
            (_, index) => `recovered ${start + index}`,
          ).join('\n') + '\n',
      }),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  const result = show(reference);
  await screen.findByRole('alert');
  fireEvent.click(screen.getByRole('button', { name: /重新|重试/ }));
  await screen.findByText('recovered 1');
  result.unmount();
  let signal: AbortSignal | undefined;
  vi.stubGlobal(
    'fetch',
    vi.fn(
      (_path: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          signal = init.signal ?? undefined;
          signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError')),
          );
        }),
    ),
  );
  const pending = show(reference);
  await waitFor(() => expect(signal).toBeDefined());
  pending.unmount();
  expect(signal!.aborted).toBe(true);
});

test('切换快照后忽略中止信号的旧请求返回也不能覆盖新源码', async () => {
  const nextFile = {
    ...file,
    id: '00000000-0000-0000-0000-000000000003',
    snapshot_id: '00000000-0000-0000-0000-000000000004',
  };
  let finishOld: (response: Response) => void = () => {
    throw new Error('旧请求尚未发起');
  };
  let oldSignal: AbortSignal | null = null;
  const response = (source: typeof file, path: string, prefix: string) => {
    const query = new URL(path, 'http://local.test').searchParams;
    const start = Number(query.get('start_line'));
    const end = Number(query.get('end_line'));
    return new Response(
      JSON.stringify({
        ...source,
        start_line: start,
        end_line: end,
        content:
          Array.from(
            { length: end - start + 1 },
            (_, index) => `${prefix} ${start + index}`,
          ).join('\n') + '\n',
      }),
    );
  };
  let oldPath = '';
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string, init: RequestInit) => {
      if (path.includes(file.id)) {
        oldPath = path;
        oldSignal = init.signal ?? null;
        return new Promise<Response>((resolve) => {
          finishOld = resolve;
        });
      }
      return Promise.resolve(response(nextFile, path, '当前快照'));
    }),
  );
  const view = render(
    <SourceViewer files={[file]} snapshotId={snapshot} reference={reference} />,
  );
  await waitFor(() => expect(oldSignal).not.toBeNull());
  view.rerender(
    <SourceViewer
      files={[nextFile]}
      snapshotId={nextFile.snapshot_id}
      reference={{ ...reference, snapshot_id: nextFile.snapshot_id }}
    />,
  );
  await screen.findByText('当前快照 1');
  expect(oldSignal!.aborted).toBe(true);
  await act(async () => finishOld(response(file, oldPath, '过期快照')));
  expect(screen.queryByText('过期快照 1')).toBeNull();
  expect(screen.getByText('当前快照 1')).toBeTruthy();
});
