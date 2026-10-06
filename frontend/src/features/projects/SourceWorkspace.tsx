import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import { Tooltip } from 'antd';
import type { SourceFile, SourceRef } from '../../shared/api/generated/schema';
import { Icon } from '../../shared/components/Icon';
import { SourceViewer } from './SourceViewer';
import { SourceEvidence } from './SourceEvidence';
import { useSourceTreeResize } from './useSourceTreeResize';
import './SourceWorkspace.css';

function SourceHint({
  title,
  children,
}: {
  title: string;
  children: React.ReactElement;
}) {
  return (
    <Tooltip
      title={title}
      placement="bottom"
      trigger={['hover', 'focus']}
      mouseEnterDelay={0.2}
      destroyOnHidden
      classNames={{ root: 'source-ide-tooltip' }}
      motion={{ motionName: 'source-hint' }}
    >
      {children}
    </Tooltip>
  );
}

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
  revealPath,
  collapseVersion = 0,
  onManualToggle,
}: {
  files: SourceFile[];
  search: string;
  selected: string | undefined;
  onOpen: (ref: SourceRef) => void;
  onPin: (ref: SourceRef) => void;
  revealPath?: string;
  collapseVersion?: number;
  onManualToggle?: () => void;
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [treeVersion, setTreeVersion] = useState(collapseVersion);
  if (treeVersion !== collapseVersion) {
    setTreeVersion(collapseVersion);
    setCollapsed(
      new Set(
        files.flatMap((file) =>
          file.file_path
            .split('/')
            .slice(0, -1)
            .map(
              (_, index, parts) => '/' + parts.slice(0, index + 1).join('/'),
            ),
        ),
      ),
    );
  }
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
            const open =
              !!search.trim() ||
              (!!revealPath &&
                ('/' + revealPath).startsWith(child.path + '/')) ||
              !collapsed.has(child.path);
            return (
              <li key={child.path}>
                <button
                  className="tree-folder"
                  aria-expanded={open}
                  onClick={() => {
                    onManualToggle?.();
                    setCollapsed((previous) => {
                      const next = new Set(previous);
                      if (open) next.add(child.path);
                      else next.delete(child.path);
                      return next;
                    });
                  }}
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
              <SourceHint title={file.file_path}>
                <button
                  className="tree-file"
                  aria-description={file.file_path}
                  aria-current={
                    selected === file.file_path ? 'true' : undefined
                  }
                  onClick={() => onOpen(reference(file))}
                >
                  <Icon name="file" />
                  <span>{file.file_path.split('/').at(-1)}</span>
                </button>
              </SourceHint>
              <SourceHint title={`在第二窗口打开 ${file.file_path}`}>
                <button
                  className="tree-pin icon-button"
                  aria-label={`在第二窗口打开 ${file.file_path}`}
                  onClick={() => onPin(reference(file))}
                >
                  <Icon name="pin" />
                </button>
              </SourceHint>
            </li>
          ))}
      </ul>
    );
  }
  return (
    <nav className="file-tree" aria-label="快照文件树">
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
  onSource,
  onSecondary,
  analysisId,
  scanId,
  onExplain,
  onCloseSource,
}: {
  files: SourceFile[];
  snapshotId: string;
  snapshotName?: string;
  reference: SourceRef | null;
  secondaryReference: SourceRef | null;
  onSource: (ref: SourceRef) => void;
  onSecondary: (ref: SourceRef | null) => void;
  analysisId?: string | null;
  scanId?: string | null;
  onExplain?: () => void;
  onCloseSource?: (
    replacement?: SourceRef | null,
    closeSecondary?: boolean,
  ) => void;
}) {
  const {
    container: sourceContainer,
    separator: treeSeparator,
    width: treeWidth,
    minimum: treeMinimum,
    maximum: treeMaximum,
    overlay: treeOverlay,
    available: treeResizeAvailable,
    dragging: treeResizing,
    onPointerDown: onTreePointerDown,
    onKeyDown: onTreeKeyDown,
  } = useSourceTreeResize();
  const treeId = useId();
  const codeId = useId();
  const [treeOpen, setTreeOpen] = useState(false),
    [activeWindow, setWindow] = useState<'primary' | 'secondary'>('primary');
  const [tabs, setTabs] = useState<SourceRef[]>([]);
  const [positions, setPositions] = useState<Record<string, number>>({});
  const [revealPath, setRevealPath] = useState<string>();
  const [collapseVersion, setCollapseVersion] = useState(0);
  const selectionKey = `${snapshotId}:${reference?.file_path}:${reference?.start_line}:${reference?.end_line}:${secondaryReference?.file_path}`;
  const [previousSelection, setPreviousSelection] = useState('');
  if (previousSelection !== selectionKey) {
    setPreviousSelection(selectionKey);
    const next = tabs.filter((tab) => tab.snapshot_id === snapshotId);
    for (const selected of [reference, secondaryReference]) {
      if (
        !selected ||
        selected.snapshot_id !== snapshotId ||
        !files.some((file) => file.file_path === selected.file_path)
      )
        continue;
      const index = next.findIndex(
        (tab) => tab.file_path === selected.file_path,
      );
      if (index < 0) next.push(selected);
      else if (selected === reference) next[index] = selected;
    }
    setTabs(next);
  }
  const activeFile = files.find(
    (file) =>
      reference?.snapshot_id === snapshotId &&
      file.snapshot_id === snapshotId &&
      file.file_path === reference.file_path,
  );
  const positionKey = (ref: SourceRef) =>
    `${ref.snapshot_id}:${ref.file_path}:${ref.start_line}:${ref.end_line}`;
  function closeTab(tab: SourceRef) {
    const index = tabs.findIndex((item) => item.file_path === tab.file_path);
    const next = tabs.filter((item) => item.file_path !== tab.file_path);
    setTabs(next);
    setPositions((previous) =>
      Object.fromEntries(
        Object.entries(previous).filter(
          ([key]) => !key.startsWith(`${tab.snapshot_id}:${tab.file_path}:`),
        ),
      ),
    );
    const closeSecondary = secondaryReference?.file_path === tab.file_path;
    if (reference?.file_path === tab.file_path) {
      const replacement = next[Math.max(0, index - 1)];
      onCloseSource?.(replacement ?? null, closeSecondary);
    } else if (closeSecondary) onSecondary(null);
    if (closeSecondary) setWindow('primary');
  }
  const treeButton = useRef<HTMLButtonElement>(null);
  const treeTrigger = useRef<HTMLButtonElement | null>(null);
  const treePanel = useRef<HTMLElement>(null);
  const [treeFocusRequest, requestTreeFocus] = useState(0);
  useEffect(() => {
    if (!treeOpen || !treeFocusRequest) return;
    // 提示组件在焦点事件中同步更新，移到提交完成后，关闭时取消待执行聚焦。
    const timer = globalThis.window.setTimeout(() => {
      const panel = treePanel.current;
      if (!panel || panel.closest('[hidden]')) return;
      const target =
        panel.querySelector<HTMLButtonElement>(
          '.tree-file[aria-current="true"]',
        ) ?? panel.querySelector<HTMLButtonElement>('.file-tree button');
      (target ?? panel).focus();
    }, 0);
    return () => globalThis.window.clearTimeout(timer);
  }, [treeFocusRequest, treeOpen]);
  useEffect(() => {
    function escape(event: KeyboardEvent) {
      if (event.key === 'Escape' && treeOpen) {
        setTreeOpen(false);
        (treeTrigger.current ?? treeButton.current)?.focus();
      }
    }
    globalThis.window.addEventListener('keydown', escape);
    return () => globalThis.window.removeEventListener('keydown', escape);
  }, [treeOpen]);
  return (
    <div
      ref={sourceContainer}
      className="source-workspace source-ide"
      style={{ '--source-tree-width': `${treeWidth}px` } as CSSProperties}
      data-window={activeWindow}
      data-split={!!secondaryReference}
      data-tree-overlay={treeOverlay}
      data-tree-resizing={treeResizing}
    >
      <button
        ref={treeButton}
        className="file-drawer-toggle"
        aria-expanded={treeOpen}
        onClick={(event) => {
          treeTrigger.current = event.currentTarget;
          setTreeOpen(!treeOpen);
        }}
      >
        <Icon name="folder" />
        项目结构
      </button>
      <aside
        ref={treePanel}
        id={treeId}
        tabIndex={-1}
        className="file-tree-panel surface"
        data-open={treeOpen}
      >
        <div
          className="source-tree-actions"
          role="toolbar"
          aria-label="目录操作"
        >
          <SourceHint title="折叠全部目录">
            <button
              className="icon-button"
              aria-label="折叠全部目录"
              disabled={!files.length}
              onClick={() => {
                setRevealPath(undefined);
                setCollapseVersion((value) => value + 1);
              }}
            >
              −
            </button>
          </SourceHint>
          <SourceHint title="定位当前文件">
            <button
              className="icon-button"
              aria-label="定位当前文件"
              disabled={!activeFile}
              onClick={() => setRevealPath(reference?.file_path)}
            >
              ⌖
            </button>
          </SourceHint>
          <button
            className="file-drawer-toggle icon-button"
            aria-label="关闭项目结构"
            onClick={() => {
              setTreeOpen(false);
              (treeTrigger.current ?? treeButton.current)?.focus();
            }}
          >
            <Icon name="close" />
          </button>
        </div>
        <FileTree
          files={files}
          search=""
          selected={reference?.file_path}
          revealPath={revealPath}
          collapseVersion={collapseVersion}
          onManualToggle={() => setRevealPath(undefined)}
          onOpen={(ref) => {
            onSource(ref);
            setWindow('primary');
            setTreeOpen(false);
            if (treeOpen && treeOverlay)
              (treeTrigger.current ?? treeButton.current)?.focus();
          }}
          onPin={(ref) => {
            onSecondary(ref);
            setWindow('secondary');
            setTreeOpen(false);
            if (treeOpen && treeOverlay)
              (treeTrigger.current ?? treeButton.current)?.focus();
          }}
        />
      </aside>
      <div
        ref={treeSeparator}
        className="source-tree-resizer"
        role="separator"
        tabIndex={treeResizeAvailable ? 0 : -1}
        aria-label="调整项目文件树宽度"
        title="拖动或按左右方向键调整目录宽度"
        aria-orientation="vertical"
        aria-valuemin={treeMinimum}
        aria-valuemax={treeMaximum}
        aria-valuenow={treeWidth}
        aria-valuetext={`${treeWidth} 像素`}
        aria-controls={`${treeId} ${codeId}`}
        aria-disabled={!treeResizeAvailable}
        onPointerDown={onTreePointerDown}
        onKeyDown={onTreeKeyDown}
      />
      <div id={codeId} className="code-workspace">
        <div className="source-editor-bar">
          <div
            className="source-file-tabs"
            role="tablist"
            aria-label="已打开文件"
          >
            {tabs.map((tab) => (
              <div
                className="source-file-tab"
                key={tab.file_path}
                data-active={reference?.file_path === tab.file_path}
              >
                <SourceHint title={tab.file_path}>
                  <button
                    role="tab"
                    aria-selected={reference?.file_path === tab.file_path}
                    aria-description={tab.file_path}
                    onClick={() => {
                      onSource(tab);
                      setWindow('primary');
                    }}
                  >
                    <Icon name="file" />
                    {tab.file_path.split('/').at(-1)}
                  </button>
                </SourceHint>
                <SourceHint title={`关闭文件 ${tab.file_path}`}>
                  <button
                    aria-label={`关闭文件 ${tab.file_path}`}
                    disabled={
                      reference?.file_path === tab.file_path && !onCloseSource
                    }
                    onClick={() => closeTab(tab)}
                  >
                    <Icon name="close" />
                  </button>
                </SourceHint>
              </div>
            ))}
            <SourceHint title="从文件树打开文件">
              <button
                className="source-open-file"
                aria-label="从文件树打开文件"
                onClick={(event) => {
                  treeTrigger.current = event.currentTarget;
                  setRevealPath(reference?.file_path);
                  setTreeOpen(true);
                  requestTreeFocus((value) => value + 1);
                }}
              >
                ＋
              </button>
            </SourceHint>
          </div>
          <div
            className="source-editor-actions"
            role="toolbar"
            aria-label="源码操作"
          >
            <SourceHint title={secondaryReference ? '关闭分屏' : '分屏浏览'}>
              <button
                className="icon-button"
                aria-label={secondaryReference ? '关闭分屏' : '分屏浏览'}
                disabled={!reference}
                onClick={() => {
                  onSecondary(secondaryReference ? null : reference);
                  setWindow('primary');
                }}
              >
                <Icon name="source" />
              </button>
            </SourceHint>
            {onExplain && (
              <SourceHint title="代码解读">
                <button
                  className="icon-button"
                  aria-label="代码解读"
                  onClick={onExplain}
                >
                  <Icon name="explanation" />
                </button>
              </SourceHint>
            )}
            <SourceHint
              title={`快照 ${snapshotName?.trim() || '未命名快照'} · 只读`}
            >
              <button
                className="icon-button source-info"
                aria-label="查看源码信息"
              >
                ⓘ
              </button>
            </SourceHint>
          </div>
        </div>
        {secondaryReference && (
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
              对照源码
            </button>
          </nav>
        )}
        <div className="code-pair">
          <div className="primary-code surface">
            {secondaryReference && (
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
            )}
            <SourceViewer
              files={files}
              snapshotId={snapshotId}
              snapshotName={snapshotName}
              reference={reference}
              onPosition={onSource}
              initialLine={
                reference ? positions[positionKey(reference)] : undefined
              }
              onVisibleLine={(line) => {
                if (reference)
                  setPositions((previous) => ({
                    ...previous,
                    [positionKey(reference)]: line,
                  }));
              }}
            />
          </div>
          {secondaryReference && (
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
                initialLine={positions[positionKey(secondaryReference)]}
                onVisibleLine={(line) =>
                  setPositions((previous) => ({
                    ...previous,
                    [positionKey(secondaryReference)]: line,
                  }))
                }
              />
            </div>
          )}
        </div>
        {activeFile && (
          <SourceEvidence
            key={`${activeFile.id}:${analysisId}:${scanId}`}
            file={activeFile}
            analysisId={analysisId}
            scanId={scanId}
            onSource={onSource}
          />
        )}
      </div>
    </div>
  );
}
