import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Form, Input, Pagination, Spin } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '../../shared/api/client';
import { createTask, listTasks } from './api/tasks-api';

const storageKey = 'task-board.pending-key.v1';
type Pending = { key: string; title: string | null };

function readPending(): Pending | null {
  try {
    const key = sessionStorage.getItem(storageKey);
    return key ? { key, title: null } : null;
  } catch {
    return null;
  }
}

export function TaskBoard() {
  const [form] = Form.useForm<{ title: string }>();
  const [page, setPage] = useState(1);
  const [pending, setPending] = useState<Pending | null>(readPending);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const client = useQueryClient();
  const activeRequest = useRef<AbortController | null>(null);
  useEffect(() => () => activeRequest.current?.abort(), []);
  const tasks = useQuery({
    queryKey: ['task-board', 'tasks', page],
    queryFn: ({ signal }) => listTasks(page, signal),
    retry: false,
  });
  const creation = useMutation({
    mutationFn: ({
      title,
      key,
    }: {
      title: string;
      key: string;
      recovering: boolean;
    }) => {
      activeRequest.current = new AbortController();
      return createTask(title, key, activeRequest.current.signal);
    },
    retry: false,
    onSuccess: async () => {
      setNotice('任务已保存。');
      setError('');
      try {
        sessionStorage.removeItem(storageKey);
        setPending(null);
        form.resetFields();
      } catch {
        setError(
          '任务已保存，但浏览器未能清除操作标识；继续恢复仍会返回同一任务。',
        );
      }
      setPage(1);
      await client.invalidateQueries({ queryKey: ['task-board', 'tasks'] });
    },
    onError: (reason: Error, operation) => {
      const message =
        reason instanceof ApiError
          ? `${reason.message}${reason.requestId ? ` 请求标识：${reason.requestId}` : ''}`
          : '请求未完成，请恢复这次提交。';
      setError(message);
      if (reason instanceof ApiError && reason.fields.title)
        form.setFields([{ name: 'title', errors: reason.fields.title }]);
      // 恢复请求被拒绝不能证明原请求未写入，必须保留原键并允许重填原标题。
      if (
        reason instanceof ApiError &&
        operation.recovering &&
        [400, 403, 409, 413, 415].includes(reason.status)
      ) {
        setPending({ key: operation.key, title: null });
        return;
      }
      // 只有首次请求的明确拒绝才能结束该操作；未知结果始终保留原键。
      if (
        reason instanceof ApiError &&
        [400, 403, 413, 415].includes(reason.status)
      ) {
        try {
          sessionStorage.removeItem(storageKey);
          setPending(null);
        } catch {
          setError('浏览器无法更新操作标识，请检查会话存储后恢复。');
        }
      }
    },
  });

  function handleSubmit(values: { title: string }) {
    if (creation.isPending) return;
    setNotice('');
    setError('');
    const operation = {
      key: pending?.key ?? crypto.randomUUID(),
      title: pending?.title ?? values.title,
      recovering: pending !== null,
    };
    try {
      sessionStorage.setItem(storageKey, operation.key);
    } catch {
      setError('浏览器无法保存操作标识，尚未发出请求。请允许会话存储后重试。');
      return;
    }
    setPending(operation);
    creation.mutate(operation);
  }

  return (
    <main>
      <header className="masthead">
        <span>项目解读实验室 / 独立示例</span>
        <span>task-board · 1.0.0</span>
      </header>
      <section className="intro">
        <p className="eyebrow">从一次提交开始</p>
        <h1>
          任务簿<span>把想法写下来。</span>
        </h1>
        <p>
          输入标题，创建一条任务。每次成功提交都会保存，刷新页面后仍可查看。
        </p>
      </section>
      <div className="workspace">
        <section className="composer" aria-labelledby="create-heading">
          <p className="section-index">01 / 创建</p>
          <h2 id="create-heading">下一件想做的事</h2>
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            requiredMark={false}
          >
            <Form.Item
              name="title"
              label="任务标题"
              rules={[
                {
                  validator: (_, value: unknown) =>
                    typeof value === 'string' &&
                    !!value.trim() &&
                    Array.from(value.trim()).length <= 200
                      ? Promise.resolve()
                      : Promise.reject(
                          new Error(
                            '请输入 1–200 个字符的标题，不能只有空白。',
                          ),
                        ),
                },
              ]}
            >
              <Input.TextArea
                placeholder="例如：读懂创建任务的请求流程"
                autoSize={{ minRows: 3, maxRows: 6 }}
                disabled={creation.isPending || pending?.title != null}
                aria-describedby="title-help"
              />
            </Form.Item>
            <p id="title-help" className="hint">
              首尾空白会去除 · 最多 200 个字符
            </p>
            <Button
              type="primary"
              htmlType="submit"
              loading={creation.isPending}
              block
            >
              {pending ? '恢复这次提交' : '创建任务'}
            </Button>
          </Form>
          {pending && (
            <p role="status" className="hint">
              保留了本次操作标识。
              {pending.title === null
                ? '请重新输入上次的原标题，再恢复提交。'
                : '结果未确认时请使用恢复按钮。'}
            </p>
          )}
          {error && <Alert type="error" title={error} showIcon />}
          {notice && (
            <p role="status" className="saved">
              {notice}
            </p>
          )}
          <aside className="scope-note">
            内置教学示例
            <br />
            这里的任务保存在独立数据库中，不会修改导入项目。
          </aside>
        </section>
        <section className="records" aria-labelledby="records-heading">
          <div className="records-heading">
            <div>
              <p className="section-index">02 / 记录</p>
              <h2 id="records-heading">已保存的任务</h2>
            </div>
            <Button
              onClick={() => void tasks.refetch()}
              loading={tasks.isFetching}
            >
              刷新列表
            </Button>
          </div>
          {tasks.isPending && (
            <div role="status">
              <Spin /> 正在读取任务…
            </div>
          )}
          {tasks.isError && (
            <Alert
              type="error"
              title={
                notice
                  ? '任务已创建，但列表暂时未能刷新。'
                  : '暂时无法读取任务。'
              }
              description="请检查示例服务，再点击刷新列表。"
              showIcon
            />
          )}
          {tasks.data && (
            <>
              <p className="hint">共 {tasks.data.count} 条 · 最新创建优先</p>
              {tasks.data.results.length === 0 ? (
                <div className="empty">
                  <span>一页新的开始</span>
                  <p>还没有任务。在左侧写下第一条标题。</p>
                </div>
              ) : (
                <ol className="task-list">
                  {tasks.data.results.map((task) => (
                    <li key={task.id}>
                      <span className="task-dot" aria-hidden="true" />
                      <div>
                        <h3>{task.title}</h3>
                        <time dateTime={task.created_at}>
                          {new Date(task.created_at).toLocaleString('zh-CN')}
                        </time>
                        <code>{task.id}</code>
                      </div>
                      <span className="task-status">已保存</span>
                    </li>
                  ))}
                </ol>
              )}
              {tasks.data.count > 20 && (
                <Pagination
                  current={page}
                  total={tasks.data.count}
                  pageSize={20}
                  showSizeChanger={false}
                  onChange={setPage}
                />
              )}
            </>
          )}
        </section>
      </div>
      <footer>内置示例 · React → HTTP → DRF → PostgreSQL</footer>
    </main>
  );
}
