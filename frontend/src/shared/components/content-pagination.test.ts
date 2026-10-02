import { expect, test } from 'vitest';
import { contentPageAt, paginateContent } from './content-pagination';

test('空内容、单页和恰好填满一页不会多出空白页', () => {
  expect(paginateContent(500, 0, [])).toEqual([{ top: 0, bottom: 0 }]);
  expect(paginateContent(500, 320, [])).toEqual([{ top: 0, bottom: 320 }]);
  expect(paginateContent(500, 500, [])).toEqual([{ top: 0, bottom: 500 }]);
  expect(paginateContent(0, 500, [])).toEqual([{ top: 0, bottom: 0 }]);
});

test('在完整记录前分页，连续记录之间不丢失或重复内容', () => {
  const ranges = Array.from({ length: 10 }, (_, index) => ({
    top: 120 + index * 120,
    bottom: 240 + index * 120,
  }));
  const breaks = paginateContent(550, 1320, ranges);
  expect(breaks).toEqual([
    { top: 0, bottom: 480 },
    { top: 480, bottom: 960 },
    { top: 960, bottom: 1320 },
  ]);
  for (const range of ranges)
    expect(
      breaks.some(
        (page) => range.top >= page.top && range.bottom <= page.bottom,
      ),
    ).toBe(true);
});

test('长内容持续前进，缩小尺寸后仍覆盖首尾，超高块可继续分页', () => {
  const breaks = paginateContent(180, 1000, [{ top: 20, bottom: 980 }]);
  expect(breaks[0]!.top).toBe(0);
  expect(breaks.at(-1)!.bottom).toBe(1000);
  expect(
    breaks.every(({ top, bottom }) => bottom > top && bottom - top <= 180),
  ).toBe(true);
  expect(contentPageAt(breaks, 800)).toBe(4);
  expect(contentPageAt([{ top: 0, bottom: 200 }], 800)).toBe(0);
});

test('文字行与控件边界优先，异常范围不影响可达性', () => {
  const pages = paginateContent(500, 700, [
    { top: 470, bottom: 510 },
    { top: NaN, bottom: 500 },
  ]);
  expect(pages).toEqual([
    { top: 0, bottom: 470 },
    { top: 470, bottom: 700 },
  ]);
  expect(contentPageAt(pages, 470)).toBe(1);
});

test('并排控件没有共同断点时，跨界内容能在某一页完整显示', () => {
  const ranges = Array.from({ length: 30 }, (_, index) => ({
    top: index * 30,
    bottom: index * 30 + 50,
  }));
  const pages = paginateContent(200, 920, ranges);
  for (const range of ranges)
    expect(
      pages.some(
        (page) => range.top >= page.top && range.bottom <= page.bottom,
      ),
    ).toBe(true);
  expect(pages.every((page) => page.bottom - page.top <= 200)).toBe(true);
});
