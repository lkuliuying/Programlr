import { useQuery } from '@tanstack/react-query';
import { Button } from 'antd';
import { useEffect, useRef, useState } from 'react';
import type { SourceFile, SourceRef } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { getSource } from './api/projects-api';
import { highlightSource } from './source-highlight';
import { Icon } from '../../shared/components/Icon';

export function SourceViewer({
  files,
  snapshotId,
  snapshotName,
  reference,
  windowLabel = '只读源码',
  onPosition,
}: {
  files: SourceFile[];
  snapshotId: string;
  snapshotName?: string;
  reference: SourceRef | null;
  windowLabel?: string;
  onPosition?: (ref: SourceRef) => void;
}) {
  if (!reference)
    return (
      <section className="workspace-source">
        <h2>{windowLabel}</h2>
        <p>选择节点或证据中的文件位置，查看当前快照的原始内容。</p>
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
    <SourceChunk
      key={`${file.id}:${reference.start_line}:${reference.end_line}`}
      file={file}
      snapshotName={snapshotName?.trim() || '未命名快照'}
      reference={reference}
      windowLabel={windowLabel}
      onPosition={onPosition}
    />
  );
}
function SourceChunk({
  file,
  snapshotName,
  reference,
  windowLabel,
  onPosition,
}: {
  file: SourceFile;
  snapshotName: string;
  reference: SourceRef;
  windowLabel: string;
  onPosition?: (ref: SourceRef) => void;
}) {
  const [start, setStart] = useState(reference.start_line);
  const sourcePanel = useRef<HTMLElement>(null);
  const end = Math.min(reference.end_line, start + 199);
  function move(next: number) {
    if (onPosition) {
      onPosition({
        ...reference,
        start_line: next,
        end_line: Math.min(file.line_count, next + 199),
      });
    } else setStart(next);
  }
  const query = useQuery({
    queryKey: ['projects', 'source', file.snapshot_id, file.id, start, end],
    queryFn: ({ signal }) => getSource(file, start, end, signal),
  });
  useEffect(() => {
    if (query.data && !onPosition)
      sourcePanel.current?.scrollIntoView?.({ block: 'nearest' });
  }, [query.data, onPosition]);
  return (
    <section
      className="workspace-source"
      aria-label={windowLabel}
      ref={sourcePanel}
    >
      <header className="source-tab">
        <Icon name="source" />
        <strong title={file.file_path}>
          {file.file_path.split('/').at(-1)}
        </strong>
        <span>
          {file.file_path.endsWith('.py')
            ? 'Python'
            : /\.tsx?$/.test(file.file_path)
              ? 'TypeScript'
              : 'Text'}
        </span>
      </header>
      <h2 className="sr-only">{windowLabel}</h2>
      <p className="source-meta">
        <strong>{file.file_path}</strong> · 第 {start}–{end} 行
        <small title={snapshotName}>快照 {snapshotName} · 只读</small>
      </p>
      <Feedback
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
      {query.isPending && <p role="status">正在读取源码…</p>}
      {query.data && (
        <div
          className="source-lines"
          tabIndex={0}
          aria-label={`${file.file_path} 源码行`}
        >
          <ol start={start}>
            {query.data.content
              .replace(/\n$/, '')
              .split('\n')
              .map((line, index) => (
                <li key={start + index} data-line={start + index}>
                  <pre>{highlightSource(line, file.file_path)}</pre>
                </li>
              ))}
          </ol>
        </div>
      )}
      {(onPosition
        ? file.line_count > 200
        : reference.end_line - reference.start_line >= 200) && (
        <nav className="workspace-pagination" aria-label="源码分段">
          <Button
            disabled={start === (onPosition ? 1 : reference.start_line)}
            onClick={() =>
              move(Math.max(onPosition ? 1 : reference.start_line, start - 200))
            }
          >
            上一段
          </Button>
          <Button
            disabled={
              end === (onPosition ? file.line_count : reference.end_line)
            }
            onClick={() => move(end + 1)}
          >
            下一段
          </Button>
        </nav>
      )}
    </section>
  );
}
