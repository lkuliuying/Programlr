import { useId } from 'react';
import type { ReactNode } from 'react';
import type {
  Analysis,
  Project,
  Snapshot,
} from '../shared/api/generated/schema';
import { Icon } from '../shared/components/Icon';
import type { IconName } from '../shared/components/Icon';
import type { WorkspaceSection } from './workspace-location';
import './WorkbenchDashboard.css';

export type DashboardMetric = {
  key: string;
  label: string;
  value: number | null;
  description: string;
  icon?: IconName;
};

export type WorkbenchDashboardProps = {
  project?: Project | null;
  snapshot?: Snapshot | null;
  analysis?: Analysis | null;
  loading?: boolean;
  unavailable?: boolean;
  recentContent: ReactNode;
  learningContent: ReactNode;
  metrics: readonly DashboardMetric[];
  onSection: (section: WorkspaceSection) => void;
  onCreateProject: () => void;
};

function ProjectLayers() {
  const id = useId();
  return (
    <svg
      className="dashboard-project-layers"
      viewBox="0 0 420 290"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id={`${id}-panel`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#24477c" />
          <stop offset="1" stopColor="#0d1d40" />
        </linearGradient>
        <linearGradient id={`${id}-edge`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#37a5ff" />
          <stop offset="1" stopColor="#87d9ff" />
        </linearGradient>
      </defs>
      <ellipse
        cx="220"
        cy="245"
        rx="172"
        ry="28"
        fill="#051025"
        opacity=".35"
      />
      <g fill="none" stroke="#35609a" strokeWidth="1" opacity=".5">
        <path d="M30 206 208 274 400 185M42 222 219 288M98 164 288 237M164 139 354 212" />
      </g>
      <g transform="translate(56 154) rotate(-13)">
        <rect
          width="210"
          height="106"
          rx="12"
          fill="#0a1a35"
          stroke="#295183"
        />
        <path
          d="M18 26h125M18 44h160M18 62h104M18 80h145"
          stroke="#4872a5"
          strokeWidth="4"
        />
        <path d="M18 26h48M18 62h34" stroke="#70c7ff" strokeWidth="4" />
      </g>
      <g transform="translate(137 73) rotate(8)">
        <rect
          width="218"
          height="145"
          rx="13"
          fill={`url(#${id}-panel)`}
          stroke="#5a8bcb"
        />
        <path d="M0 30h218" stroke="#4873aa" />
        <circle cx="17" cy="15" r="3" fill="#77b7f8" />
        <circle cx="29" cy="15" r="3" fill="#497ba9" />
        <circle cx="41" cy="15" r="3" fill="#497ba9" />
        <g
          transform="translate(110 83)"
          stroke="#66d5ff"
          fill="none"
          strokeWidth="2.8"
        >
          <ellipse rx="47" ry="17" />
          <ellipse rx="47" ry="17" transform="rotate(60)" />
          <ellipse rx="47" ry="17" transform="rotate(120)" />
          <circle r="6" fill="#66d5ff" stroke="none" />
        </g>
        <text x="88" y="132" fill="#d9eeff" fontSize="13">
          React
        </text>
      </g>
      <g transform="translate(50 54) rotate(-8)">
        <rect width="133" height="92" rx="12" fill="#132f54" stroke="#6395cc" />
        <rect x="13" y="14" width="107" height="4" rx="2" fill="#4a82b8" />
        <text x="29" y="55" fill="#d9eeff" fontSize="29" fontWeight="700">
          DRF
        </text>
        <path d="M29 70h76" stroke="#75b9f8" strokeWidth="3" />
      </g>
      <g fill="#16345a" stroke={`url(#${id}-edge)`} strokeWidth="1.5">
        <path d="m324 224 21-12 21 12v25l-21 12-21-12Z" />
        <path d="m324 224 21 12 21-12M345 236v25" fill="none" />
        <path d="m71 35 14-8 14 8v16l-14 8-14-8Z" />
      </g>
      <path
        d="M289 47h51v27M32 135v32h21M357 126h25v37"
        fill="none"
        stroke="#65adf5"
        strokeWidth="2"
        strokeDasharray="4 6"
      />
      <circle cx="289" cy="47" r="4" fill="#82c8ff" />
      <circle cx="382" cy="163" r="4" fill="#82c8ff" />
    </svg>
  );
}

const shortcuts = [
  {
    section: 'import',
    icon: 'folder',
    title: '准备项目',
    detail: '创建或打开一个学习项目',
  },
  {
    section: 'import',
    icon: 'import',
    title: '导入源码',
    detail: '选择源码 ZIP，保存只读快照',
  },
  {
    section: 'api',
    icon: 'search',
    title: '查看分析',
    detail: '从接口出发，核对静态关系',
  },
  {
    section: 'learning',
    icon: 'learning',
    title: '开始学习',
    detail: '按课程阅读，连接代码与原理',
  },
] as const;

export function WorkbenchDashboard({
  project,
  snapshot,
  analysis,
  loading = false,
  unavailable = false,
  recentContent,
  learningContent,
  metrics,
  onSection,
  onCreateProject,
}: WorkbenchDashboardProps) {
  const projectReady = !!project && !loading && !unavailable;
  const snapshotReady = projectReady && snapshot?.project_id === project.id;
  // 准备状态必须来自已加载且绑定当前快照的分析，不能由 URL 中的 ID 推断。
  const analysisReady = snapshotReady && analysis?.snapshot_id === snapshot?.id;
  const step = !projectReady ? 0 : !snapshotReady ? 1 : !analysisReady ? 2 : 3;
  const primary = [
    { label: '创建或打开项目', section: 'import' },
    { label: '导入源码 ZIP', section: 'import' },
    { label: '选择根路由并分析', section: 'api' },
    { label: '继续阅读 API', section: 'api' },
  ] as const;
  const preparation = [
    {
      label: '打开学习项目',
      detail: '创建项目，或继续已有项目',
      ready: projectReady,
      enabled: true,
      section: 'import',
    },
    {
      label: '导入源码快照',
      detail: '保存这一次的源码版本',
      ready: snapshotReady,
      enabled: projectReady,
      section: 'import',
    },
    {
      label: '选择静态分析',
      detail: '显式选择根路由，读取接口与关系',
      ready: analysisReady,
      enabled: snapshotReady,
      section: 'api',
    },
  ] as const;
  return (
    <div className="workbench-dashboard">
      <div className="dashboard-top">
        <section className="dashboard-hero" aria-label="项目探索入口">
          <div className="dashboard-hero-copy">
            <span className="dashboard-eyebrow">DRF + React 学习工作台</span>
            <h2>
              从源码出发，
              <br />
              读懂你的项目
            </h2>
            <p>串起接口、源码与知识，在自己的项目里理解每一条调用链。</p>
            {loading ? (
              <p role="status">正在读取当前项目和分析…</p>
            ) : unavailable ? (
              <p role="alert">当前项目暂不可用，请重新选择项目与快照。</p>
            ) : (
              <p className="dashboard-context">
                {projectReady
                  ? `当前项目：${project.name}`
                  : '先打开一个项目，开始你的第一次源码探索。'}
              </p>
            )}
            <div className="dashboard-hero-actions" data-page-keep>
              <button
                type="button"
                className="primary-button"
                disabled={loading}
                onClick={() =>
                  onSection(unavailable ? 'import' : primary[step]!.section)
                }
              >
                {unavailable ? '重新选择项目' : primary[step]!.label}
                <Icon name="arrow" />
              </button>
              <button
                type="button"
                className="dashboard-secondary"
                onClick={() => onSection('learning')}
              >
                浏览知识卡片
              </button>
            </div>
          </div>
          <div className="dashboard-hero-visual">
            <ProjectLayers />
          </div>
        </section>
        <section
          className="dashboard-preparation dashboard-panel"
          aria-label="项目准备步骤"
        >
          <div className="dashboard-panel-heading">
            <Icon name="workbench" />
            <h2>项目准备</h2>
          </div>
          <ol>
            {preparation.map((item, index) => (
              <li
                key={item.label}
                data-state={
                  item.ready ? 'ready' : index === step ? 'current' : 'waiting'
                }
              >
                <span className="dashboard-step-number" aria-hidden="true">
                  {item.ready ? '✓' : index + 1}
                </span>
                <div>
                  <button
                    type="button"
                    disabled={!item.enabled || loading}
                    onClick={() => onSection(item.section)}
                  >
                    {item.label}
                  </button>
                  <p>{item.detail}</p>
                </div>
                <small>
                  {item.ready
                    ? '已选择'
                    : index === step
                      ? '当前步骤'
                      : '待准备'}
                </small>
              </li>
            ))}
          </ol>
          <p className="dashboard-boundary">
            导入源码只读分析；分析与实验均需显式操作。
          </p>
        </section>
      </div>
      <section className="dashboard-quick" aria-label="快捷入口">
        {shortcuts.map((item) => (
          <button
            type="button"
            key={item.title}
            className="dashboard-quick-card"
            onClick={() => onSection(item.section)}
          >
            <span className="dashboard-quick-icon">
              <Icon name={item.icon} />
            </span>
            <span>
              <strong>{item.title}</strong>
              <small>{item.detail}</small>
            </span>
            <Icon name="arrow" />
          </button>
        ))}
      </section>
      <div className="dashboard-lower">
        <section
          className="dashboard-panel dashboard-recent"
          aria-label="最近项目"
        >
          <div className="dashboard-panel-heading">
            <Icon name="folder" />
            <h2>最近创建的项目</h2>
            <button
              type="button"
              className="dashboard-panel-link"
              onClick={() => onSection('import')}
            >
              全部项目 <Icon name="arrow" />
            </button>
          </div>
          {recentContent}
          <button
            type="button"
            className="dashboard-create"
            onClick={() => onCreateProject()}
          >
            <span aria-hidden="true">＋</span>创建新项目
          </button>
        </section>
        <section
          className="dashboard-panel dashboard-learning"
          aria-label="推荐学习"
        >
          <div className="dashboard-panel-heading">
            <Icon name="learning" />
            <h2>推荐学习</h2>
          </div>
          {learningContent}
        </section>
        <section
          className="dashboard-panel dashboard-overview"
          aria-label="数据概览"
        >
          <div className="dashboard-panel-heading">
            <Icon name="cube" />
            <h2>数据概览</h2>
          </div>
          <dl className="dashboard-metrics">
            {metrics.slice(0, 4).map((metric) => (
              <div key={metric.key} data-page-keep>
                <dt>
                  {metric.icon && <Icon name={metric.icon} />}
                  {metric.label}
                </dt>
                <dd className="dashboard-metric-value">
                  {metric.value !== null &&
                  Number.isSafeInteger(metric.value) &&
                  metric.value >= 0
                    ? metric.value.toLocaleString('zh-CN')
                    : '未读取'}
                </dd>
                <dd className="dashboard-metric-description">
                  {metric.description}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </div>
  );
}
