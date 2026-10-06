import type { ReactNode } from 'react';

export function PageHeading({
  title,
  description,
  icon,
  hidden = false,
}: {
  title: string;
  description: string;
  icon?: ReactNode;
  hidden?: boolean;
}) {
  return (
    <header className={hidden ? 'sr-only' : 'module-heading'}>
      {icon}
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </header>
  );
}

export function ContentState({
  children,
  kind = 'empty',
  action,
}: {
  children: ReactNode;
  kind?: 'empty' | 'loading' | 'error';
  action?: ReactNode;
}) {
  return (
    <div
      className={`content-state content-state-${kind}`}
      role={
        kind === 'error' ? 'alert' : kind === 'loading' ? 'status' : undefined
      }
    >
      <div>{children}</div>
      {action && <div className="content-state-action">{action}</div>}
    </div>
  );
}
