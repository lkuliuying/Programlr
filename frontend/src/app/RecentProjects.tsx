import { useQuery } from '@tanstack/react-query';
import {
  listProjects,
  listSnapshots,
  snapshotDisplayName,
} from '../features/projects';
import { queryJobs } from '../features/jobs';
import type { Project } from '../shared/api/generated/schema';
import { Feedback } from '../shared/components/Feedback';

function RecentProject({
  project,
  onProject,
  active,
}: {
  project: Project;
  onProject: (id: string) => void;
  active: boolean;
}) {
  const snapshots = useQuery({
    queryKey: ['projects', 'snapshots', project.id, 1],
    queryFn: ({ signal }) => listSnapshots(project.id, 1, signal),
    enabled: active,
    retry: false,
  });
  const snapshot = snapshots.data?.results[0];
  const jobs = useQuery({
    queryKey: ['jobs', 'history', snapshot?.id, 1],
    queryFn: ({ signal }) => queryJobs(snapshot!.id, 1, signal),
    enabled: active && !!snapshot,
    retry: false,
  });
  const job = jobs.data?.results[0];
  const state = snapshots.error
    ? '快照读取失败'
    : !snapshots.data
      ? '读取快照…'
      : !snapshot
        ? '尚未导入'
        : jobs.error
          ? '分析状态读取失败'
          : !jobs.data
            ? '读取分析状态…'
            : !job
              ? '待分析'
              : (
                  {
                    queued: '分析排队中',
                    running: '分析中',
                    failed: '分析失败',
                    succeeded: '已分析',
                  } as const
                )[job.status];
  return (
    <article className="dashboard-project-record" data-page-keep>
      <button type="button" onClick={() => onProject(project.id)}>
        {project.name}
      </button>
      <p>{snapshot ? snapshotDisplayName(snapshot) : state}</p>
      <p className="muted">
        <time dateTime={project.created_at}>
          创建于 {new Date(project.created_at).toLocaleString('zh-CN')}
        </time>{' '}
        · {state}
      </p>
      <Feedback
        error={snapshots.error ?? jobs.error}
        retry={() => {
          if (snapshots.error) void snapshots.refetch();
          else void jobs.refetch();
        }}
      />
    </article>
  );
}
export function RecentProjects({
  active,
  onProject,
}: {
  active: boolean;
  onProject: (id: string) => void;
}) {
  const projects = useQuery({
    queryKey: ['projects', 'list', 1],
    queryFn: ({ signal }) => listProjects(1, signal),
    enabled: active,
    retry: false,
  });
  return (
    <>
      <Feedback error={projects.error} retry={() => void projects.refetch()} />
      {!projects.data ? (
        <p role="status">
          {projects.isFetching ? '正在读取项目…' : '尚未取得项目列表。'}
        </p>
      ) : !projects.data.results.length ? (
        <p>暂无项目。创建一个项目开始学习。</p>
      ) : (
        projects.data.results
          .slice(0, 3)
          .map((project) => (
            <RecentProject
              key={project.id}
              project={project}
              active={active}
              onProject={onProject}
            />
          ))
      )}
    </>
  );
}
