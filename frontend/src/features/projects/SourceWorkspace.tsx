import { useEffect, useMemo, useRef, useState } from 'react';
import type { SourceFile, SourceRef } from '../../shared/api/generated/schema';
import { Icon } from '../../shared/components/Icon';
import { SourceViewer } from './SourceViewer';

type Directory = {
  path: string;
  name: string;
  directories: Map<string, Directory>;
  files: SourceFile[];
};
function fileTree(files: SourceFile[]): Directory {
  const root: Directory = {
    path: '',
    name: '',
    directories: new Map(),
    files: [],
  };
  for (const file of files) {
    const parts = file.file_path.split('/');
    let current = root;
    for (const name of parts.slice(0, -1)) {
      if (!current.directories.has(name))
        current.directories.set(name, {
          path: current.path + '/' + name,
          name,
          directories: new Map(),
          files: [],
        });
      current = current.directories.get(name)!;
    }
    current.files.push(file);
  }
  return root;
}
export function FileTree({
  files,
  search,
  selected,
  onOpen,
  onPin,
}: {
  files: SourceFile[];
  search: string;
  selected: string | undefined;
  onOpen: (ref: SourceRef) => void;
  onPin: (ref: SourceRef) => void;
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const filtered = useMemo(
    () =>
      files.filter((file) =>
        file.file_path
          .toLocaleLowerCase()
          .includes(search.trim().toLocaleLowerCase()),
      ),
    [files, search],
  );
  const root = useMemo(() => fileTree(filtered), [filtered]);
  const reference = (file: SourceFile): SourceRef => ({
    snapshot_id: file.snapshot_id,
    file_path: file.file_path,
    start_line: 1,
    end_line: file.line_count,
  });
  function branch(directory: Directory): React.ReactNode {
    return (
      <ul>
        {[...directory.directories.values()]
          .sort((a, b) => a.name.localeCompare(b.name))
          .map((child) => {
            const open = !!search.trim() || !collapsed.has(child.path);
            return (
              <li key={child.path}>
                <button
                  className="tree-folder"
                  aria-expanded={open}
                  onClick={() =>
                    setCollapsed((previous) => {
                      const next = new Set(previous);
                      if (open) next.add(child.path);
                      else next.delete(child.path);
                      return next;
                    })
                  }
                >
                  <span className="tree-chevron">{open ? '⌄' : '›'}</span>
                  <Icon name="folder" />
                  {child.name}
                </button>
                {open && branch(child)}
              </li>
            );
          })}
        {directory.files
          .sort((a, b) => a.file_path.localeCompare(b.file_path))
          .map((file) => (
            <li className="tree-file-row" key={file.id}>
              <button
                className="tree-file"
                title={file.file_path}
                aria-current={selected === file.file_path ? 'true' : undefined}
                onClick={() => onOpen(reference(file))}
              >
                <Icon name="file" />
                <span>{file.file_path.split('/').at(-1)}</span>
              </button>
              <button
                className="tree-pin icon-button"
                aria-label={`在第二窗口打开 ${file.file_path}`}
                onClick={() => onPin(reference(file))}
              >
                <Icon name="pin" />
              </button>
            </li>
          ))}
      </ul>
    );
  }
  return (
    <nav className="file-tree" aria-label="快照文件树">
      <p className="tree-scope">
        已接收源码 · {filtered.length}/{files.length}
      </p>
      {branch(root)}
      {!filtered.length && (
        <p className="panel-empty">
          {files.length ? '没有匹配的文件。' : '此快照没有可读源码。'}
        </p>
      )}
    </nav>
  );
}
export function SourceWorkspace({
  files,
  snapshotId,
  snapshotName,
  reference,
  secondaryReference,
  search,
  onSource,
  onSecondary,
}: {
  files: SourceFile[];
  snapshotId: string;
  snapshotName?: string;
  reference: SourceRef | null;
  secondaryReference: SourceRef | null;
  search: string;
  onSource: (ref: SourceRef) => void;
  onSecondary: (ref: SourceRef | null) => void;
}) {
  const [treeOpen, setTreeOpen] = useState(false),
    [activeWindow, setWindow] = useState<'primary' | 'secondary'>('primary');
  const treeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    function escape(event: KeyboardEvent) {
      if (event.key === 'Escape' && treeOpen) {
        setTreeOpen(false);
        treeButton.current?.focus();
      }
    }
    globalThis.window.addEventListener('keydown', escape);
    return () => globalThis.window.removeEventListener('keydown', escape);
  }, [treeOpen]);
  return (
    <div className="source-workspace" data-window={activeWindow}>
      <button
        ref={treeButton}
        className="file-drawer-toggle"
        aria-expanded={treeOpen}
        onClick={() => setTreeOpen(!treeOpen)}
      >
        <Icon name="folder" />
        项目结构
      </button>
      <aside className="file-tree-panel surface" data-open={treeOpen}>
        <div className="panel-title">
          <Icon name="graph" />
          <h2>项目结构</h2>
          <span className="panel-caption">文件树</span>
          <button
            className="file-drawer-toggle icon-button"
            aria-label="关闭项目结构"
            onClick={() => {
              setTreeOpen(false);
              treeButton.current?.focus();
            }}
          >
            <Icon name="close" />
          </button>
        </div>
        <FileTree
          files={files}
          search={search}
          selected={reference?.file_path}
          onOpen={(ref) => {
            onSource(ref);
            setWindow('primary');
            setTreeOpen(false);
            if (treeOpen) treeButton.current?.focus();
          }}
          onPin={(ref) => {
            onSecondary(ref);
            setWindow('secondary');
            setTreeOpen(false);
            if (treeOpen) treeButton.current?.focus();
          }}
        />
      </aside>
      <div className="code-workspace">
        <nav className="code-window-tabs" aria-label="源码窗口">
          <button
            aria-pressed={activeWindow === 'primary'}
            onClick={() => setWindow('primary')}
          >
            主源码
          </button>
          <button
            aria-pressed={activeWindow === 'secondary'}
            onClick={() => setWindow('secondary')}
          >
            固定源码{secondaryReference ? ' · 1' : ''}
          </button>
        </nav>
        <div className="code-pair">
          <div className="primary-code surface">
            <div className="code-actions">
              <span>主源码窗口</span>
              <button
                className="text-button"
                disabled={!reference}
                onClick={() => {
                  onSecondary(reference);
                  setWindow('secondary');
                }}
              >
                <Icon name="pin" />
                固定至第二窗口
              </button>
            </div>
            <SourceViewer
              files={files}
              snapshotId={snapshotId}
              snapshotName={snapshotName}
              reference={reference}
              onPosition={onSource}
            />
          </div>
          <div className="secondary-code surface">
            <div className="code-actions">
              <span>固定源码窗口</span>
              <button
                className="icon-button"
                aria-label="关闭固定源码"
                disabled={!secondaryReference}
                onClick={() => {
                  onSecondary(null);
                  setWindow('primary');
                }}
              >
                <Icon name="close" />
              </button>
            </div>
            <SourceViewer
              files={files}
              snapshotId={snapshotId}
              snapshotName={snapshotName}
              reference={secondaryReference}
              windowLabel="固定只读源码"
              onPosition={onSecondary}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
