import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '../../shared/api/client';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { WorkspaceDialog } from '../../shared/components/WorkspaceDialog';
import {
  listNotifications,
  readAllNotifications,
  readNotification,
} from './api/notifications-api';

const kinds: Record<string, string> = {
  import: '项目导入',
  analysis: '源码分析',
  explanation: '模型讲解',
  lab: '受控实验',
  snapshot_comparison: '快照对比',
  system_check: '系统检查',
};
export function NotificationControl({
  onTask,
  active = true,
}: {
  onTask: (id: string) => void;
  active?: boolean;
}) {
  const [open, setOpen] = useState(false),
    [page, setPage] = useState(1);
  const [visible, setVisible] = useState(document.visibilityState !== 'hidden');
  const [pending, setPending] = useState(false),
    [error, setError] = useState<Error | null>(null),
    [message, setMessage] = useState('');
  const operation = useRef<AbortController | null>(null);
  const client = useQueryClient();
  useEffect(() => {
    const change = () => setVisible(document.visibilityState !== 'hidden');
    document.addEventListener('visibilitychange', change);
    return () => {
      document.removeEventListener('visibilitychange', change);
      operation.current?.abort();
    };
  }, []);
  const notifications = useQuery({
    queryKey: ['notifications', page],
    queryFn: ({ signal }) => listNotifications(page, signal),
    enabled: active && (visible || open),
    retry: false,
    refetchInterval: active && visible ? 5000 : false,
    refetchIntervalInBackground: false,
  });
  async function mark(id?: string) {
    if (!notifications.data || pending) return;
    const boundary = notifications.data.as_of;
    setPending(true);
    setError(null);
    setMessage('');
    const controller = new AbortController();
    operation.current = controller;
    try {
      if (id) await readNotification(id, controller.signal);
      else await readAllNotifications(boundary, controller.signal);
      await client.invalidateQueries({ queryKey: ['notifications'] });
      setMessage(
        id ? '已标记已读。' : '本次列表读取时点之前完成的任务已标记已读。',
      );
    } catch (failure) {
      if (controller.signal.aborted) return;
      setError(
        failure instanceof Error ? failure : new Error('已读状态保存失败。'),
      );
      if (
        failure instanceof ApiError &&
        (failure.status === 0 || failure.status >= 500)
      ) {
        const response = await notifications.refetch();
        const verified = id
          ? response.data?.results.find((item) => item.job.id === id)?.read ===
            true
          : !!response.data?.read_through &&
            Date.parse(response.data.read_through) >= Date.parse(boundary);
        if (verified) {
          setError(null);
          setMessage('读取已核实：已读状态已保存。');
        } else
          setMessage(
            '提交结果尚未核实。请刷新读取状态；本次不会自动重试写入。',
          );
      }
    } finally {
      if (!controller.signal.aborted) setPending(false);
    }
  }
  return (
    <>
      <button
        type="button"
        className="icon-button notification-bell"
        aria-label={`任务通知${notifications.data ? `，${notifications.data.unread_count} 条未读` : '，未读数未取得'}`}
        title="任务通知"
        onClick={() => setOpen(true)}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          aria-hidden="true"
        >
          <path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5l-2 3Zm5 3h4M12 2v2" />
        </svg>
        {!!notifications.data?.unread_count && (
          <span>
            {notifications.data.unread_count > 99
              ? '99+'
              : notifications.data.unread_count}
          </span>
        )}
      </button>
      <WorkspaceDialog
        open={open}
        title="任务通知"
        onClose={() => setOpen(false)}
        resetKey={String(page)}
      >
        <p>来自已完成或失败的真实任务。打开通知或查看任务不会自动标记已读。</p>
        <div className="notification-actions">
          <button
            type="button"
            data-dialog-autofocus
            disabled={pending || !notifications.data}
            onClick={() => void mark()}
          >
            全部标记已读
          </button>
          <button type="button" onClick={() => void notifications.refetch()}>
            刷新通知
          </button>
        </div>
        <Feedback
          error={notifications.error ?? error}
          retry={() => void notifications.refetch()}
        />
        {message && <p role="status">{message}</p>}
        {!notifications.data ? (
          <p role="status">
            {notifications.isFetching ? '正在读取通知…' : '尚未取得通知。'}
          </p>
        ) : (
          <>
            <p className="muted">
              未读 {notifications.data.unread_count} 条 · 读取时间{' '}
              {new Date(notifications.data.as_of).toLocaleString('zh-CN')}
            </p>
            <PageControls
              page={page}
              previous={notifications.data.previous}
              next={notifications.data.next}
              onPage={setPage}
            />
            {!notifications.data.results.length && (
              <p>暂无已完成或失败的任务。</p>
            )}
            {notifications.data.results.map(({ job, read }) => (
              <article className="notification-record" key={job.id}>
                <p>
                  <strong>
                    {kinds[job.kind]} ·{' '}
                    {job.status === 'succeeded' ? '已完成' : '失败'}
                  </strong>{' '}
                  · {read ? '已读' : '未读'}
                </p>
                <p>
                  <time dateTime={job.updated_at}>
                    {new Date(job.updated_at).toLocaleString('zh-CN')}
                  </time>
                </p>
                {job.error && (
                  <p>
                    {job.error.message} · 请求标识 {job.error.request_id}
                  </p>
                )}
                <div className="notification-actions">
                  <button
                    type="button"
                    onClick={() => {
                      onTask(job.id);
                      setOpen(false);
                    }}
                  >
                    查看任务
                  </button>
                  <button
                    type="button"
                    disabled={read || pending}
                    onClick={() => void mark(job.id)}
                  >
                    {read ? '已读' : '标记已读'}
                  </button>
                </div>
              </article>
            ))}
          </>
        )}
      </WorkspaceDialog>
    </>
  );
}
