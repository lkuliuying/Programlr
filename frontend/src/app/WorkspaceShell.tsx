import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Icon, LabMark } from '../shared/components/Icon';
import type { IconName } from '../shared/components/Icon';
import type { WorkspaceSection } from './workspace-location';
import {
  initialRecentSections,
  navigation,
  navigationGroups,
  rememberSection,
  workspaceCategory,
} from './workspace-navigation';
import './shell-redesign.css';

export { navigation } from './workspace-navigation';
const categoryIcons = {
  workbench: 'workbench',
  project: 'graph',
  system: 'system',
} as const satisfies Record<string, IconName>;
function NavigationLinks({
  section,
  onSelect,
  sections,
  label = '功能导航',
}: {
  section: WorkspaceSection;
  onSelect: (section: WorkspaceSection) => void;
  sections: readonly WorkspaceSection[];
  label?: string;
}) {
  return (
    <nav aria-label={label}>
      <ul>
        {navigation
          .filter(([value]) => sections.includes(value))
          .map(([value, label]) => (
            <li key={value}>
              <button
                title={label}
                aria-current={
                  workspaceCategory(section) === workspaceCategory(value)
                    ? 'page'
                    : undefined
                }
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
  notificationControl,
}: {
  children: ReactNode;
  section: WorkspaceSection;
  onSection: (section: WorkspaceSection) => void;
  notificationControl?: ReactNode;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [recent, setRecent] = useState(() => initialRecentSections(section));
  const category = workspaceCategory(section);
  const remembered = rememberSection(recent, section);
  if (recent[category] !== remembered[category]) setRecent(remembered);
  const menuButton = useRef<HTMLButtonElement>(null);
  const menuDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    const onResize = () => {
      if (window.innerWidth >= 768) menuDialog.current?.close();
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [menuOpen]);
  return (
    <div
      className="workspace app-shell shell-redesign"
      data-category={category}
    >
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
        <div className="header-leading">
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
            <span className="brand-copy">
              <strong>项目解读实验室</strong>
              <small className="brand-subtitle">
                从源码出发，理解项目与知识
              </small>
            </span>
          </a>
        </div>
        <nav className="primary-navigation" aria-label="主分类导航">
          {navigationGroups.map((item) => (
            <button
              key={item.id}
              aria-current={category === item.id ? 'page' : undefined}
              onClick={() => onSection(recent[item.id])}
            >
              <Icon name={categoryIcons[item.id]} />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="header-trailing">
          <span className="local-status">
            <i />
            本地模式
          </span>
          {notificationControl ? (
            <div className="header-notifications">{notificationControl}</div>
          ) : (
            <button
              className="icon-button header-jobs"
              aria-label="查看操作日志"
              title="操作日志"
              onClick={() => onSection('jobs')}
            >
              <Icon name="jobs" />
            </button>
          )}
        </div>
      </header>
      <div className="shell-body">
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
          <div className="navigation-groups">
            {navigationGroups.map((item) => (
              <section key={item.id} aria-label={`${item.label}导航组`}>
                <h3>{item.label}</h3>
                <NavigationLinks
                  section={section}
                  sections={item.sections}
                  label={`${item.label}功能导航`}
                  onSelect={(value) => {
                    onSection(value);
                    menuDialog.current?.close();
                  }}
                />
              </section>
            ))}
          </div>
        </div>
      </dialog>
    </div>
  );
}
