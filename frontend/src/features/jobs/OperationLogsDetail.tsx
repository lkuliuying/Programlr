import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tag } from 'antd';
import type {
  Job,
  OperationLog,
  RelatedOperationLog,
} from '../../shared/api/generated/schema';
import { requestJson } from '../../shared/api/client';
import * as v from '../../shared/api/validation';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { MainlineTask } from './MainlineTask';
import {
  operationLabels,
  outcomeLabels,
  parseOperationLog,
} from './OperationLogsApi';

const stageLabels: Record<string, string> = {
  queued: '等待执行',
  extracting: '解包并验证源码',
  publishing: '保存源码快照',
  parsing: '分析接口和关系',
  source_scanning: '识别源码与知识',
  generating: '生成讲解',
  cleaning_files: '清理内部文件',
  cleanup_pending: '等待继续清理',
  completed: '执行完成',
  failed: '执行失败',
  retired: '功能已退役',
};
const suggestions: Record<string, string> = {
  QUEUE_UNAVAILABLE: '检查本地任务服务，恢复后可显式重试。',
  RECEIVE_TIMEOUT: '接收未完成，请返回项目管理重新选择原源码并核对导入状态。',
  SOURCE_SCAN_FAILED:
    '查看根路由诊断和保留的源码；修复源项目后导入新快照，或显式重试。',
  ARCHIVE_LIMIT_EXCEEDED:
    '核对导入容量与有效文件数量，排除依赖及构建产物后重新导入。',
  RESOURCE_DELETED: '结果已永久清理；仍可查阅操作日志与任务摘要。',
  FEATURE_RETIRED: '此功能只保留历史结果，不能继续执行。',
};
const formatTime = (value: string) => (
  <time dateTime={value}>{new Date(value).toLocaleString('zh-CN')}</time>
);

function LinkedRecords({
  log,
  kind,
  active,
  onSelect,
}: {
  log: OperationLog;
  kind: 'related' | 'history';
  active: boolean;
  onSelect: (id: string) => void;
}) {
  const [page, setPage] = useState(1);
  const path = `/api/v1/operation-logs/${log.id}/${kind}/`;
  const result = useQuery({
    queryKey: ['operation-logs', kind, log.id, page],
    queryFn: ({ signal }) =>
      requestJson(
        path + `?page=${page}&page_size=5`,
        (raw) =>
          v.page(raw, path, (raw): RelatedOperationLog => ({
            ...parseOperationLog(raw),
            relation:
              kind === 'related'
                ? v.text(v.object(raw).relation, 20)
                : 'history',
          })),
        { signal },
      ),
    enabled: active,
  });
  const relationLabels: Record<string, string> = {
    parent: '前置任务',
    child: '后续任务',
    previous: '上次尝试',
    retry: '重试任务',
    history: '历史操作',
  };
  return (
    <section className="operation-linked">
      <h3>{kind === 'related' ? '关联任务' : '历史记录'}</h3>
      <Feedback error={result.error} retry={() => void result.refetch()} />
      {result.isPending && <p role="status">正在读取…</p>}
      {result.data?.results.length === 0 && (
        <p className="operation-muted">
          暂无{kind === 'related' ? '关联任务' : '更早记录'}。
        </p>
      )}
      <ul>
        {result.data?.results.map((item) => (
          <li key={item.id}>
            <button onClick={() => onSelect(item.id)}>
              <span>
                {relationLabels[item.relation] ?? '关联操作'} ·{' '}
                {item.display_id}
              </span>
              <strong>
                {operationLabels[item.operation] ?? item.operation}
              </strong>
              <small>
                {formatTime(item.started_at)} ·{' '}
                {outcomeLabels[item.result] ?? item.result}
              </small>
            </button>
          </li>
        ))}
      </ul>
      {result.data && (result.data.next || result.data.previous) && (
        <PageControls page={page} {...result.data} onPage={setPage} />
      )}
    </section>
  );
}

