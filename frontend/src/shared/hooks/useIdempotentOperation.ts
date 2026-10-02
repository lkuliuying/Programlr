import { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ApiError, isRecord } from '../api/client';

type Pending = { key: string; digest: string };
function read(name: string): Pending | null {
  const raw = sessionStorage.getItem(name);
  if (!raw) return null;
  const value: unknown = JSON.parse(raw);
  if (
    !isRecord(value) ||
    typeof value.key !== 'string' ||
    !/^[0-9a-f-]{36}$/.test(value.key) ||
    typeof value.digest !== 'string' ||
    !/^[0-9a-f]{64}$/.test(value.digest)
  )
    throw new Error('操作标识损坏，请先核对任务历史。');
  return { key: value.key, digest: value.digest };
}

export function useIdempotentOperation<T, R>(
  scope: string,
  fingerprint: (input: T) => string | Blob,
  execute: (input: T, key: string, signal: AbortSignal) => Promise<R>,
  onSuccess: (result: R) => void,
  onUnconfirmed?: (jobId: string) => void,
  onFailure?: (error: Error, retained: boolean) => void,
) {
  const storage = 'learning-lab.operation.' + scope;
  const [pending, setPending] = useState(() => {
    try {
      return read(storage) !== null;
    } catch {
      return true;
    }
  });
  const active = useRef(true);
  const busy = useRef(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      controller.current?.abort();
    };
  }, []);
  const mutation = useMutation({
    mutationFn: async (input: T) => {
      const original = read(storage);
      const content = fingerprint(input);
      const buffer =
        typeof content === 'string'
          ? new TextEncoder().encode(content)
          : await content.arrayBuffer();
      const digest = Array.from(
        new Uint8Array(await crypto.subtle.digest('SHA-256', buffer)),
      )
        .map((byte) => byte.toString(16).padStart(2, '0'))
        .join('');
      if (!active.current)
        throw new DOMException('操作已离开当前视图。', 'AbortError');
      if (original && original.digest !== digest)
        throw new Error(
          '请使用上次的相同输入恢复提交；当前输入与原操作不一致。',
        );
      const key = original?.key ?? crypto.randomUUID();
      sessionStorage.setItem(storage, JSON.stringify({ key, digest }));
      setPending(true);
      controller.current = new AbortController();
      try {
        const result = await execute(input, key, controller.current.signal);
        if (read(storage)?.key === key) sessionStorage.removeItem(storage);
        return result;
      } catch (error) {
        if (
          error instanceof ApiError &&
          ((!original && [400, 403, 404, 413, 415].includes(error.status)) ||
            (error.status === 409 &&
              [
                'CONSENT_STALE',
                'EXERCISE_VERSION_MISMATCH',
                'EXERCISE_NOT_APPLICABLE',
                'REATTEMPT_SCOPE_MISMATCH',
                'LAB_VERSION_MISMATCH',
                'LAB_NOT_APPLICABLE',
                'MODEL_NOT_CONFIGURED',
                'MODEL_CONFIGURATION_INVALID',
                'CONTEXT_UNAVAILABLE',
                'RELATION_REVISION_CONFLICT',
                'RELATION_NOT_CANDIDATE',
                'COMPARISON_SCOPE_MISMATCH',
              ].includes(error.code ?? '')))
        ) {
          sessionStorage.removeItem(storage);
          if (active.current) setPending(false);
        }
        throw error;
      }
    },
    retry: false,
    onSuccess: (result) => {
      if (active.current) {
        setPending(false);
        onSuccess(result);
      }
    },
    onError: (error) => {
      if (active.current && onFailure) {
        let retained = true;
        try {
          retained = read(storage) !== null;
        } catch {
          // 损坏的恢复标识也保留，不能把未知提交当作未执行。
        }
        onFailure(error, retained);
      }
      if (
        active.current &&
        error instanceof ApiError &&
        typeof error.details.job_url === 'string'
      ) {
        const match = /^\/api\/v1\/jobs\/([0-9a-f-]{36})\/$/.exec(
          error.details.job_url,
        );
        if (match) onUnconfirmed?.(match[1]);
      }
    },
    onSettled: () => {
      busy.current = false;
    },
  });
  return {
    pending,
    isPending: mutation.isPending,
    error: mutation.error,
    start: (input: T) => {
      if (!busy.current) {
        busy.current = true;
        mutation.mutate(input);
      }
    },
  };
}
