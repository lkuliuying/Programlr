import { useId, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from 'antd';
import type { Job, Project } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import {
  createProject,
  importArchive,
  listProjects,
  listSnapshots,
} from './api/projects-api';
import { snapshotDisplayName } from './snapshot-name';
import { archiveValidationMessage } from './archive-validation';

export function ProjectNavigator({
  projectId,
  snapshotId,
  onProject,
  onSnapshot,
}: {
  projectId: string | null;
  snapshotId: string | null;
  onProject: (id: string) => void;
  onSnapshot: (id: string) => void;
}) {
  const [page, setPage] = useState(1),
    [name, setName] = useState('');
  const cache = useQueryClient();
  const projects = useQuery({
    queryKey: ['projects', 'list', page],
    queryFn: ({ signal }) => listProjects(page, signal),
  });
  const create = useIdempotentOperation<string, Project>(
    'create-project',
    (name) => name.trim(),
    (name, key, signal) => createProject(name.trim(), key, signal),
    (project) => {
      void cache.invalidateQueries({ queryKey: ['projects', 'list'] });
      setName('');
      onProject(project.id);
    },
  );
  return (
    <>
      <h2>项目与快照</h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          create.start(name);
        }}
        className="workspace-form"
      >
        <label>
          项目名称
          <input
            required
            maxLength={200}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <Button htmlType="submit" loading={create.isPending}>
          {create.pending ? '恢复创建项目' : '创建项目'}
        </Button>
        <Feedback error={create.error} />
        {create.pending && (
          <small>结果未确认时，请输入原名称恢复同一操作。</small>
        )}
      </form>
      <Feedback
        error={projects.error}
        retry={() => {
          void projects.refetch();
        }}
      />
      {projects.isPending && <p role="status">加载项目…</p>}
      {projects.data && (
        <>
          <ul className="workspace-nav">
            {projects.data.results.map((project) => (
              <li key={project.id}>
                <button
                  aria-current={projectId === project.id ? 'true' : undefined}
                  onClick={() => onProject(project.id)}
                >
                  {project.name}
                </button>
              </li>
            ))}
          </ul>
          {!projects.data.count && <p>还没有项目，先创建一个学习空间。</p>}
          <PageControls page={page} {...projects.data} onPage={setPage} />
        </>
      )}
      {projectId && (
        <SnapshotNavigator
          key={projectId}
          projectId={projectId}
          selected={snapshotId}
          onSelect={onSnapshot}
        />
      )}
    </>
  );
}
function SnapshotNavigator({
  projectId,
  selected,
  onSelect,
}: {
  projectId: string;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ['projects', 'snapshots', projectId, page],
    queryFn: ({ signal }) => listSnapshots(projectId, page, signal),
  });
  return (
    <section>
      <h3>源码快照</h3>
      <Feedback
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
      {query.isPending && <p role="status">加载快照…</p>}
      {query.data && (
        <>
          <ul className="workspace-nav">
            {query.data.results.map((snapshot) => (
              <li key={snapshot.id}>
                <button
                  onClick={() => onSelect(snapshot.id)}
                  aria-current={snapshot.id === selected ? 'true' : undefined}
                >
                  <strong>{snapshotDisplayName(snapshot)}</strong>
                  <time>
                    {new Date(snapshot.created_at).toLocaleString('zh-CN')}
                  </time>
                  <small>{snapshot.summary.accepted} 个文件</small>
                </button>
              </li>
            ))}
          </ul>
          {!query.data.count && <p>尚未导入快照。</p>}
          <PageControls page={page} {...query.data} onPage={setPage} />
        </>
      )}
    </section>
  );
}
export function ImportForm({
  projectId,
  onJob,
}: {
  projectId: string;
  onJob: (id: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [submittedFile, setSubmittedFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const helpId = useId();
  const errorId = useId();
  const validation = file ? archiveValidationMessage(file) : null;
  const operation = useIdempotentOperation<File, Job>(
    `import.${projectId}`,
    (file) => file,
    (file, key, signal) => importArchive(projectId, file, key, signal),
    (job) => onJob(job.id),
    onJob,
  );
  return (
    <form
      className="workspace-form archive-import"
      onSubmit={(event) => {
        event.preventDefault();
        if (file && !validation) {
          setSubmittedFile(file);
          operation.start(file);
        }
      }}
    >
      <label>
        导入源码 ZIP
        <input
          ref={input}
          type="file"
          required
          accept=".zip"
          disabled={operation.isPending}
          aria-invalid={!!validation}
          aria-describedby={`${helpId}${validation ? ` ${errorId}` : ''}`}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <small id={helpId}>
        ZIP 上限 20 MiB。仅静态读取，不会安装依赖或运行导入项目。
      </small>
      {file && (
        <div className="archive-selection">
          <div role="status">
            <strong>{file.name}</strong>
            <small>
              {file.size.toLocaleString('zh-CN')} 字节 · 上限 20 MiB
            </small>
          </div>
          <button
            type="button"
            disabled={operation.isPending}
            onClick={() => {
              setFile(null);
              if (input.current) {
                input.current.value = '';
                input.current.focus();
              }
            }}
          >
            移除文件
          </button>
        </div>
      )}
      {validation && (
        <p id={errorId} role="alert" className="archive-validation">
          {validation}
        </p>
      )}
      <Button
        htmlType="submit"
        type="primary"
        aria-label={operation.pending ? '恢复原 ZIP 导入' : '导入为新快照'}
        loading={operation.isPending}
        disabled={!file || !!validation}
      >
        {operation.pending ? '恢复原 ZIP 导入' : '导入为新快照'}
      </Button>
      {operation.pending && (
        <small>请重新选择原 ZIP，以相同操作标识恢复提交。</small>
      )}
      <Feedback error={submittedFile === file ? operation.error : null} />
    </form>
  );
}
