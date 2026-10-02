import { useId, useLayoutEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { contentPageAt, paginateContent } from './content-pagination';
import type { ContentRange } from './content-pagination';
import './ContentPager.css';

const atoms =
  'button, input, select, textarea, summary, label, fieldset, p, pre, li, article, h1, h2, h3, h4, tr, [data-page-keep]';
function readRanges(content: HTMLElement, height: number): ContentRange[] {
  const origin = content.getBoundingClientRect().top;
  const ranges: ContentRange[] = [];
  const add = (rect: DOMRect) => {
    if (rect.width > 0 && rect.height > 0 && rect.height <= height)
      ranges.push({
        top: Math.round(rect.top - origin),
        bottom: Math.round(rect.bottom - origin),
      });
  };
  content.querySelectorAll<HTMLElement>(atoms).forEach((element) => {
    add(element.getBoundingClientRect());
  });
  const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (
      !node.textContent?.trim() ||
      node.parentElement?.closest('.sr-only, svg, [hidden]')
    )
      continue;
    range.selectNodeContents(node);
    for (const rect of range.getClientRects()) add(rect);
  }
  return ranges;
}

export function ContentPager({
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
  const id = useId();
  const viewport = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const [layout, setLayout] = useState({
    pages: [{ top: 0, bottom: 0 }],
    height: 0,
    page: 0,
    resetKey,
  });
  if (layout.resetKey !== resetKey) setLayout({ ...layout, page: 0, resetKey });
  const page = Math.min(layout.page, layout.pages.length - 1);
  const current = layout.pages[page]!;
  const start = current.top;
  const count = layout.pages.length;

  useLayoutEffect(() => {
    if (!active || !viewport.current || !content.current) return;
    const frame = viewport.current,
      body = content.current;
    let pending = 0;
    const measure = () => {
      const height = Math.floor(frame.clientHeight);
      if (!height) return;
      const pages = paginateContent(
        height,
        body.scrollHeight,
        readRanges(body, height),
      );
      setLayout((previous) => {
        const position = previous.pages[previous.page]?.top ?? 0;
        return {
          height,
          pages,
          page: contentPageAt(pages, position),
          resetKey: previous.resetKey,
        };
      });
    };
    const schedule = () => {
      cancelAnimationFrame(pending);
      pending = requestAnimationFrame(measure);
    };
    measure();
    const resize =
      typeof ResizeObserver === 'undefined'
        ? null
        : new ResizeObserver(schedule);
    resize?.observe(frame);
    resize?.observe(body);
    const mutations = new MutationObserver((records) => {
      if (
        records.some(
          (record) =>
            record.target !== body || record.attributeName !== 'style',
        )
      )
        schedule();
    });
    mutations.observe(body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: [
        'hidden',
        'open',
        'class',
        'style',
        'data-window',
        'data-open',
      ],
    });
    window.addEventListener('resize', schedule);
    return () => {
      cancelAnimationFrame(pending);
      resize?.disconnect();
      mutations.disconnect();
      window.removeEventListener('resize', schedule);
    };
  }, [active]);

  useLayoutEffect(() => {
    if (!active || !layout.height || !content.current) return;
    const body = content.current;
    const origin = body.getBoundingClientRect().top;
    const elements = body.querySelectorAll<HTMLElement>(atoms);
    for (const element of elements) {
      const rect = element.getBoundingClientRect();
      const top = Math.round(rect.top - origin),
        bottom = Math.round(rect.bottom - origin);
      const crosses =
        (top < current.top && bottom > current.top) ||
        (top < current.bottom && bottom > current.bottom);
      // 跨页控件和短段落在能完整容纳的页显示，保留原节点、尺寸和输入状态。
      element.toggleAttribute(
        'data-page-fragment',
        crosses && rect.height <= layout.height,
      );
    }
    return () => {
      for (const element of elements)
        element.removeAttribute('data-page-fragment');
    };
  }, [active, layout, current]);

  function move(next: number) {
    setLayout((previous) => ({
      ...previous,
      page: Math.max(0, Math.min(next, previous.pages.length - 1)),
    }));
  }
  function reveal(element: HTMLElement) {
    if (!content.current || !layout.height) return;
    const rect = element.getBoundingClientRect();
    const top = rect.top - content.current.getBoundingClientRect().top;
    if (top < start || top + rect.height > current.bottom) {
      const whole = layout.pages.findIndex(
        (item) => top >= item.top - 1 && top + rect.height <= item.bottom + 1,
      );
      move(whole >= 0 ? whole : contentPageAt(layout.pages, top));
    }
  }
  return (
    <div className="content-pager">
      <div className="paged-viewport" ref={viewport}>
        <div
          className="paged-window"
          style={layout.height ? { height: current.bottom - start } : undefined}
        >
          <div
            id={id}
            ref={content}
            className="paged-content"
            style={{ transform: `translateY(${-start}px)` }}
            onFocusCapture={(event) => reveal(event.target)}
            onInvalidCapture={(event) => reveal(event.target as HTMLElement)}
            onClickCapture={(event) => {
              if (
                (event.target as HTMLElement).closest(
                  '.workspace-pagination button',
                )
              )
                move(0);
            }}
            onKeyDown={(event) => {
              if (
                (event.target as HTMLElement).closest(
                  'input, textarea, select, [contenteditable="true"]',
                )
              )
                return;
              if (event.key === 'PageDown' || event.key === 'PageUp') {
                event.preventDefault();
                move(page + (event.key === 'PageDown' ? 1 : -1));
              }
            }}
          >
            {children}
          </div>
        </div>
      </div>
      <nav className="content-pagination" aria-label={`${label}内容分页`}>
        <span className="content-page-hint">
          {count > 1 ? '内容分为多页' : '全部内容'}
        </span>
        <button
          type="button"
          aria-controls={id}
          disabled={page === 0}
          onClick={() => move(page - 1)}
        >
          上一页内容
        </button>
        <label>
          <span className="sr-only">{label}内容页码</span>
          <select
            value={page}
            onChange={(event) => move(Number(event.target.value))}
          >
            {Array.from({ length: count }, (_, index) => (
              <option key={index} value={index}>
                第 {index + 1} / {count} 页
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          aria-controls={id}
          disabled={page === count - 1}
          onClick={() => move(page + 1)}
        >
          下一页内容
        </button>
        {count > 1 && (
          <span className="sr-only" role="status">
            第 {page + 1} 页，共 {count} 页
          </span>
        )}
      </nav>
    </div>
  );
}
