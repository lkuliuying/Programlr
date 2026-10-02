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
  ['system', '系统状态'],
  ['jobs', '任务历史'],
] as const;
function NavigationLinks({
  section,
  onSelect,
}: {
  section: WorkspaceSection;
  onSelect: (section: WorkspaceSection) => void;
}) {
  return (
    <nav aria-label="功能导航">
      <ul>
        {navigation.map(([value, label]) => (
          <li key={value}>
            <button
              title={label}
              aria-current={section === value ? 'page' : undefined}
              onClick={() => onSelect(value)}
            >
              <Icon name={value} />
              <span>{label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
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
  const menuDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === 'k' &&
        searchable &&
        !menuOpen
      ) {
        event.preventDefault();
        searchInput.current?.focus();
      }
    }
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [searchable, menuOpen]);
  useEffect(() => {
    if (!menuOpen) return;
    const onResize = () => {
      if (window.innerWidth >= 768) menuDialog.current?.close();
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [menuOpen]);
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
          aria-haspopup="dialog"
          aria-controls="workspace-navigation"
          aria-expanded={menuOpen}
          onClick={() => {
            menuDialog.current?.showModal();
            setMenuOpen(true);
            menuDialog.current
              ?.querySelector<HTMLButtonElement>('[aria-current="page"]')
              ?.focus();
          }}
        >
          <Icon name="menu" />
        </button>
        <a
          className="app-brand"
          href="/"
          aria-label="项目解读实验室首页"
          onClick={(event) => {
            if (
              event.ctrlKey ||
              event.metaKey ||
              event.altKey ||
              event.shiftKey
            )
              return;
            event.preventDefault();
            onSection('workbench');
          }}
        >
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
          title="任务历史"
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
        <aside className="app-sidebar">
          <NavigationLinks section={section} onSelect={onSection} />
        </aside>
        <main id="workspace-main" className="shell-main" tabIndex={-1}>
          {children}
        </main>
      </div>
      <dialog
        ref={menuDialog}
        id="workspace-navigation"
        className="navigation-dialog"
        aria-label="功能导航菜单"
        onKeyDown={(event) => {
          if (event.key !== 'Tab') return;
          const buttons =
            event.currentTarget.querySelectorAll<HTMLButtonElement>('button');
          const first = buttons[0],
            last = buttons[buttons.length - 1];
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last?.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first?.focus();
          }
        }}
        onCancel={(event) => {
          event.preventDefault();
          event.currentTarget.close();
        }}
        onClose={() => {
          setMenuOpen(false);
          if (window.innerWidth < 768) menuButton.current?.focus();
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) event.currentTarget.close();
        }}
      >
        <div className="navigation-dialog-content">
          <header>
            <h2>功能导航</h2>
            <button
              aria-label="关闭功能导航"
              onClick={() => menuDialog.current?.close()}
            >
              关闭
            </button>
          </header>
          <NavigationLinks
            section={section}
            onSelect={(value) => {
              onSection(value);
              menuDialog.current?.close();
            }}
          />
        </div>
      </dialog>
    </div>
  );
}
