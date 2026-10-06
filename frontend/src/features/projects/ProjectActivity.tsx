import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { ProjectActivityItem } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { Icon } from '../../shared/components/Icon';
import { getProjectActivity } from './api/mainline-api';

export const preparationLabels: Record<string, string> = {
  pending: '等待识别',
  importing: '正在导入源码',
  scanning: '正在识别源码与知识',
  needs_root: '等待选择根路由',
  no_root: '未发现根路由',
  analyzing: '正在分析接口',
  ready: '识别完成',
  failed: '处理失败',
};
export const formatProjectTime = (value: string) =>
  new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
const jobLabels = {
  queued: '等待中',
  running: '进行中',
  succeeded: '已完成',
  failed: '失败',
};
const stageLabels: Record<string, string> = {
  queued: '等待执行',
  extracting: '解压源码',
  publishing: '保存快照',
  source_scanning: '扫描结构与知识',
  parsing: '分析接口',
  completed: '已完成',
  failed: '执行失败',
};

export function ProjectActivitySidebar({
  active,
  onOpenSnapshot,
  onLogs,
}: {
  active: boolean;
  onOpenSnapshot: (projectId: string, snapshotId: string) => void;
  onLogs?: () => void;
}) {
  const [desktop, setDesktop] = useState(
    () => window.matchMedia('(min-width: 1280px)').matches,
  );
  const [opened, setOpened] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const modalOpen = active && !desktop && opened;
  useEffect(() => {
    const media = window.matchMedia('(min-width: 1280px)');
    const change = (event: MediaQueryListEvent) => {
      setDesktop(event.matches);
      setOpened(false);
    };
    media.addEventListener('change', change);
    return () => media.removeEventListener('change', change);
  }, []);
  useLayoutEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (desktop) {
      // 使用同一内容树切换常驻侧栏和模态，保留帮助展开与执行记录状态。
      node.setAttribute('open', '');
      return () => node.removeAttribute('open');
    }
    if (!modalOpen) return;
    const origin =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    node.showModal();
    const background = [...document.body.children].filter(
      (element): element is HTMLElement =>
        element instanceof HTMLElement && !element.contains(node),
    );
    const inert = background.map((element) => element.inert);
    background.forEach((element) => {
      element.inert = true;
    });
    node.querySelector<HTMLButtonElement>('.project-activity-close')?.focus();
    return () => {
      node.close();
      background.forEach((element, index) => {
        element.inert = inert[index]!;
      });
      if (
        origin?.isConnected &&
        !window.matchMedia('(min-width: 1280px)').matches
      ) {
        origin.focus();
        queueMicrotask(() => {
          if (
            origin.isConnected &&
            !document.querySelector('dialog[open]:not([data-inline="true"])')
          )
            origin.focus();
        });
      }
    };
  }, [desktop, modalOpen]);
  return (
    <>
      <button
        type="button"
        className="project-activity-toggle"
        hidden={desktop}
        aria-haspopup="dialog"
        aria-expanded={modalOpen}
        onClick={() => setOpened(true)}
      >
        <Icon name="jobs" />
        导入状态与帮助
      </button>
      <dialog
        ref={dialog}
        className="project-activity-sidebar"
        data-inline={desktop}
        role={desktop ? 'presentation' : undefined}
        aria-label={desktop ? undefined : '导入状态与帮助'}
        onCancel={(event) => {
          event.preventDefault();
          setOpened(false);
        }}
        onClick={(event) => {
          if (!desktop && event.target === event.currentTarget)
            setOpened(false);
        }}
        onKeyDown={(event) => {
          if (desktop || event.key !== 'Tab') return;
          const items = [
            ...event.currentTarget.querySelectorAll<HTMLElement>(
              'button:not(:disabled),input:not(:disabled),a[href],select:not(:disabled),textarea:not(:disabled),summary',
            ),
          ].filter(
            (element) =>
              element.getClientRects().length && !element.closest('[hidden]'),
          );
          const first = items[0],
            last = items.at(-1);
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last?.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first?.focus();
          }
        }}
      >
        <div className="project-activity-content">
          <header className="project-activity-mobile-header" hidden={desktop}>
            <h2>导入状态与帮助</h2>
            <button
              type="button"
              className="project-activity-close"
              onClick={() => setOpened(false)}
            >
              关闭
            </button>
          </header>
          <ProjectActivity
            active={active && (desktop || opened)}
            onOpenSnapshot={(project, snapshot) => {
              setOpened(false);
              onOpenSnapshot(project, snapshot);
            }}
            onLogs={
              onLogs
                ? () => {
                    setOpened(false);
                    onLogs();
                  }
                : undefined
            }
          />
        </div>
      </dialog>
    </>
  );
}

