import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  Endpoint,
  Project,
  SourceFile,
  Snapshot,
} from '../shared/api/generated/schema';
import {
  listProjects,
  searchSnapshots,
} from '../features/projects/api/projects-api';
import { snapshotDisplayName } from '../features/projects/snapshot-name';
import { listEndpoints } from '../features/analysis';
import { Feedback } from '../shared/components/Feedback';
import { PageControls } from '../shared/components/PageControls';
import { ScrollPanel } from '../shared/components/ScrollPanel';
import { Icon } from '../shared/components/Icon';

export function WorkspaceSearch({
  snapshotId,
  analysisId,
  files,
  filesError,
  onProject,
  onSnapshot,
  onFile,
  onEndpoint,
}: {
  snapshotId: string | null;
  analysisId: string | null;
  files?: SourceFile[];
  filesError?: Error | null;
  onProject: (project: Project) => void;
  onSnapshot?: (snapshot: Snapshot, project: Project) => void;
  onFile: (file: SourceFile) => void;
  onEndpoint: (endpoint: Endpoint) => void;
}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [composing, setComposing] = useState(false);
  const [query, setQuery] = useState('');
  const expanded = open && !composing && !!query && query === input.trim();
  const container = useRef<HTMLDivElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const results = useRef<HTMLDivElement>(null);
  const resultsId = useId();
  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !container.current?.contains(event.target)
      )
        setOpen(false);
    };
    document.addEventListener('pointerdown', dismiss);
    return () => document.removeEventListener('pointerdown', dismiss);
  }, [open]);
  useLayoutEffect(() => {
    if (!expanded) return;
    const measure = () => {
      if (!container.current) return;
      const bottom = container.current.getBoundingClientRect().bottom;
      container.current.style.setProperty(
        '--search-results-height',
        `${Math.max(0, window.innerHeight - bottom - 16)}px`,
      );
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [expanded]);
  const client = useQueryClient();
  const [pages, setPages] = useState({
    projects: 1,
    snapshots: 1,
    files: 1,
    endpoints: 1,
  });
  useEffect(() => {
    if (composing) return;
    const timer = setTimeout(() => {
      setQuery([...input.trim()].slice(0, 200).join(''));
      setPages({ projects: 1, snapshots: 1, files: 1, endpoints: 1 });
    }, 200);
    return () => clearTimeout(timer);
  }, [input, composing, snapshotId, analysisId]);
  const projects = useQuery({
    queryKey: ['projects', 'search', query, pages.projects],
    queryFn: ({ signal }) => listProjects(pages.projects, signal, query),
    enabled: expanded,
    retry: false,
  });
  const snapshots = useQuery({
    queryKey: ['projects', 'snapshot-search', query, pages.snapshots],
    queryFn: ({ signal }) => searchSnapshots(pages.snapshots, signal, query),
    enabled: expanded && !!onSnapshot,
    retry: false,
  });
  const endpoints = useQuery({
    queryKey: [
      'analysis',
      'search',
      snapshotId,
      analysisId,
      query,
      pages.endpoints,
    ],
    queryFn: ({ signal }) =>
      listEndpoints(snapshotId!, analysisId!, pages.endpoints, signal, query),
    enabled: expanded && !!snapshotId && !!analysisId,
    retry: false,
  });
  useEffect(() => {
    if (!expanded) return;
    return () => {
      void client.cancelQueries({
        queryKey: ['projects', 'search', query, pages.projects],
        exact: true,
      });
      void client.cancelQueries({
        queryKey: ['projects', 'snapshot-search', query, pages.snapshots],
        exact: true,
      });
      void client.cancelQueries({
        queryKey: [
          'analysis',
          'search',
          snapshotId,
          analysisId,
          query,
          pages.endpoints,
        ],
        exact: true,
      });
    };
  }, [
    expanded,
    client,
    query,
    snapshotId,
    analysisId,
    pages.projects,
    pages.snapshots,
    pages.endpoints,
  ]);
  const matches = files?.filter((file) =>
    file.file_path.toLowerCase().includes(query.toLowerCase()),
  );
  const select = <T,>(value: T, handler: (value: T) => void) => {
    handler(value);
    setOpen(false);
  };
  return (
    <div
      ref={container}
      className="workspace-search"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
      onKeyDown={(event) => {
        if (
          composing ||
          event.nativeEvent.isComposing ||
          event.key !== 'Escape'
        )
          return;
        event.preventDefault();
        searchInput.current?.focus();
        setOpen(false);
      }}
    >
      <label className="header-search">
        <Icon name="search" />
        <input
          ref={searchInput}
          aria-label="搜索项目、快照、文件、接口"
          aria-expanded={expanded}
          aria-controls={resultsId}
          value={input}
          maxLength={400}
          onFocus={() => setOpen(true)}
          onClick={() => setOpen(true)}
          onChange={(event) => {
            setInput([...event.target.value].slice(0, 200).join(''));
            setOpen(true);
          }}
          onCompositionStart={() => setComposing(true)}
          onCompositionEnd={() => setComposing(false)}
          onKeyDown={(event) => {
            if (
              !composing &&
              !event.nativeEvent.isComposing &&
              (event.ctrlKey || event.metaKey) &&
              event.key.toLowerCase() === 'k' &&
              !event.defaultPrevented &&
              !event.repeat
            ) {
              event.preventDefault();
              setOpen(true);
              return;
            }
            if (
              composing ||
              event.nativeEvent.isComposing ||
              !input.trim() ||
              !['ArrowDown', 'ArrowUp'].includes(event.key)
            )
              return;
            event.preventDefault();
            setOpen(true);
            const items = [
              ...(results.current?.querySelectorAll<HTMLButtonElement>(
                '[data-search-result]',
              ) ?? []),
            ];
            const target = event.key === 'ArrowDown' ? items[0] : items.at(-1);
            target?.focus();
            target?.scrollIntoView?.({ block: 'nearest' });
          }}
          placeholder="搜索项目、快照或关键词…"
        />
      </label>
      {expanded && (
        <div
          ref={results}
          id={resultsId}
          role="region"
          aria-label="搜索本地项目与当前上下文"
          className="workspace-search-results"
        >
          <ScrollPanel
            label="搜索结果"
            resetKey={`${query}|${snapshotId}|${analysisId}|${JSON.stringify(pages)}`}
          >
            <p className="muted">
              仅搜索名称与路径；不搜索源码全文。项目与快照覆盖全部可读项目。
            </p>
            <div
              onKeyDown={(event) => {
                if (
                  !['ArrowDown', 'ArrowUp'].includes(event.key) ||
                  !(event.target instanceof HTMLButtonElement) ||
                  !event.target.hasAttribute('data-search-result')
                )
                  return;
                event.preventDefault();
                const items = [
                  ...event.currentTarget.querySelectorAll<HTMLButtonElement>(
                    '[data-search-result]',
                  ),
                ];
                const index = items.indexOf(event.target);
                const target =
                  items[
                    (index +
                      (event.key === 'ArrowDown' ? 1 : -1) +
                      items.length) %
                      items.length
                  ];
                target?.focus();
                target?.scrollIntoView?.({ block: 'nearest' });
              }}
            >
              <section
                className="global-search-group"
                aria-label="项目搜索结果"
              >
                <h3>本地项目</h3>
                <Feedback
                  error={projects.error}
                  retry={() => void projects.refetch()}
                />
                {projects.isFetching && <p role="status">正在搜索项目…</p>}
                {projects.data && (
                  <>
                    <PageControls
                      page={pages.projects}
                      previous={projects.data.previous}
                      next={projects.data.next}
                      onPage={(projects) => setPages({ ...pages, projects })}
                    />
                    {!projects.data.results.length && <p>没有匹配的项目。</p>}
                    {projects.data.results.map((project) => (
                      <button
                        type="button"
                        data-search-result
                        className="global-search-result"
                        key={project.id}
                        onClick={() => select(project, onProject)}
                      >
                        {project.name}
                      </button>
                    ))}
                  </>
                )}
              </section>
              {onSnapshot && (
                <section
                  className="global-search-group"
                  aria-label="快照搜索结果"
                >
                  <h3>版本快照</h3>
                  <Feedback
                    error={snapshots.error}
                    retry={() => void snapshots.refetch()}
                  />
                  {snapshots.isFetching && <p role="status">正在搜索快照…</p>}
                  {snapshots.data && (
                    <>
                      <PageControls
                        page={pages.snapshots}
                        previous={snapshots.data.previous}
                        next={snapshots.data.next}
                        onPage={(snapshots) =>
                          setPages({ ...pages, snapshots })
                        }
                      />
                      {!snapshots.data.results.length && (
                        <p>没有匹配的快照。</p>
                      )}
                      {snapshots.data.results.map((item) => (
                        <button
                          type="button"
                          data-search-result
                          className="global-search-result"
                          key={item.snapshot.id}
                          onClick={() =>
                            select(item, ({ snapshot, project }) =>
                              onSnapshot(snapshot, project),
                            )
                          }
                        >
                          {snapshotDisplayName(item.snapshot)}
                          <small>{item.project.name}</small>
                        </button>
                      ))}
                    </>
                  )}
                </section>
              )}
              <section
                className="global-search-group"
                aria-label="文件搜索结果"
              >
                <h3>当前快照文件</h3>
                {!snapshotId ? (
                  <p>尚未选择可读取的快照。</p>
                ) : filesError ? (
                  <Feedback error={filesError} />
                ) : !files ? (
                  <p role="status">正在读取完整文件清单…</p>
                ) : (
                  <>
                    <PageControls
                      page={pages.files}
                      previous={pages.files > 1 ? 'previous' : null}
                      next={pages.files * 20 < matches!.length ? 'next' : null}
                      onPage={(files) => setPages({ ...pages, files })}
                    />
                    {!matches!.length && <p>没有匹配的文件。</p>}
                    {matches!
                      .slice((pages.files - 1) * 20, pages.files * 20)
                      .map((file) => (
                        <button
                          type="button"
                          data-search-result
                          className="global-search-result"
                          key={file.id}
                          onClick={() => select(file, onFile)}
                        >
                          {file.file_path}
                        </button>
                      ))}
                  </>
                )}
              </section>
              <section
                className="global-search-group"
                aria-label="接口搜索结果"
              >
                <h3>当前分析接口</h3>
                {!analysisId || !snapshotId ? (
                  <p>尚未选择可读取的分析。</p>
                ) : (
                  <>
                    <Feedback
                      error={endpoints.error}
                      retry={() => void endpoints.refetch()}
                    />
                    {endpoints.isFetching && <p role="status">正在搜索接口…</p>}
                    {endpoints.data && (
                      <>
                        <PageControls
                          page={pages.endpoints}
                          previous={endpoints.data.previous}
                          next={endpoints.data.next}
                          onPage={(endpoints) =>
                            setPages({ ...pages, endpoints })
                          }
                        />
                        {!endpoints.data.results.length && (
                          <p>没有匹配的接口。</p>
                        )}
                        {endpoints.data.results.map((endpoint) => (
                          <button
                            type="button"
                            data-search-result
                            className="global-search-result"
                            key={endpoint.index}
                            onClick={() => select(endpoint, onEndpoint)}
                          >
                            {endpoint.method} {endpoint.path}
                          </button>
                        ))}
                      </>
                    )}
                  </>
                )}
              </section>
            </div>
          </ScrollPanel>
        </div>
      )}
    </div>
  );
}
