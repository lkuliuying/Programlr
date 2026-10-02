export type ContentRange = { top: number; bottom: number };

export function paginateContent(
  height: number,
  contentHeight: number,
  ranges: ContentRange[],
): ContentRange[] {
  if (!Number.isFinite(height) || height < 1 || !Number.isFinite(contentHeight))
    return [{ top: 0, bottom: 0 }];
  const total = Math.max(0, Math.ceil(contentHeight));
  const protectedRanges = ranges
    .filter(
      ({ top, bottom }) =>
        Number.isFinite(top) &&
        Number.isFinite(bottom) &&
        bottom > top &&
        bottom - top <= height,
    )
    .sort((a, b) => a.top - b.top);
  const pages: ContentRange[] = [];
  let start = 0;
  while (start + height < total) {
    let end = start + height;
    // 按文字行和控件边界回退，避免把同一段内容中的控件分到两页。
    for (const range of [...protectedRanges].reverse()) {
      if (range.top < end && range.bottom > end) end = range.top;
    }
    if (end > start) {
      pages.push({ top: start, bottom: end });
      start = end;
    } else {
      // 并排内容可能没有共同断点；下一页承接跨界部分，使每个控件至少完整出现一次。
      const limit = start + height;
      const crossing = protectedRanges.filter(
        (range) =>
          range.top > start && range.top < limit && range.bottom > limit,
      );
      pages.push({ top: start, bottom: limit });
      start = crossing.length
        ? Math.min(...crossing.map((range) => range.top))
        : limit;
    }
  }
  pages.push({ top: start, bottom: total });
  return pages;
}

export function contentPageAt(pages: ContentRange[], position: number): number {
  for (let index = pages.length - 1; index > 0; index--)
    if (pages[index]!.top <= position) return index;
  return 0;
}