export function OperationLogsDetail({
  log,
  active,
  onSelect,
  onJob,
}: {
  log: OperationLog;
  active: boolean;
  onSelect: (id: string) => void;
  onJob: (job: Job) => void;
}) {
  const projectQuery = new URLSearchParams({
    section: 'import',
    project: log.project_id ?? '',
  });
  if (log.snapshot_id && !log.result_deleted) {
    projectQuery.set('section', 'source');
    projectQuery.set('snapshot', log.snapshot_id);
  }
  const duration = log.ended_at
    ? new Date(log.ended_at).getTime() - new Date(log.started_at).getTime()
    : null;
  const sourceLabels: Record<string, string> = {
    zip: 'ZIP 文件',
    folder: '本地目录',
  };
  return (
    <div className="operation-detail-content">
      <section className="operation-detail-summary">
        <h3>基本信息</h3>
        <dl className="operation-detail-fields">
          <div>
            <dt>日志 ID</dt>
            <dd className="operation-display-id">{log.display_id}</dd>
          </div>
          <div>
            <dt>操作类型</dt>
            <dd>{operationLabels[log.operation] ?? log.operation}</dd>
          </div>
          <div>
            <dt>操作对象</dt>
            <dd>{log.object_name || log.project_name || '目标未创建'}</dd>
          </div>
          <div>
            <dt>所属项目</dt>
            <dd>{log.project_name || '未关联项目'}</dd>
          </div>
          <div>
            <dt>执行结果</dt>
            <dd>
              <Tag
                color={
                  log.result === 'succeeded'
                    ? 'success'
                    : log.result === 'failed' || log.result === 'rejected'
                      ? 'error'
                      : 'processing'
                }
              >
                {outcomeLabels[log.result] ?? log.result}
              </Tag>
            </dd>
          </div>
          <div>
            <dt>开始时间</dt>
            <dd>{formatTime(log.started_at)}</dd>
          </div>
          <div>
            <dt>结束时间</dt>
            <dd>{log.ended_at ? formatTime(log.ended_at) : '未记录'}</dd>
          </div>
          <div>
            <dt>执行耗时</dt>
            <dd>
              {duration !== null && duration >= 0
                ? `${(duration / 1000).toFixed(1)} 秒`
                : '未记录'}
            </dd>
          </div>
          <div>
            <dt>来源类型</dt>
            <dd>
              {sourceLabels[log.source_kind] ?? (log.source_kind || '未记录')}
            </dd>
          </div>
          <div>
            <dt>请求标识</dt>
            <dd>{log.request_id || '未记录'}</dd>
          </div>
        </dl>
        {log.project_available && log.project_id && (
          <a className="operation-project-link" href={'/?' + projectQuery}>
            查看相关项目
          </a>
        )}
        {log.result_deleted && (
          <p>目标结果已删除；操作日志与任务摘要继续保留。</p>
        )}
      </section>
      <section className="operation-timeline">
        <h3>执行记录</h3>
        {!log.events.length && (
          <p className="operation-muted">此操作没有保存阶段事件。</p>
        )}
        <ol>
          {log.events.map((event, index) => {
            const stage = typeof event.stage === 'string' ? event.stage : '';
            const result = typeof event.result === 'string' ? event.result : '';
            const at =
              typeof event.at === 'string' &&
              Number.isFinite(Date.parse(event.at))
                ? event.at
                : null;
            return (
              <li key={index} data-state={result}>
                <strong>
                  {stageLabels[stage] ??
                    outcomeLabels[result] ??
                    (result === 'response' ? '请求已响应' : '阶段记录')}
                </strong>
                {at && <small>{formatTime(at)}</small>}
                {typeof event.error_code === 'string' && event.error_code && (
                  <code>{event.error_code}</code>
                )}
              </li>
            );
          })}
        </ol>
      </section>
      {(log.error_code || log.job?.error) && (
        <section className="operation-error">
          <h3>错误信息</h3>
          <p>{log.job?.error?.message ?? '本次操作未完成，请核对错误代码。'}</p>
          <code>{log.error_code || log.job?.error?.code}</code>
        </section>
      )}
      {log.job && (
        <MainlineTask
          key={log.job.id}
          id={log.job.id}
          active={active}
          retryAction={log.retry_action}
          retryReason={log.retry_reason}
          onJob={onJob}
        />
      )}
      <div className="operation-linked-grid">
        <LinkedRecords
          key={log.id + '-related'}
          log={log}
          kind="related"
          active={active}
          onSelect={onSelect}
        />
        <LinkedRecords
          key={log.id + '-history'}
          log={log}
          kind="history"
          active={active}
          onSelect={onSelect}
        />
      </div>
      {(log.result === 'failed' || log.result === 'rejected') && (
        <section className="operation-guidance">
          <h3>建议与解决方案</h3>
          <p>{suggestions[log.error_code] ?? log.retry_reason}</p>
          {log.retry_action === 'reconfirm_explanation' &&
            log.project_available && (
              <a
                href={
                  '/?' +
                  new URLSearchParams({
                    ...Object.fromEntries(projectQuery),
                    section: 'explanation',
                  })
                }
              >
                打开讲解工作区
              </a>
            )}
        </section>
      )}
    </div>
  );
}
