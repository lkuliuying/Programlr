import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { SourceFile, SourceRef } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { getSource } from './api/projects-api';
import { highlightSource } from './source-highlight';

const blockSize = 200;
const lineHeight = 23;
const blockAt = (line: number) => Math.floor((line - 1) / blockSize);

export function SourceViewer({
  files,
  snapshotId,
  snapshotName,
  reference,
  windowLabel = '只读源码',
  initialLine,
  onVisibleLine,
  onPosition,
}: {
  files: SourceFile[];
  snapshotId: string;
  snapshotName?: string;
  reference: SourceRef | null;
  windowLabel?: string;
  initialLine?: number;
  onVisibleLine?: (line: number) => void;
  onPosition?: (ref: SourceRef) => void;
}) {
  if (!reference)
    return (
      <section className="workspace-source source-empty">
        <h2>{windowLabel}</h2>
        <p>从左侧文件树打开源码，或选择接口、关系、知识中的源码依据。</p>
      </section>
    );
  const matches = files.filter(
    (file) => file.file_path === reference.file_path,
  );
  const file = matches[0];
  if (
    reference.snapshot_id !== snapshotId ||
    matches.length !== 1 ||
    !file ||
    file.snapshot_id !== snapshotId ||
    !Number.isSafeInteger(reference.start_line) ||
    !Number.isSafeInteger(reference.end_line) ||
    reference.start_line < 1 ||
    reference.end_line < reference.start_line ||
    reference.end_line > file.line_count
  )
    return (
      <section className="workspace-source" role="alert">
        源码引用失效或不属于当前快照，无法定位。
      </section>
    );
  return (
    <SourceDocument
      key={`${file.id}:${reference.start_line}:${reference.end_line}`}
      file={file}
      reference={reference}
      snapshotName={snapshotName?.trim() || '未命名快照'}
      windowLabel={windowLabel}
      initialLine={initialLine}
      onVisibleLine={onVisibleLine}
      onPosition={onPosition}
    />
  );
}

