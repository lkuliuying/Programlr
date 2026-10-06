import { afterEach, beforeEach, vi } from 'vitest';

let releaseMedia: (() => void) | undefined;

beforeEach(() => {
  // jsdom 不实现媒体查询；这里仅为组件行为提供可随 resize 更新的测试替身。
  const queries = new Map<string, { target: EventTarget; previous: boolean }>();
  const matches = (query: string) => {
    const min = /min-width:\s*(\d+)px/.exec(query);
    const max = /max-width:\s*(\d+)px/.exec(query);
    return (
      (!min || window.innerWidth >= Number(min[1])) &&
      (!max || window.innerWidth <= Number(max[1]))
    );
  };
  const resize = () => {
    for (const [query, item] of queries) {
      const current = matches(query);
      if (item.previous === current) continue;
      item.previous = current;
      item.target.dispatchEvent(
        Object.assign(new Event('change'), { matches: current, media: query }),
      );
    }
  };
  window.addEventListener('resize', resize);
  releaseMedia = () => window.removeEventListener('resize', resize);
  vi.stubGlobal('matchMedia', (query: string) => {
    let item = queries.get(query);
    if (!item) {
      item = { target: new EventTarget(), previous: matches(query) };
      queries.set(query, item);
    }
    const target = item.target;
    return {
      media: query,
      get matches() {
        return matches(query);
      },
      onchange: null,
      addEventListener: target.addEventListener.bind(target),
      removeEventListener: target.removeEventListener.bind(target),
      dispatchEvent: target.dispatchEvent.bind(target),
      addListener: (listener: EventListener) =>
        target.addEventListener('change', listener),
      removeListener: (listener: EventListener) =>
        target.removeEventListener('change', listener),
    };
  });
});

afterEach(() => {
  releaseMedia?.();
  releaseMedia = undefined;
});
