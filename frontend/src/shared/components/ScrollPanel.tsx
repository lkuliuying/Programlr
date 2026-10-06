import { useLayoutEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import './ScrollPanel.css';

export function ScrollPanel({
  children,
  active = true,
  label,
  resetKey = '',
}: {
  children: ReactNode;
  active?: boolean;
  label: string;
  resetKey?: string;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (viewport.current) viewport.current.scrollTop = 0;
  }, [resetKey]);
  return (
    <div
      ref={viewport}
      className="scroll-panel"
      role="region"
      aria-label={label}
      hidden={!active}
      tabIndex={0}
      onClick={(event) => {
        const target = event.target;
        if (
          target instanceof Element &&
          viewport.current?.contains(target) &&
          target.closest('.workspace-pagination button:not(:disabled)')
        )
          viewport.current.scrollTop = 0;
      }}
    >
      <div className="scroll-panel-content">{children}</div>
    </div>
  );
}
