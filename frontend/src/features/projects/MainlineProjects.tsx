import { useRef, useState } from 'react';
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { Button } from 'antd';
import type {
  Job,
  Project,
  ProjectSummary,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { WorkspaceDialog } from '../../shared/components/WorkspaceDialog';
import { Icon } from '../../shared/components/Icon';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import { archiveValidationMessage } from './archive-validation';
import { selectFolder, type FolderSelection } from './folder-validation';
import {
  createProject,
  importArchive,
  listProjects,
  listSnapshots,
} from './api/projects-api';
import {
  deleteTarget,
  getDeletionPreview,
  importFolder,
  listProjectManagement,
  type ProjectOrdering,
} from './api/mainline-api';
import { snapshotDisplayName } from './snapshot-name';
import { SnapshotNameForm } from './SnapshotNameForm';
import {
  ProjectActivitySidebar,
  formatProjectTime,
  preparationLabels,
} from './ProjectActivity';
import './MainlineProjects.css';

type ImportInput = {
  name: string;
  projectId: string | null;
  archive: File | null;
  folder: FolderSelection | null;
};
export function MainlineImport({
  project,
  onSubmitted,
  sourceMode,
  onSourceMode,
}: {
  project: Project | null;
  onSubmitted: (projectId: string, job: Job) => void;
  sourceMode?: 'zip' | 'folder';
  onSourceMode?: (mode: 'zip' | 'folder') => void;
}) {
  const [selectedMode, setMode] = useState<'zip' | 'folder'>('zip');
  const mode = sourceMode ?? selectedMode;
  const [projectChoice, setProjectChoice] = useState({
    id: project?.id ?? null,
    create: !project,
  });
  const newProject =
    projectChoice.id === (project?.id ?? null)
      ? projectChoice.create
      : !project;
  const [name, setName] = useState('');
  const [archive, setArchive] = useState<File | null>(null);
  const [folder, setFolder] = useState<FolderSelection | null>(null);
  const [selectionError, setSelectionError] = useState<Error | null>(null);
  const directory = useRef<HTMLInputElement>(null);
  const createdProject = useRef<{ name: string; id: string } | null>(null);
  const operation = useIdempotentOperation<
    ImportInput,
    { projectId: string; job: Job }
  >(
    'mainline-import',
    (input) =>
      new Blob([
        JSON.stringify({
          name: input.name.trim(),
          projectId: input.projectId,
          mode: input.folder ? 'folder' : 'zip',
        }),
        ...(input.folder
          ? input.folder.entries.flatMap(({ path, file }) => [
              JSON.stringify(path),
              file,
            ])
          : [input.archive!]),
      ]),
    async (input, key, signal) => {
      const projectId =
        input.projectId ??
        (createdProject.current?.name === input.name.trim()
          ? createdProject.current.id
          : (await createProject(input.name.trim(), key, signal)).id);
      if (!input.projectId)
        createdProject.current = { name: input.name.trim(), id: projectId };
      const job = input.folder
        ? await importFolder(projectId, input.folder, key, signal)
        : await importArchive(projectId, input.archive!, key, signal);
      return { projectId, job };
    },
    ({ projectId, job }) => {
      createdProject.current = null;
      setArchive(null);
      setFolder(null);
      setName('');
      onSubmitted(projectId, job);
    },
  );
  const valid =
    mode === 'zip' ? !!archive && !archiveValidationMessage(archive) : !!folder;
  return (
    <form
      className="workspace-form mainline-import"
      onSubmit={(event) => {
        event.preventDefault();
        if (valid && (newProject ? name.trim() : project))
          operation.start({
            name,
            projectId: newProject ? null : project!.id,
            archive: mode === 'zip' ? archive : null,
            folder: mode === 'folder' ? folder : null,
          });
      }}
    >
      <h2>{newProject ? '导入源码，开始阅读' : '导入项目的新快照'}</h2>
      {project && (
        <label>
          <input
            type="checkbox"
            checked={newProject}
            onChange={(event) =>
              setProjectChoice({
                id: project?.id ?? null,
                create: event.target.checked,
              })
            }
          />
          创建新项目
        </label>
      )}
      <div className="mainline-choice" role="group" aria-label="导入来源">
        <Button
          aria-pressed={mode === 'zip'}
          onClick={() => {
            setMode('zip');
            onSourceMode?.('zip');
          }}
        >
          ZIP 文件
        </Button>
        <Button
          aria-pressed={mode === 'folder'}
          onClick={() => {
            setMode('folder');
            onSourceMode?.('folder');
          }}
        >
          源码文件夹
        </Button>
      </div>
      {mode === 'zip' ? (
        <label>
          选择源码 ZIP
          <input
            type="file"
            accept=".zip"
            onChange={(event) => {
              const file = event.target.files?.[0] ?? null;
              setArchive(file);
              setSelectionError(null);
              if (file) setName(file.name.replace(/\.zip$/i, ''));
            }}
          />
        </label>
      ) : (
        <label>
          选择源码目录
          <input
            type="file"
            multiple
            ref={(node) => {
              directory.current = node;
              node?.setAttribute('webkitdirectory', '');
            }}
            onChange={(event) => {
              try {
                const result = selectFolder([...(event.target.files ?? [])]);
                setFolder(result);
                setName(result.name);
                setSelectionError(null);
              } catch (error) {
                setFolder(null);
                setSelectionError(
                  error instanceof Error ? error : new Error('无法读取目录。'),
                );
              }
            }}
          />
        </label>
      )}
      {newProject && (
        <label>
          项目名称
          <input
            required
            maxLength={200}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
      )}
      {!newProject && project && (
        <p>
          保存到：<strong>{project.name}</strong>
        </p>
      )}
      <p className="mainline-help">
        ZIP 上限 20 MiB；目录最多 2000 个有效文件、单文件 1 MiB、合计 100
        MiB。自动排除环境、依赖、构建产物与敏感文件，只读分析源码。
      </p>
      {folder && mode === 'folder' && (
        <p role="status">
          已选择 {folder.entries.length} 个文件 ·{' '}
          {(folder.bytes / 1024 / 1024).toFixed(2)} MiB · 排除 {folder.excluded}{' '}
          个文件
        </p>
      )}
      <Feedback
        error={
          selectionError ??
          (archive && mode === 'zip' && archiveValidationMessage(archive)
            ? new Error(archiveValidationMessage(archive)!)
            : operation.error)
        }
      />
      <Button
        type="primary"
        htmlType="submit"
        disabled={!valid || !!selectionError}
        loading={operation.isPending}
      >
        {operation.pending ? '恢复本次导入' : '导入并自动识别'}
      </Button>
      {operation.pending && (
        <p>提交结果尚未确认时，请保留相同名称和原文件，恢复同一操作。</p>
      )}
    </form>
  );
}

export function DeletionControl({
  kind,
  id,
  onJob,
}: {
  kind: 'project' | 'snapshot';
  id: string;
  onJob: (job: Job) => void;
}) {
  const [open, setOpen] = useState(false),
    [confirmed, setConfirmed] = useState(false);
  const preview = useQuery({
    queryKey: ['deletion-preview', kind, id],
    queryFn: ({ signal }) => getDeletionPreview(kind, id, signal),
    enabled: open,
    staleTime: 0,
  });
  const operation = useIdempotentOperation<string, Job>(
    `delete.${kind}.${id}`,
    (digest) => digest,
    (digest, key, signal) =>
      deleteTarget(
        { ...preview.data!, confirmation_digest: digest },
        key,
        signal,
      ),
    (job) => {
      setOpen(false);
      onJob(job);
    },
  );
  return (
    <>
      <Button
        danger
        onClick={() => {
          setConfirmed(false);
          setOpen(true);
          void preview.refetch();
        }}
      >
        删除{kind === 'project' ? '项目' : '快照'}
      </Button>
      <WorkspaceDialog
        open={open}
        onClose={() => setOpen(false)}
        title="确认永久删除内部副本"
      >
        <Feedback
          error={preview.error ?? operation.error}
          retry={() => {
            setConfirmed(false);
            void preview.refetch();
          }}
        />
        {preview.isPending && <p role="status">正在核对清理范围…</p>}
        {preview.data && (
          <>
            <p>
              <strong>{preview.data.object_name}</strong>{' '}
              的内部副本及关联结果将永久清理；原 ZIP
              和原目录保持原样，操作日志与必要任务摘要保留。
            </p>
            <dl className="deletion-scope">
              {Object.entries(preview.data.scope).map(([key, count]) => (
                <div key={key}>
                  <dt>
                    {{
                      snapshots: '快照',
                      files: '源码文件',
                      analyses: '接口分析',
                      source_scans: '源码扫描',
                      explanations: '模型讲解',
                      attempts: '历史作答',
                      lab_runs: '历史实验',
                      comparisons: '历史对比',
                    }[key] ?? key}
                  </dt>
                  <dd>{count}</dd>
                </div>
              ))}
            </dl>
            {!preview.data.can_delete && (
              <p role="alert">
                目标正在接收文件或执行任务，请等待任务结束再删除。
              </p>
            )}
            <label>
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              我确认永久删除上述内部副本及结果。
            </label>
            <Button
              danger
              type="primary"
              disabled={
                !confirmed || !preview.data.can_delete || preview.isFetching
              }
              loading={operation.isPending}
              onClick={() => operation.start(preview.data!.confirmation_digest)}
            >
              提交永久删除
            </Button>
          </>
        )}
      </WorkspaceDialog>
    </>
  );
}

export function MainlineProjects({
  projectId,
  snapshotId,
  project,
  onProject,
  onSnapshot,
  onSubmitted,
  onDelete,
  onOpenSnapshot,
  onLogs,
  active = true,
}: {
  projectId: string | null;
  snapshotId: string | null;
  project: Project | null;
  onProject: (id: string) => void;
  onSnapshot: (id: string) => void;
  onSubmitted: (projectId: string, job: Job) => void;
  onDelete: (job: Job) => void;
  onOpenSnapshot?: (projectId: string, snapshotId: string) => void;
  onLogs?: () => void;
  active?: boolean;
}) {
  const [page, setPage] = useState(1),
    [query, setQuery] = useState(''),
    [technology, setTechnology] = useState(''),
    [ordering, setOrdering] = useState<ProjectOrdering>('recent_import'),
    [expandedId, setExpandedId] = useState<string | null>(projectId),
    [importOpen, setImportOpen] = useState(false),
    [sourceMode, setSourceMode] = useState<'zip' | 'folder'>('zip'),
    [importProject, setImportProject] = useState<Project | null>(project),
    [chooseExisting, setChooseExisting] = useState(false),
    [choicePage, setChoicePage] = useState(1),
    [createOpen, setCreateOpen] = useState(false),
    [newName, setNewName] = useState('');
  const cache = useQueryClient();
  const projects = useQuery({
    queryKey: ['projects', 'management', page, query, technology, ordering],
    queryFn: ({ signal }) =>
      listProjectManagement(page, signal, query, technology, ordering),
    placeholderData: keepPreviousData,
    enabled: active,
  });
  const choices = useQuery({
    queryKey: ['projects', 'import-choices', choicePage],
    queryFn: ({ signal }) => listProjects(choicePage, signal),
    enabled: importOpen && chooseExisting,
  });
  const creation = useIdempotentOperation<string, Project>(
    'mainline-create-project',
    (name) => name.trim(),
    (name, key, signal) => createProject(name.trim(), key, signal),
    (created) => {
      void cache.invalidateQueries({ queryKey: ['projects'] });
      setCreateOpen(false);
      setImportProject(created);
      setExpandedId(created.id);
      onProject(created.id);
    },
  );
  const openSnapshot = (owner: string, snapshot: string) => {
    if (onOpenSnapshot) onOpenSnapshot(owner, snapshot);
    else if (owner === projectId) onSnapshot(snapshot);
    else onProject(owner);
  };
  function openImport(
    target: Project | null,
    mode: 'zip' | 'folder' = 'zip',
    choose = false,
  ) {
    setImportProject(target);
    setSourceMode(mode);
    setChooseExisting(choose);
    setImportOpen(true);
  }
  return (
    <div className="project-management-grid">
      <div className="project-management-main">
        <section className="project-import-banner" aria-label="源码导入">
          <div className="project-import-primary">
            <div className="project-import-intro">
              <span className="project-import-symbol">
                <Icon name="import" />
              </span>
              <div>
                <h2>导入源码，开始解读</h2>
                <p>
                  支持上传 ZIP 压缩包或选择本地源码文件夹
                  <br />
                  导入后自动识别项目结构、知识与根路由
                </p>
              </div>
            </div>
            <div className="project-import-actions">
              <Button type="primary" onClick={() => openImport(null)}>
                <Icon name="import" />
                上传 ZIP 压缩包
              </Button>
              <Button onClick={() => openImport(null, 'folder')}>
                <Icon name="folder" />
                选择源码文件夹
              </Button>
            </div>
            <p className="project-import-limits">
              ZIP ≤ 20 MiB · 目录有效文件 ≤ 100 MiB、2000 个 · 源码只读分析
            </p>
          </div>
          <div className="project-import-secondary">
            <button type="button" onClick={() => setCreateOpen(true)}>
              <span className="project-action-symbol">＋</span>
              <span>
                <strong>新建项目</strong>
                <small>创建空白项目，稍后导入源码</small>
              </span>
              <span aria-hidden="true">›</span>
            </button>
            <button
              type="button"
              onClick={() => openImport(project, 'zip', true)}
            >
              <span className="project-action-symbol">
                <Icon name="folder" />
              </span>
              <span>
                <strong>导入到已有项目</strong>
                <small>为现有项目导入新版本源码</small>
              </span>
              <span aria-hidden="true">›</span>
            </button>
          </div>
        </section>
        <section className="project-catalog" aria-label="我的项目">
          <header className="project-catalog-header">
            <h2>
              我的项目{' '}
              {projects.data && (
                <span className="project-count">{projects.data.count}</span>
              )}
            </h2>
            <div className="project-catalog-controls">
              <label className="project-catalog-search">
                <Icon name="search" />
                <input
                  aria-label="搜索项目"
                  placeholder="搜索项目…"
                  maxLength={200}
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setPage(1);
                  }}
                />
              </label>
              <select
                aria-label="项目技术"
                value={technology}
                onChange={(event) => {
                  setTechnology(event.target.value);
                  setPage(1);
                }}
              >
                <option value="">全部技术</option>
                {projects.data?.technologies.map((name) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
              <select
                aria-label="项目排序"
                value={ordering}
                onChange={(event) => {
                  setOrdering(event.target.value as ProjectOrdering);
                  setPage(1);
                }}
              >
                <option value="recent_import">最近导入</option>
                <option value="created">最新创建</option>
                <option value="name">名称排序</option>
              </select>
            </div>
          </header>
          <Feedback
            error={projects.error}
            retry={() => void projects.refetch()}
          />
          {projects.isPending && <p role="status">读取项目…</p>}
          {projects.data?.results.map((item) => (
            <ProjectCard
              key={item.project.id}
              item={item}
              expanded={expandedId === item.project.id}
              snapshotId={snapshotId}
              onToggle={() =>
                setExpandedId(
                  expandedId === item.project.id ? null : item.project.id,
                )
              }
              onOpenSnapshot={openSnapshot}
              onImport={() => openImport(item.project)}
              onDelete={onDelete}
              active={active}
            />
          ))}
          {projects.data && !projects.data.count && (
            <div className="surface project-empty">
              <Icon name="folder" />
              <h3>{query || technology ? '没有匹配的项目' : '还没有项目'}</h3>
              <p>
                {query || technology
                  ? '调整搜索关键词或技术筛选后再试。'
                  : '上传源码或创建空白项目，开始整理项目版本。'}
              </p>
            </div>
          )}
          {projects.data && (
            <footer className="project-catalog-footer">
              <small>共 {projects.data.count} 个项目 · 每批 10 个</small>
              <PageControls page={page} {...projects.data} onPage={setPage} />
            </footer>
          )}
        </section>
      </div>
      <ProjectActivitySidebar
        onOpenSnapshot={openSnapshot}
        onLogs={onLogs}
        active={active}
      />
      <WorkspaceDialog
        open={importOpen}
        title="导入项目源码"
        onClose={() => setImportOpen(false)}
      >
        {chooseExisting && (
          <section className="project-import-target">
            <label>
              选择已有项目
              <select
                aria-label="选择已有项目"
                value={importProject?.id ?? ''}
                onChange={(event) =>
                  setImportProject(
                    choices.data?.results.find(
                      (item) => item.id === event.target.value,
                    ) ?? null,
                  )
                }
              >
                <option value="">请选择项目</option>
                {importProject &&
                  !choices.data?.results.some(
                    (item) => item.id === importProject.id,
                  ) && (
                    <option value={importProject.id}>
                      {importProject.name}
                    </option>
                  )}
                {choices.data?.results.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <Feedback
              error={choices.error}
              retry={() => void choices.refetch()}
            />
            {choices.data && (
              <PageControls
                page={choicePage}
                {...choices.data}
                onPage={setChoicePage}
              />
            )}
          </section>
        )}
        <div hidden={chooseExisting && !importProject}>
          <MainlineImport
            project={importProject}
            sourceMode={sourceMode}
            onSourceMode={setSourceMode}
            onSubmitted={(id, job) => {
              void cache.invalidateQueries({ queryKey: ['projects'] });
              setImportOpen(false);
              onSubmitted(id, job);
            }}
          />
        </div>
      </WorkspaceDialog>
      <WorkspaceDialog
        open={createOpen}
        title="新建空白项目"
        onClose={() => setCreateOpen(false)}
      >
        <form
          className="workspace-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (newName.trim()) creation.start(newName);
          }}
        >
          <label>
            项目名称
            <input
              data-dialog-autofocus
              required
              maxLength={200}
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
            />
          </label>
          <p>创建后可随时导入源码快照。</p>
          <Feedback error={creation.error} />
          <Button type="primary" htmlType="submit" loading={creation.isPending}>
            {creation.pending ? '恢复创建项目' : '创建项目'}
          </Button>
        </form>
      </WorkspaceDialog>
    </div>
  );
}

