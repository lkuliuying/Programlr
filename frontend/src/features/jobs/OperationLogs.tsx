import { useEffect, useId, useRef, useState } from 'react';
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { Button, ConfigProvider, Drawer, Pagination, Table, Tag } from 'antd';
import type { TableColumnsType } from 'antd';
import type { Job, OperationLog } from '../../shared/api/generated/schema';
import { ApiError, requestJson } from '../../shared/api/client';
import * as v from '../../shared/api/validation';
import { Feedback } from '../../shared/components/Feedback';
import { Icon } from '../../shared/components/Icon';
import { MainlineTask } from './MainlineTask';
import { OperationLogsDetail } from './OperationLogsDetail';
import {
  downloadOperationLogs,
  parseOperationLog,
  parseOperationStatistics,
} from './OperationLogsApi';
import {
  LogTimeFilter,
  LogValueFilter,
  emptyLogTimeRange,
} from './OperationLogFilters';
import type { LogTimeRange } from './OperationLogFilters';
import './OperationLogs.css';

function parseLog(raw: unknown): OperationLog {
  return parseOperationLog(raw);
}
const operations: Record<string, string> = {
  import: '源码导入',
  source_scan: '源码扫描',
  analysis: '接口分析',
  explanation: '模型讲解',
  delete: '永久删除',
  delete_project: '删除项目',
  delete_snapshot: '删除快照',
  retry: '任务重试',
  lab: '历史实验',
  snapshot_comparison: '历史对比',
  system_check: '历史检查',
};
const outcomes: Record<string, string> = {
  submitted: '已提交',
  accepted: '已接收',
  running: '处理中',
  succeeded: '成功',
  failed: '失败',
  rejected: '前置拒绝',
  replayed: '幂等重放',
};
export function OperationLogs({
  active = true,
  jobId,
  onJob,
}: {
  active?: boolean;
  jobId: string | null;
  onJob: (job: Job) => void;
}) {
  const [page, setPage] = useState(1),
    [pageSize, setPageSize] = useState(20),
    [operation, setOperation] = useState(''),
    [result, setResult] = useState(''),
    [searchDraft, setSearchDraft] = useState(''),
    [searchTerm, setSearchTerm] = useState(''),
    [composing, setComposing] = useState(false),
    [started, setStarted] = useState<LogTimeRange>(emptyLogTimeRange),
    [ended, setEnded] = useState<LogTimeRange>(emptyLogTimeRange),
    [selected, setSelected] = useState<string | null>(null),
    [view, setView] = useState('all'),
    [ordering, setOrdering] = useState('-started_at'),
    [exporting, setExporting] = useState(false),
    [exportError, setExportError] = useState<Error | null>(null),
    [exportStatus, setExportStatus] = useState(''),
    [pageNotice, setPageNotice] = useState('');
  const queryClient = useQueryClient();
  const detailTitleId = useId();
  const searchInput = useRef<HTMLInputElement>(null);
  const detailTrigger = useRef<HTMLElement | null>(null);
  const drawerPanel = useRef<HTMLDivElement>(null);
  const restoreDetailFocus = useRef(false);
  const focusFrame = useRef<number | null>(null);
  const exportController = useRef<AbortController | null>(null);
  const exportUrl = useRef<string | null>(null);
  const exportTimer = useRef<number | null>(null);
  useEffect(
    () => () => {
      exportController.current?.abort();
      if (focusFrame.current !== null)
        window.cancelAnimationFrame(focusFrame.current);
      if (exportTimer.current !== null)
        window.clearTimeout(exportTimer.current);
      if (exportUrl.current) URL.revokeObjectURL(exportUrl.current);
    },
    [],
  );
  useEffect(() => {
    if (!active) {
      restoreDetailFocus.current = false;
      if (focusFrame.current !== null) {
        window.cancelAnimationFrame(focusFrame.current);
        focusFrame.current = null;
      }
      exportController.current?.abort();
      void queryClient.cancelQueries({ queryKey: ['operation-logs'] });
    }
  }, [active, queryClient]);
  const searchPending = composing || searchDraft.trim() !== searchTerm;
  useEffect(() => {
    if (composing || searchDraft.trim() === searchTerm) return;
    const timer = window.setTimeout(() => {
      setSearchTerm(searchDraft.trim());
    }, 200);
    return () => window.clearTimeout(timer);
  }, [searchDraft, searchTerm, composing]);
  const cancelReads = () => {
    void queryClient.cancelQueries({ queryKey: ['operation-logs'] });
  };
  const changeSearch = (raw: string) => {
    const value = [...raw].slice(0, 200).join('');
    setSearchDraft(value);
    if (value.trim() !== searchTerm) {
      cancelReads();
      setPage(1);
      setPageNotice('');
      setSelected(null);
    }
    if (!value.trim()) setSearchTerm('');
  };
  const clearSearch = () => {
    cancelReads();
    setSearchDraft('');
    setSearchTerm('');
    setComposing(false);
    setPage(1);
    setPageNotice('');
    setSelected(null);
  };
  const tableViewport = useRef<HTMLDivElement>(null);
  const [horizontal, setHorizontal] = useState({ overflow: false, percent: 0 });
  useEffect(() => {
    const element = tableViewport.current;
    if (!element || !active) return;
    const measure = () => {
      const maximum = element.scrollWidth - element.clientWidth;
      const next = {
        overflow: maximum > 1,
        percent:
          maximum > 1 ? Math.round((element.scrollLeft / maximum) * 100) : 0,
      };
      setHorizontal((previous) =>
        previous.overflow === next.overflow && previous.percent === next.percent
          ? previous
          : next,
      );
    };
    const observer =
      typeof ResizeObserver === 'undefined'
        ? null
        : new ResizeObserver(measure);
    observer?.observe(element);
    element.addEventListener('scroll', measure, { passive: true });
    measure();
    return () => {
      observer?.disconnect();
      element.removeEventListener('scroll', measure);
    };
  }, [active]);
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (view !== 'all') query.set('view', view);
  if (ordering !== '-started_at') query.set('ordering', ordering);
  if (searchTerm) query.set('q', searchTerm);
  if (operation) query.set('operation', operation);
  if (result) query.set('result', result);
  if (started.after) query.set('started_after', started.after.toISOString());
  if (started.before) query.set('started_before', started.before.toISOString());
  if (ended.after) query.set('ended_after', ended.after.toISOString());
  if (ended.before) query.set('ended_before', ended.before.toISOString());
  const path = '/api/v1/operation-logs/';
  const logs = useQuery({
    queryKey: ['operation-logs', query.toString()],
    queryFn: async ({ signal }) => {
      try {
        return await requestJson(
          path + '?' + query,
          (raw) =>
            v.page(raw, path, parseLog, [
              'q',
              'operation',
              'result',
              'started_after',
              'started_before',
              'ended_after',
              'ended_before',
              'view',
              'ordering',
            ]),
          { signal },
        );
      } catch (error) {
        if (
          !signal.aborted &&
          page > 1 &&
          error instanceof ApiError &&
          error.code === 'PAGE_NOT_FOUND'
        ) {
          setPage((current) => (current === page ? 1 : current));
          setSelected(null);
          setPageNotice('记录范围已更新，已返回第一页。');
        }
        throw error;
      }
    },
    placeholderData: keepPreviousData,
    enabled: active && !searchPending,
    refetchInterval: active && !searchPending ? 3000 : false,
  });
  const statisticsQuery = new URLSearchParams(query);
  for (const name of ['page', 'page_size', 'view', 'result', 'ordering'])
    statisticsQuery.delete(name);
  const statistics = useQuery({
    queryKey: ['operation-logs', 'statistics', statisticsQuery.toString()],
    queryFn: ({ signal }) =>
      requestJson(
        path + 'statistics/?' + statisticsQuery,
        parseOperationStatistics,
        { signal },
      ),
    enabled: active && !searchPending,
    refetchInterval: active && !searchPending ? 3000 : false,
  });
  const detail = useQuery({
    queryKey: ['operation-logs', 'detail', selected],
    queryFn: ({ signal }) =>
      requestJson(path + selected + '/', parseLog, { signal }),
    enabled: active && !!selected,
    refetchInterval: active && !!selected ? 3000 : false,
    // 关闭过渡保留正文；切换记录时不把上一条详情作为占位内容。
    placeholderData: (previous) => (selected ? undefined : previous),
  });
  const rowsPending = searchPending || logs.isPlaceholderData || logs.isPending;
  const onFilter = <T,>(setter: (value: T) => void, value: T) => {
    setter(value);
    setPage(1);
    setPageNotice('');
    setSelected(null);
  };
  const formatTime = (value: string) => (
    <time dateTime={value}>{new Date(value).toLocaleString('zh-CN')}</time>
  );
  const closeDetail = () => {
    restoreDetailFocus.current = true;
    setSelected(null);
    void queryClient.cancelQueries({ queryKey: ['operation-logs', 'detail'] });
    if (focusFrame.current !== null)
      window.cancelAnimationFrame(focusFrame.current);
    // 开启动效尚未完成就关闭时，组件可能没有关闭回调，下一帧补上焦点恢复。
    focusFrame.current = window.requestAnimationFrame(() => {
      focusFrame.current = null;
      if (restoreDetailFocus.current) {
        const target = detailTrigger.current?.isConnected
          ? detailTrigger.current
          : searchInput.current;
        target?.focus({ preventScroll: true });
      }
    });
  };
  const openDetail = (id: string) => {
    restoreDetailFocus.current = false;
    if (focusFrame.current !== null) {
      window.cancelAnimationFrame(focusFrame.current);
      focusFrame.current = null;
    }
    setSelected(id);
    if (selected)
      drawerPanel.current
        ?.querySelector<HTMLButtonElement>('button[aria-label="关闭操作详情"]')
        ?.focus({ preventScroll: true });
  };
  const exportLogs = async () => {
    if (exportController.current) return;
    const controller = new AbortController();
    exportController.current = controller;
    setExportError(null);
    setExportStatus('');
    setExporting(true);
    try {
      const blob = await downloadOperationLogs(query, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      if (exportUrl.current) URL.revokeObjectURL(exportUrl.current);
      exportUrl.current = url;
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'operation-logs.csv';
      anchor.click();
      setExportStatus('日志 CSV 已生成并开始下载。');
      if (exportTimer.current !== null)
        window.clearTimeout(exportTimer.current);
      exportTimer.current = window.setTimeout(() => {
        URL.revokeObjectURL(url);
        if (exportUrl.current === url) exportUrl.current = null;
        exportTimer.current = null;
      }, 1000);
    } catch (error) {
      if (controller.signal.aborted) setExportStatus('已取消日志导出。');
      else
        setExportError(
          error instanceof Error ? error : new Error('日志导出失败。'),
        );
    } finally {
      if (exportController.current === controller) {
        exportController.current = null;
        setExporting(false);
      }
    }
  };
  const cancelExport = () => {
    exportController.current?.abort();
    setExportStatus('已取消日志导出。');
  };
  const columns: TableColumnsType<OperationLog> = [
    {
      key: 'display_id',
      title: 'ID',
      width: 86,
      align: 'center',
      render: (_, item) => (
        <span className="operation-display-id">{item.display_id}</span>
      ),
    },
    {
      key: 'operation',
      width: 146,
      title: (
        <LogValueFilter
          key={`operation-${active}`}
          label="操作类型"
          value={operation}
          options={operations}
          onChange={(value) => onFilter(setOperation, value)}
        />
      ),
      render: (_, item) => operations[item.operation] ?? item.operation,
    },
    {
      key: 'object',
      title: '操作对象 / 项目',
      width: 230,
      render: (_, item) => (
        <div className="operation-object">
          <strong title={item.object_name || item.project_name || '目标未创建'}>
            {item.object_name || item.project_name || '目标未创建'}
          </strong>
          {item.project_name && item.project_name !== item.object_name && (
            <small title={item.project_name}>{item.project_name}</small>
          )}
          {item.result_deleted && <small>结果已删除</small>}
        </div>
      ),
    },
    {
      key: 'result',
      width: 170,
      align: 'center',
      title: (
        <LogValueFilter
          key={`result-${active}`}
          label="结果"
          value={result}
          options={outcomes}
          onChange={(value) => {
            setView('all');
            onFilter(setResult, value);
          }}
        />
      ),
      render: (_, item) => (
        <div className="operation-result">
          <Tag
            color={
              item.result === 'succeeded'
                ? 'success'
                : ['failed', 'rejected'].includes(item.result)
                  ? 'error'
                  : 'default'
            }
          >
            {outcomes[item.result] ?? item.result}
          </Tag>
          {item.error_code && (
            <code title={item.error_code}>{item.error_code}</code>
          )}
        </div>
      ),
    },
    {
      key: 'started_at',
      width: 190,
      align: 'center',
      title: (
        <LogTimeFilter
          key={`started-${active}`}
          label="开始时间"
          value={started}
          onChange={(value) => onFilter(setStarted, value)}
        />
      ),
      render: (_, item) => formatTime(item.started_at),
    },
    {
      key: 'ended_at',
      width: 190,
      align: 'center',
      title: (
        <LogTimeFilter
          key={`ended-${active}`}
          label="结束时间"
          value={ended}
          onChange={(value) => onFilter(setEnded, value)}
        />
      ),
      render: (_, item) => (
        <div className="operation-time">
          {item.ended_at ? (
            formatTime(item.ended_at)
          ) : (
            <span className="operation-muted">
              {['submitted', 'accepted', 'running'].includes(item.result)
                ? '尚未结束'
                : '未记录'}
            </span>
          )}
          {item.ended_at &&
            item.events.some((event) => event.legacy === true) && (
              <small>历史摘要</small>
            )}
        </div>
      ),
    },
    {
      key: 'detail',
      title: '详情',
      width: 90,
      align: 'center',
      render: (_, item) => (
        <Button
          size="small"
          type="link"
          aria-label={`查看${operations[item.operation] ?? item.operation}日志详情`}
          aria-expanded={selected === item.id}
          disabled={rowsPending || !!logs.error}
          onClick={(event) => {
            detailTrigger.current = event.currentTarget;
            if (selected === item.id) closeDetail();
            else openDetail(item.id);
          }}
        >
          {selected === item.id ? '收起' : '查看'}
        </Button>
      ),
    },
  ];
  const stats = statistics.data;
  const countText = (value: number | undefined) =>
    value === undefined ? '—' : value.toLocaleString('zh-CN');
  const metrics = [
    {
      label: '操作总数',
      value: countText(stats?.count),
      icon: 'file' as const,
      tone: 'blue',
      note: '当前搜索与时间范围',
    },
    {
      label: '失败记录',
      value: countText(stats?.failed_count),
      icon: 'close' as const,
      tone: 'red',
      note: '不含前置拒绝与幂等重放',
    },
    {
      label: '进行中记录',
      value: countText(stats?.active_count),
      icon: 'clock' as const,
      tone: 'blue',
      note: '已提交、已接收与处理中',
    },
    {
      label: '近 7 天成功率',
      value:
        stats?.recent_success_rate === null
          ? '暂无数据'
          : stats?.recent_success_rate === undefined
            ? '—'
            : stats.recent_success_rate + '%',
      icon: 'jobs' as const,
      tone: 'green',
      note:
        stats?.success_rate_change_pp === null ||
        stats?.success_rate_change_pp === undefined
          ? '暂无可比较的上一周期'
          : '较前 7 天 ' +
            (stats.success_rate_change_pp >= 0 ? '+' : '') +
            stats.success_rate_change_pp +
            ' 个百分点',
    },
  ];
  return (
    <section className="operation-logs">
      <div className="operation-main" data-has-job={!!jobId}>
        <nav className="operation-breadcrumb" aria-label="面包屑">
          <span>项目解读实验室</span>
          <span aria-hidden="true">/</span>
          <span aria-current="page">操作日志</span>
        </nav>
        <header className="operation-page-heading">
          <span className="operation-title-marker" aria-hidden="true" />
          <h1>操作日志</h1>
          <p>查看操作结果、排查失败原因、访问必要历史结果。</p>
        </header>
        <div className="operation-metrics" aria-label="操作日志统计">
          {metrics.map((metric, index) => (
            <article
              className="operation-metric"
              key={metric.label}
              data-tone={metric.tone}
            >
              <span className="operation-metric-icon">
                <Icon name={metric.icon} />
              </span>
              <div>
                <strong>{metric.value}</strong>
                <span>{metric.label}</span>
                <small>{metric.note}</small>
              </div>
              {stats && index < 2 && (
                <span
                  className="operation-mini-bars"
                  role="img"
                  aria-label={
                    index === 0
                      ? '近7天每日新增操作趋势'
                      : '近7天每日失败结束趋势'
                  }
                >
                  {stats.trend.map((bucket) => {
                    const field = index === 0 ? 'count' : 'failed_count';
                    const max = Math.max(
                      1,
                      ...stats.trend.map((item) => item[field]),
                    );
                    return (
                      <i
                        key={bucket.start}
                        style={{ height: 3 + (bucket[field] / max) * 27 }}
                        title={
                          new Date(bucket.start).toLocaleDateString('zh-CN') +
                          '：' +
                          bucket[field]
                        }
                      />
                    );
                  })}
                </span>
              )}
            </article>
          ))}
        </div>
        <p className="operation-statistics-note">
          统计覆盖完整查询；成功率按已结束的成功与失败记录计算，不含前置拒绝、重放和缺失结束时间的记录。
        </p>
        <Feedback
          error={statistics.error}
          retry={() => void statistics.refetch()}
        />
        {jobId && (
          <MainlineTask key={jobId} id={jobId} active={active} onJob={onJob} />
        )}
        <section className="surface operation-records">
          <div className="operation-toolbar">
            <label className="operation-search">
              <Icon name="search" />
              <input
                ref={searchInput}
                aria-label="搜索操作日志"
                value={searchDraft}
                maxLength={400}
                placeholder="搜索操作类型、操作对象、项目…"
                onChange={(event) => changeSearch(event.target.value)}
                onCompositionStart={() => {
                  setComposing(true);
                  cancelReads();
                }}
                onCompositionEnd={(event) => {
                  setComposing(false);
                  changeSearch(event.currentTarget.value);
                }}
              />
              {searchDraft && (
                <button
                  type="button"
                  className="operation-search-clear"
                  aria-label="清除日志搜索"
                  onClick={() => {
                    clearSearch();
                    searchInput.current?.focus();
                  }}
                >
                  ×
                </button>
              )}
            </label>
            <div className="operation-toolbar-actions">
              <label className="operation-sort">
                排序
                <select
                  aria-label="日志排序"
                  value={ordering}
                  onChange={(event) =>
                    onFilter(setOrdering, event.target.value)
                  }
                >
                  <option value="-started_at">开始时间：最新</option>
                  <option value="started_at">开始时间：最早</option>
                  <option value="-ended_at">结束时间：最新</option>
                  <option value="ended_at">结束时间：最早</option>
                </select>
              </label>
              <Button
                size="small"
                onClick={() => {
                  clearSearch();
                  setOperation('');
                  setResult('');
                  setView('all');
                  setOrdering('-started_at');
                  setStarted(emptyLogTimeRange);
                  setEnded(emptyLogTimeRange);
                  setPage(1);
                  setSelected(null);
                }}
              >
                清除全部筛选
              </Button>
              <Button
                size="small"
                onClick={() => {
                  if (exporting) cancelExport();
                  else void exportLogs();
                }}
                disabled={!exporting && searchPending}
              >
                {exporting ? '取消导出' : '导出日志'}
              </Button>
            </div>
          </div>
          <div className="operation-views" aria-label="日志快捷视图">
            {[
              ['all', '全部', stats?.count],
              ['failed', '失败', stats?.failed_count],
              ['active', '进行中', stats?.active_count],
              ['retryable', '可重试', stats?.retryable_count],
            ].map(([key, label, count]) => (
              <Button
                size="small"
                key={String(key)}
                type={view === key && !result ? 'primary' : 'default'}
                aria-pressed={view === key && !result}
                onClick={() => {
                  setResult('');
                  onFilter(setView, String(key));
                }}
              >
                {label} (
                {typeof count === 'number'
                  ? count.toLocaleString('zh-CN')
                  : '—'}
                )
              </Button>
            ))}
          </div>
          <Feedback error={logs.error} retry={() => void logs.refetch()} />
          <Feedback error={exportError} />
          <div
            className="operation-table-navigation"
            hidden={!horizontal.overflow}
          >
            <label>
              横向浏览
              <input
                aria-label="操作日志横向位置"
                type="range"
                min="0"
                max="100"
                value={horizontal.percent}
                onChange={(event) => {
                  const percent = Number(event.target.value);
                  const element = tableViewport.current;
                  if (element)
                    element.scrollLeft =
                      ((element.scrollWidth - element.clientWidth) * percent) /
                      100;
                  setHorizontal((previous) => ({ ...previous, percent }));
                }}
              />
            </label>
          </div>
          <div
            className="operation-table-shell"
            aria-busy={rowsPending || logs.isFetching}
          >
            <div
              ref={tableViewport}
              className="operation-table"
              role="region"
              aria-label="操作日志表格区域"
              tabIndex={0}
            >
              <Table<OperationLog>
                aria-label="操作日志表格"
                size="small"
                bordered
                tableLayout="fixed"
                pagination={false}
                rowKey="id"
                columns={columns}
                dataSource={logs.data?.results ?? []}
                loading={false}
                rowClassName={(item) =>
                  selected === item.id ? 'operation-selected' : ''
                }
                onRow={(item) => ({ 'aria-selected': selected === item.id })}
                locale={{
                  emptyText: logs.error
                    ? '日志读取失败，请重试。'
                    : rowsPending
                      ? '正在读取操作日志…'
                      : '当前条件没有操作记录。',
                }}
              />
            </div>
            {rowsPending && !logs.error && (
              <div className="operation-table-updating" aria-hidden="true">
                正在更新日志…
              </div>
            )}
          </div>
          <footer className="operation-record-footer">
            <p className="operation-total" role="status" aria-live="polite">
              {rowsPending
                ? '正在更新日志…'
                : logs.data
                  ? `共 ${logs.data.count} 条操作记录`
                  : '尚未读取操作记录'}
              {exportStatus && (
                <span className="operation-export-status">{exportStatus}</span>
              )}
              {pageNotice && <span>{pageNotice}</span>}
            </p>
            <Pagination
              key={String(active)}
              aria-label="操作日志分页"
              current={page}
              pageSize={pageSize}
              total={logs.data?.count ?? 0}
              pageSizeOptions={[10, 20, 50, 100]}
              showSizeChanger={{
                'aria-label': '每页日志数量',
                showSearch: false,
              }}
              showLessItems
              size="small"
              locale={{
                items_per_page: '条/页',
                prev_page: '上一页',
                next_page: '下一页',
              }}
              onChange={(nextPage, nextSize) => {
                setPage(nextSize === pageSize ? nextPage : 1);
                setPageSize(nextSize);
                setPageNotice('');
                setSelected(null);
              }}
            />
            <p className="operation-retention-note">
              即使项目被删除，相关操作日志与必要任务摘要仍会保留。
            </p>
          </footer>
        </section>
      </div>
      <ConfigProvider theme={{ token: { motionDurationSlow: '0.24s' } }}>
        <Drawer
          rootClassName="operation-log-drawer"
          title={<span id={detailTitleId}>操作详情</span>}
          aria-label="操作详情"
          aria-labelledby={detailTitleId}
          size={600}
          panelRef={drawerPanel}
          open={active && !!selected}
          destroyOnHidden
          closable={{ placement: 'end', 'aria-label': '关闭操作详情' }}
          focusable={{ trap: true, focusTriggerAfterClose: false }}
          onClose={closeDetail}
          afterOpenChange={(open) => {
            if (open && active && selected) {
              drawerPanel.current
                ?.querySelector<HTMLButtonElement>(
                  'button[aria-label="关闭操作详情"]',
                )
                ?.focus({ preventScroll: true });
            }
            if (!open && restoreDetailFocus.current) {
              restoreDetailFocus.current = false;
              if (active && !selected) {
                const target = detailTrigger.current?.isConnected
                  ? detailTrigger.current
                  : searchInput.current;
                target?.focus({ preventScroll: true });
              }
            }
          }}
        >
          <Feedback error={detail.error} retry={() => void detail.refetch()} />
          {selected && detail.isPending && (
            <div className="operation-detail-placeholder">
              <p role="status">正在读取操作详情…</p>
            </div>
          )}
          {detail.data ? (
            <OperationLogsDetail
              key={detail.data.id}
              log={detail.data}
              active={active}
              onSelect={openDetail}
              onJob={onJob}
            />
          ) : null}
        </Drawer>
      </ConfigProvider>
    </section>
  );
}