function SourceDocument({
  file,
  reference,
  snapshotName,
  windowLabel,
  initialLine,
  onVisibleLine,
  onPosition,
}: {
  file: SourceFile;
  reference: SourceRef;
  snapshotName: string;
  windowLabel: string;
  initialLine?: number;
  onVisibleLine?: (line: number) => void;
  onPosition?: (ref: SourceRef) => void;
}) {
  const [firstLine] = useState(() =>
    Math.max(1, Math.min(file.line_count, initialLine ?? reference.start_line)),
  );
  const [viewport, setViewport] = useState({
    line: firstLine,
    rows: 24,
    direction: 1,
  });
  const [jump, setJump] = useState(String(firstLine));
  const [chunks, setChunks] = useState(new Map<number, string[]>());
  const [errors, setErrors] = useState(new Map<number, Error>());
  const frame = useRef<HTMLDivElement>(null);
  const lastBlock = blockAt(file.line_count);
  const currentBlock = blockAt(viewport.line);
  const visibleEnd = Math.min(
    file.line_count,
    viewport.line + viewport.rows - 1,
  );
  const finalVisibleBlock = blockAt(visibleEnd);
  const adjacent =
    viewport.direction > 0 ? finalVisibleBlock + 1 : currentBlock - 1;
  // 每个窗口顺序读取可见块及一个相邻预取，远处跳转不会扫描前文。
  const needed = [currentBlock, finalVisibleBlock, adjacent].find(
    (block) =>
      block >= 0 &&
      block <= lastBlock &&
      !chunks.has(block) &&
      !errors.has(block),
  );
  useEffect(() => {
    if (needed === undefined) return;
    const controller = new AbortController();
    const start = needed * blockSize + 1;
    void getSource(
      file,
      start,
      Math.min(file.line_count, start + blockSize - 1),
      controller.signal,
    ).then(
      (data) => {
        if (controller.signal.aborted) return;
        setChunks((previous) => {
          const next = new Map(
            [...previous].filter(
              ([block]) => Math.abs(block - currentBlock) <= 2,
            ),
          );
          next.set(needed, data.content.replace(/\n$/, '').split('\n'));
          return next;
        });
      },
      (error: unknown) => {
        if (!controller.signal.aborted)
          setErrors((previous) =>
            new Map(
              [...previous].filter(
                ([block]) => Math.abs(block - currentBlock) <= 2,
              ),
            ).set(
              needed,
              error instanceof Error
                ? error
                : new Error('源码读取失败，请重试。'),
            ),
          );
      },
    );
    return () => controller.abort();
  }, [file, needed, currentBlock]);
  useLayoutEffect(() => {
    const element = frame.current;
    if (!element) return;
    let positioned = false;
    const measure = () => {
      // 隐藏窗口没有可测高度，首次实际显示后才恢复引用位置。
      if (element.clientHeight <= 0 || element.scrollHeight <= 0) return;
      if (!positioned) {
        element.scrollTop = (firstLine - 1) * lineHeight;
        positioned = true;
      }
      const rows = Math.max(1, Math.ceil(element.clientHeight / lineHeight));
      const line = Math.max(
        1,
        Math.min(
          file.line_count,
          Math.floor(element.scrollTop / lineHeight) + 1,
        ),
      );
      setViewport((previous) => ({
        ...previous,
        line,
        rows: Math.min(rows, blockSize),
      }));
    };
    const observer =
      typeof ResizeObserver === 'undefined'
        ? null
        : new ResizeObserver(measure);
    observer?.observe(element);
    measure();
    return () => observer?.disconnect();
  }, [firstLine, file.line_count]);
  const visibleChunks = [...chunks]
    .filter(([block]) => Math.abs(block - currentBlock) <= 2)
    .sort(([a], [b]) => a - b);
  const loadedStart = visibleChunks.length
    ? visibleChunks[0]![0] * blockSize + 1
    : 0;
  const loadedEnd = visibleChunks.length
    ? Math.min(file.line_count, (visibleChunks.at(-1)![0] + 1) * blockSize)
    : 0;
  function scrollToLine(line: number) {
    const requested = Math.max(1, Math.min(file.line_count, line));
    const element = frame.current;
    if (element) element.scrollTop = (requested - 1) * lineHeight;
    // 短文件及末尾由浏览器限制滚动位置，视口反馈必须使用实际首行。
    const value = element
      ? Math.max(
          1,
          Math.min(
            file.line_count,
            Math.floor(element.scrollTop / lineHeight) + 1,
          ),
        )
      : requested;
    setViewport((previous) => ({
      ...previous,
      line: value,
      direction: value >= previous.line ? 1 : -1,
    }));
    onVisibleLine?.(value);
  }
  function explicitJump() {
    const line = Number(jump);
    if (!Number.isSafeInteger(line) || line < 1 || line > file.line_count)
      return;
    scrollToLine(line);
    onPosition?.({ ...reference, start_line: line, end_line: line });
  }
  const language = /\.py$/i.test(file.file_path)
    ? 'Python'
    : /\.tsx?$/i.test(file.file_path)
      ? 'TypeScript'
      : /\.jsx?$/i.test(file.file_path)
        ? 'JavaScript'
        : 'Text';
  return (
    <section
      className="workspace-source source-document"
      aria-label={windowLabel}
    >
      <p className="source-meta">
        <strong title={file.file_path}>{file.file_path}</strong>
        <small title={snapshotName}>快照 {snapshotName} · 只读</small>
      </p>
      <div className="source-reading-area">
        <div
          ref={frame}
          className="source-lines"
          tabIndex={0}
          aria-label={`${file.file_path} 源码行`}
          onScroll={(event) => {
            const line = Math.min(
              file.line_count,
              Math.floor(event.currentTarget.scrollTop / lineHeight) + 1,
            );
            setViewport((previous) => ({
              ...previous,
              line,
              direction: line >= previous.line ? 1 : -1,
            }));
            onVisibleLine?.(line);
          }}
        >
          <div
            className="source-virtual-space"
            style={{ height: file.line_count * lineHeight }}
          >
            {visibleChunks.map(([block, lines]) => (
              <ol
                key={block}
                start={block * blockSize + 1}
                style={{ top: block * blockSize * lineHeight }}
              >
                {lines.map((line, index) => {
                  const number = block * blockSize + index + 1;
                  return (
                    <li
                      key={number}
                      data-line={number}
                      data-highlight={
                        (reference.end_line - reference.start_line <
                          blockSize &&
                          number >= reference.start_line &&
                          number <= reference.end_line) ||
                        undefined
                      }
                    >
                      <pre>{highlightSource(line, file.file_path)}</pre>
                    </li>
                  );
                })}
              </ol>
            ))}
            {[...new Set([currentBlock, finalVisibleBlock])]
              .filter((block) => !chunks.has(block))
              .map((block) => (
                <div
                  className="source-block-feedback"
                  key={block}
                  style={{ top: block * blockSize * lineHeight }}
                >
                  {errors.has(block) ? (
                    <Feedback
                      error={errors.get(block) ?? null}
                      retry={() =>
                        setErrors((previous) => {
                          const next = new Map(previous);
                          next.delete(block);
                          return next;
                        })
                      }
                    />
                  ) : (
                    <p role="status">
                      正在读取第 {block * blockSize + 1} 行起的源码…
                    </p>
                  )}
                </div>
              ))}
          </div>
        </div>
        {loadedStart > 0 && (
          <aside
            className="source-minimap"
            aria-label={`源码缩略图，仅已加载行 ${loadedStart}–${loadedEnd}`}
          >
            <span>
              已加载
              <br />
              {loadedStart}–{loadedEnd}
            </span>
            <button
              type="button"
              title="点击缩略图定位已加载源码"
              aria-label="定位已加载源码"
              onClick={(event) => {
                const rect = event.currentTarget.getBoundingClientRect();
                const ratio = rect.height
                  ? Math.max(
                      0,
                      Math.min(1, (event.clientY - rect.top) / rect.height),
                    )
                  : 0;
                const candidate =
                  loadedStart + Math.floor(ratio * (loadedEnd - loadedStart));
                const containing = visibleChunks.find(
                  ([block]) => block === blockAt(candidate),
                );
                // 缩略图只定位实际加载的块，跳过尚未读取的空隙。
                const nearest = visibleChunks.reduce(
                  (best, chunk) =>
                    Math.abs(chunk[0] * blockSize + 1 - candidate) <
                    Math.abs(best[0] * blockSize + 1 - candidate)
                      ? chunk
                      : best,
                  visibleChunks[0]!,
                );
                scrollToLine(
                  containing ? candidate : nearest[0] * blockSize + 1,
                );
              }}
            >
              <svg
                viewBox={`0 0 80 ${loadedEnd - loadedStart + 1}`}
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                {visibleChunks.flatMap(([block, lines]) =>
                  lines.map((line, index) => (
                    <path
                      key={block * blockSize + index}
                      d={`M ${Math.min(24, (line.length - line.trimStart().length) * 2)} ${block * blockSize + index + 1 - loadedStart} h ${Math.min(70, line.trim().length * 1.5)}`}
                    />
                  )),
                )}
                <rect
                  x="0"
                  y={Math.max(0, viewport.line - loadedStart)}
                  width="80"
                  height={Math.max(
                    3,
                    Math.min(viewport.rows, loadedEnd - viewport.line + 1),
                  )}
                />
              </svg>
            </button>
          </aside>
        )}
      </div>
      <footer className="source-status-bar">
        <span>
          第 {viewport.line}–{visibleEnd} 行 / 共 {file.line_count} 行
        </span>
        <span>
          {language} · {file.encoding.toUpperCase()} · 只读
        </span>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            explicitJump();
          }}
        >
          <label>
            跳转到行
            <input
              aria-label={`${windowLabel}跳转到行`}
              type="number"
              min="1"
              max={file.line_count}
              value={jump}
              onChange={(event) => setJump(event.target.value)}
            />
          </label>
          <button type="submit">跳转</button>
        </form>
      </footer>
    </section>
  );
}
