import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Icon, LabMark } from '../shared/components/Icon';
import { useTheme } from './ThemeProvider';
import type { WorkspaceSection } from './workspace-location';

export const navigation = [
  ['workbench', '工作台'],
  ['import', '项目导入'],
  ['source', '源码阅读'],
  ['api', 'API 分析'],
  ['graph', '静态关系图'],
  ['comparison', '快照与对比'],
  ['impact', '候选影响'],
  ['learning', '知识与学习'],
  ['labs', '练习与实验'],
  ['explanation', '模型讲解'],
  ['jobs', '系统与任务'],
] as const;
export function WorkspaceShell({
  children,
  section,
  onSection,
  search = '',
  onSearch,
  searchable = false,
}: {
  children: ReactNode;
  section: WorkspaceSection;
  onSection: (section: WorkspaceSection) => void;
  search?: string;
  onSearch?: (value: string) => void;
  searchable?: boolean;
}) {
  const { mode, setMode } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const searchInput = useRef<HTMLInputElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === 'k' &&
        searchable
      ) {
        event.preventDefault();
        searchInput.current?.focus();
      }
      if (event.key === 'Escape' && menuOpen) {
        setMenuOpen(false);
        menuButton.current?.focus();
      }
    }
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [searchable, menuOpen]);
  return (
    <div className="workspace app-shell">
      <a className="skip-link" href="#workspace-main">
        跳到工作区内容
      </a>
      <header className="app-header">
        <button
          ref={menuButton}
          className="icon-button mobile-menu"
          aria-label="功能导航"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <Icon name="menu" />
        </button>
        <a className="app-brand" href="/" aria-label="项目解读实验室首页">
          <LabMark />
          <strong>项目解读实验室</strong>
        </a>
        <span className="brand-subtitle">DRF + React 本地学习工作台</span>
        <span className="header-purpose">读懂代码 · 理解架构 · 动手实验</span>
        <label className="header-search">
          <Icon name="search" />
          <span className="sr-only">搜索当前快照文件</span>
          <input
            ref={searchInput}
            aria-label="搜索当前快照文件"
            placeholder="搜索当前快照文件…"
            disabled={!searchable}
            value={search}
            onChange={(event) => {
              onSearch?.(event.target.value);
              if (event.target.value) onSection('source');
            }}
            onKeyDown={(event) => {
              if (event.key === 'Escape') onSearch?.('');
            }}
          />
          <kbd>Ctrl K</kbd>
        </label>
        <span className="local-status">
          <i />
          本地 · 只读分析
        </span>
        <button
          className="icon-button header-jobs"
          aria-label="查看任务历史"
          title="系统与任务"
          onClick={() => onSection('jobs')}
        >
          <Icon name="jobs" />
        </button>
        <button
          className="theme-switch"
          aria-label={mode === 'dark' ? '切换为浅色模式' : '切换为深色模式'}
          onClick={() => setMode(mode === 'dark' ? 'light' : 'dark')}
        >
          <Icon name={mode === 'dark' ? 'sun' : 'moon'} />
          <span>{mode === 'dark' ? '浅色' : '深色'}</span>
        </button>
        <span className="learner">
          <span className="learner-avatar">学</span>
          <span>
            学习者<small>Code · Understand · Grow</small>
          </span>
        </span>
      </header>
      <div className="shell-body">
        <aside className="app-sidebar" data-open={menuOpen}>
          <nav aria-label="功能导航">
            <ul>
              {navigation.map(([value, label]) => (
                <li key={value}>
                  <button
                    title={label}
                    aria-current={section === value ? 'page' : undefined}
                    onClick={() => {
                      onSection(value);
                      setMenuOpen(false);
                      if (menuOpen) menuButton.current?.focus();
                    }}
                  >
                    <Icon name={value} />
                    <span>{label}</span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </aside>
        <main id="workspace-main" className="shell-main" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
