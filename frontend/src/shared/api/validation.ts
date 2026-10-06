import { ApiError, isRecord } from './client';
import type { SourceRef } from './generated/schema';

export function invalid(): never {
  throw new ApiError('响应结构或资源归属无效。', 0);
}
export function object(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : invalid();
}
export function text(value: unknown, maximum = 10000): string {
  return typeof value === 'string' && value.length <= maximum
    ? value
    : invalid();
}
export function integer(
  value: unknown,
  minimum = 0,
  maximum = Number.MAX_SAFE_INTEGER,
): number {
  return typeof value === 'number' &&
    Number.isSafeInteger(value) &&
    value >= minimum &&
    value <= maximum
    ? value
    : invalid();
}
export function boolean(value: unknown): boolean {
  return typeof value === 'boolean' ? value : invalid();
}
export function uuid(value: unknown): string {
  return typeof value === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value)
    ? value
    : invalid();
}
export function oneOf<T extends string>(
  value: unknown,
  choices: readonly T[],
): T {
  return choices.find((choice) => choice === value) ?? invalid();
}
export function list<T>(
  value: unknown,
  decode: (item: unknown) => T,
  maximum = 10000,
): T[] {
  return Array.isArray(value) && value.length <= maximum
    ? value.map(decode)
    : invalid();
}
export function nullable<T>(
  value: unknown,
  decode: (item: unknown) => T,
): T | null {
  return value === null ? null : decode(value);
}
export function date(value: unknown): string {
  const result = text(value, 40);
  return result.endsWith('Z') && !Number.isNaN(Date.parse(result))
    ? result
    : invalid();
}
export function sourcePath(value: unknown): string {
  const result = text(value, 1024);
  return !/[\\:]/.test(result) &&
    ![...result].some((char) => char.charCodeAt(0) < 32) &&
    result.split('/').every((part) => part && part !== '.' && part !== '..')
    ? result
    : invalid();
}
export function sourceRef(value: unknown, snapshotId: string): SourceRef {
  const item = object(value);
  const result = {
    snapshot_id: uuid(item.snapshot_id),
    file_path: sourcePath(item.file_path),
    start_line: integer(item.start_line, 1),
    end_line: integer(item.end_line, 1),
  };
  return result.snapshot_id === snapshotId &&
    result.end_line >= result.start_line
    ? result
    : invalid();
}
export function page<T>(
  value: unknown,
  resourcePath: string,
  decode: (item: unknown) => T,
  allowedFilters: readonly string[] = [],
) {
  const item = object(value);
  const link = (value: unknown) =>
    nullable(value, (raw) => {
      const result = text(raw);
      if (!result.startsWith(resourcePath + '?')) return invalid();
      const query = new URLSearchParams(result.slice(resourcePath.length + 1));
      if (
        [...query.keys()].some(
          (key) =>
            ![
              'page',
              'page_size',
              'kind',
              'snapshot_id',
              'attempt_id',
              'analysis_id',
              'endpoint_index',
              'request_id',
              ...allowedFilters,
            ].includes(key) || query.getAll(key).length !== 1,
        ) ||
        !/^[1-9][0-9]*$/.test(query.get('page') ?? '') ||
        !/^[1-9][0-9]*$/.test(query.get('page_size') ?? '')
      )
        return invalid();
      return result;
    });
  const result = {
    count: integer(item.count),
    next: link(item.next),
    previous: link(item.previous),
    results: list(item.results, decode, 100),
  };
  return result.results.length <= result.count ? result : invalid();
}