function ActivityItem({
  item,
  onOpenSnapshot,
}: {
  item: ProjectActivityItem;
  onOpenSnapshot: (projectId: string, snapshotId: string) => void;
}) {
  return (
    <article className={`project-activity-item activity-${item.status}`}>
      <header>
        <span className="project-folder-symbol">
          <Icon name="folder" />
        </span>
        <div>
          <strong>{item.project.name}</strong>
          <p>{preparationLabels[item.status]}</p>
        </div>
      </header>
      <ol className="project-activity-stages">
        {item.stages.map((stage) => (
          <li key={stage.job.id} data-status={stage.job.status}>
            <span className="activity-stage-mark" aria-hidden="true">
              {stage.job.status === 'succeeded'
                ? '✓'
                : stage.job.status === 'failed'
                  ? '!'
                  : '•'}
            </span>
            <span>
              {
                {
                  import: '导入源码',
                  source_scan: '识别结构与知识',
                  analysis: '分析接口',
                }[stage.kind]
              }
              <small>{stageLabels[stage.job.stage] ?? stage.job.stage}</small>
            </span>
            <small>{jobLabels[stage.job.status]}</small>
          </li>
        ))}
      </ol>
      {item.status === 'needs_root' && (
        <p className="project-activity-note">
          发现 {item.root_count ?? '多个'} 个候选根，请进入工作区选择后继续。
        </p>
      )}
      {item.status === 'no_root' && (
        <p className="project-activity-note">
          源码与知识已可阅读；未执行接口分析。
        </p>
      )}
      {item.status === 'ready' && item.endpoint_count !== null && (
        <p className="project-activity-note">
          接口分析完成 · {item.endpoint_count} 个接口
        </p>
      )}
      {item.stages.find((stage) => stage.job.error)?.job.error && (
        <p role="alert">
          {item.stages.find((stage) => stage.job.error)!.job.error!.message}
        </p>
      )}
      {item.stages.some((stage) => stage.events.length) && (
        <details className="project-activity-events">
          <summary>查看执行记录</summary>
          <ol>
            {item.stages.flatMap((stage) =>
              stage.events
                .filter((event) => event.stage)
                .map((event, index) => (
                  <li key={`${stage.job.id}-${index}`}>
                    <time>{formatProjectTime(event.at)}</time> ·{' '}
                    {stageLabels[event.stage] ?? event.stage}
                    {event.error_code && <code> {event.error_code}</code>}
                  </li>
                )),
            )}
          </ol>
        </details>
      )}
      {item.snapshot && (
        <button
          type="button"
          className="project-text-action"
          onClick={() => onOpenSnapshot(item.project.id, item.snapshot!.id)}
        >
          {item.status === 'needs_root' ? '选择根路由' : '进入工作区'}{' '}
          <span aria-hidden="true">›</span>
        </button>
      )}
    </article>
  );
}

export function ProjectActivity({
  onOpenSnapshot,
  onLogs,
  active = true,
}: {
  onOpenSnapshot: (projectId: string, snapshotId: string) => void;
  onLogs?: () => void;
  active?: boolean;
}) {
  const activity = useQuery({
    queryKey: ['projects', 'activity'],
    queryFn: ({ signal }) => getProjectActivity(signal),
    enabled: active,
    refetchInterval: active ? 5000 : false,
    refetchIntervalInBackground: false,
  });
  return (
    <aside className="project-management-aside" aria-label="导入状态和帮助">
      <section className="surface project-activity-panel">
        <header>
          <h2>
            <Icon name="jobs" />
            导入与识别状态
          </h2>
          {onLogs && (
            <button
              type="button"
              className="project-text-action"
              onClick={onLogs}
            >
              查看全部
            </button>
          )}
        </header>
        <Feedback
          error={activity.error}
          retry={() => void activity.refetch()}
        />
        {activity.isPending && <p role="status">正在读取导入与识别状态…</p>}
        {activity.data && !activity.data.active.length && (
          <p className="project-aside-empty">暂无进行中或待处理的导入。</p>
        )}
        {activity.data?.active.map((item) => (
          <ActivityItem
            key={item.snapshot?.id ?? item.stages[0]?.job.id}
            item={item}
            onOpenSnapshot={onOpenSnapshot}
          />
        ))}
        {!!activity.data?.recent.length && (
          <div className="project-recent-completed">
            <h3>最近完成</h3>
            {activity.data.recent.map((item) => (
              <ActivityItem
                key={item.snapshot!.id}
                item={item}
                onOpenSnapshot={onOpenSnapshot}
              />
            ))}
          </div>
        )}
      </section>
      <section className="surface project-help-panel">
        <h2>
          <Icon name="learning" />
          常见问题
        </h2>
        <details>
          <summary>支持哪些源码与项目？</summary>
          <p>
            支持 ZIP 或源码目录导入，只读保留 Python、JavaScript、TypeScript
            源码及受支持的 Python 依赖声明。接口识别面向 Django /
            DRF；语言标签不代表已识别框架。
          </p>
        </details>
        <details>
          <summary>如何选择正确的根路由？</summary>
          <p>
            唯一根会自动继续分析。多个候选根时，进入工作区根据文件位置与识别依据选择；未发现根时仍可阅读源码和知识。
          </p>
        </details>
        <details>
          <summary>导入失败后怎么办？</summary>
          <p>
            先查看操作日志中的失败原因。提交结果未确认时，使用相同名称和原文件恢复本次导入，避免重复创建。
          </p>
        </details>
        <details>
          <summary>删除项目会影响原文件吗？</summary>
          <p>
            删除仅清理系统内部副本及关联结果，原 ZIP
            和目录不受影响。操作日志和必要任务摘要继续保留；提交前会展示实际清理范围。
          </p>
        </details>
      </section>
    </aside>
  );
}