function ProjectCard({
  item,
  expanded,
  snapshotId,
  onToggle,
  onOpenSnapshot,
  onImport,
  onDelete,
  active,
}: {
  item: ProjectSummary;
  expanded: boolean;
  snapshotId: string | null;
  onToggle: () => void;
  onOpenSnapshot: (projectId: string, snapshotId: string) => void;
  onImport: () => void;
  onDelete: (job: Job) => void;
  active: boolean;
}) {
  const [page, setPage] = useState(1);
  const snapshots = useQuery({
    queryKey: ['projects', 'snapshots', item.project.id, page],
    queryFn: ({ signal }) => listSnapshots(item.project.id, page, signal),
    enabled: active && expanded,
  });
  return (
    <article className="surface project-card">
      <header className="project-card-header">
        <span className="project-folder-symbol">
          <Icon name="folder" />
        </span>
        <div className="project-card-heading">
          <h3>
            <button type="button" aria-expanded={expanded} onClick={onToggle}>
              {item.project.name}
            </button>
          </h3>
          <p>
            {item.latest_snapshot
              ? `${item.snapshot_count} 个版本快照 · 最新快照 ${item.latest_snapshot.summary.accepted} 个源码文件`
              : '空白项目，等待导入第一份源码'}
          </p>
          <div className="project-technology-tags">
            {item.technologies.length === 0 && <span>未识别</span>}
            {item.technologies.map((tag) => (
              <span
                key={`${tag.name}-${tag.evidence_kind}`}
                title={
                  {
                    language: '根据快照文件语言识别',
                    declaration: '来自持久化依赖声明，不代表已安装',
                    usage: '来自已发布扫描的源码引用或使用',
                  }[tag.evidence_kind]
                }
              >
                {tag.name}
                <small>
                  {
                    { language: '语言', declaration: '声明', usage: '使用' }[
                      tag.evidence_kind
                    ]
                  }
                </small>
              </span>
            ))}
          </div>
        </div>
        <div className="project-card-commands">
          <small>
            {item.last_imported_at
              ? `最近导入：${formatProjectTime(item.last_imported_at)}`
              : `创建于：${formatProjectTime(item.project.created_at)}`}
          </small>
          <div>
            <Button
              type="primary"
              disabled={!item.latest_snapshot}
              onClick={() =>
                item.latest_snapshot &&
                onOpenSnapshot(item.project.id, item.latest_snapshot.id)
              }
            >
              进入工作区
            </Button>
            <Button onClick={onImport}>导入新快照</Button>
            <DeletionControl
              kind="project"
              id={item.project.id}
              onJob={onDelete}
            />
            <button
              className="project-expand"
              type="button"
              aria-label={`${expanded ? '收起' : '展开'}${item.project.name}的快照`}
              aria-expanded={expanded}
              onClick={onToggle}
            >
              {expanded ? '⌃' : '⌄'}
            </button>
          </div>
        </div>
      </header>
      <section
        className="project-snapshots"
        hidden={!expanded}
        aria-label={`${item.project.name}的版本快照`}
      >
        <h4>
          版本快照{' '}
          <span className="project-count">
            {snapshots.data?.count ?? item.snapshot_count}
          </span>
        </h4>
        <Feedback
          error={snapshots.error}
          retry={() => void snapshots.refetch()}
        />
        {snapshots.isPending && expanded && <p role="status">读取快照…</p>}
        {snapshots.data?.results.map((snapshot) => (
          <div key={snapshot.id} className="project-snapshot-row">
            <div className="project-snapshot-name">
              <span
                className={`project-state-dot state-${snapshot.preparation_status}`}
              />
              <div>
                <strong>{snapshotDisplayName(snapshot)}</strong>
                <small>{snapshot.summary.accepted} 个文件</small>
              </div>
            </div>
            <div className="project-snapshot-fact">
              <small>导入时间</small>
              <span>{formatProjectTime(snapshot.created_at)}</span>
            </div>
            <div className="project-snapshot-fact">
              <small>识别结果</small>
              <span
                className={`project-status-tag state-${snapshot.preparation_status}`}
              >
                {preparationLabels[snapshot.preparation_status]}
              </span>
            </div>
            <div className="project-snapshot-fact">
              <small>根路由</small>
              <span>
                {snapshot.id === item.latest_snapshot?.id && item.root_path
                  ? item.root_path
                  : snapshot.preparation_status === 'needs_root'
                    ? '需要选择根路由'
                    : snapshot.preparation_status === 'no_root'
                      ? '未发现 · 源码知识可读'
                      : snapshot.analysis_id
                        ? '分析结果中查看'
                        : '等待识别'}
              </span>
            </div>
            <div className="project-snapshot-actions">
              <Button
                type="primary"
                aria-current={snapshotId === snapshot.id ? 'true' : undefined}
                onClick={() => onOpenSnapshot(item.project.id, snapshot.id)}
              >
                {snapshot.preparation_status === 'needs_root'
                  ? '选择根路由'
                  : '进入工作区'}
              </Button>
              <SnapshotNameForm snapshot={snapshot} />
              <DeletionControl
                kind="snapshot"
                id={snapshot.id}
                onJob={onDelete}
              />
            </div>
          </div>
        ))}
        {snapshots.data && !snapshots.data.count && <p>尚未导入快照。</p>}
        {snapshots.data && (
          <PageControls page={page} {...snapshots.data} onPage={setPage} />
        )}
      </section>
    </article>
  );
}
