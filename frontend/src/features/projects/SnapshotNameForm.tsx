import { useEffect, useId, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from 'antd';
import type { Snapshot } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { ContentPager } from '../../shared/components/ContentPager';
import { listSnapshots, renameSnapshot } from './api/projects-api';

export function SnapshotNameForm({ snapshot }: { snapshot: Snapshot }) {
  const [name, setName] = useState(snapshot.name),
    [open, setOpen] = useState(false),
    [saved, setSaved] = useState(false);
  const formId = useId();
  const cache = useQueryClient();
  const controller = useRef<AbortController | null>(null);
  const active = useRef(true);
  const busy = useRef(false);
  const dirty = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!dirty.current) setName(snapshot.name);
  }, [snapshot.name]);
  const mutation = useMutation({
    mutationFn: (value: string) => {
      controller.current = new AbortController();
      return renameSnapshot(snapshot, value, controller.current.signal);
    },
    retry: false,
    onSuccess: async (result) => {
      await Promise.all([
        cache.cancelQueries({
          queryKey: ['projects', 'snapshot', result.project_id, result.id],
          exact: true,
        }),
        cache.cancelQueries({
          queryKey: ['projects', 'snapshots', result.project_id],
        }),
      ]);
      cache.setQueryData(
        ['projects', 'snapshot', result.project_id, result.id],
        result,
      );
      cache.setQueriesData<Awaited<ReturnType<typeof listSnapshots>>>(
        { queryKey: ['projects', 'snapshots', result.project_id] },
        (page) =>
          page && {
            ...page,
            results: page.results.map((item) =>
              item.id === result.id ? result : item,
            ),
          },
      );
      if (active.current) {
        dirty.current = false;
        setName(result.name);
        setSaved(true);
      }
    },
    onSettled: () => {
      busy.current = false;
    },
  });
  return (
    <div className="snapshot-name-editor">
      <button
        type="button"
        className="snapshot-name-trigger"
        aria-expanded={open}
        aria-controls={formId}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? '收起快照命名' : '命名当前快照'}
      </button>
      <form
        hidden={!open}
        id={formId}
        className="workspace-form snapshot-name-form"
        aria-label="快照命名"
        onSubmit={(event) => {
          event.preventDefault();
          if (!busy.current) {
            busy.current = true;
            setSaved(false);
            mutation.mutate(name);
          }
        }}
      >
        <ContentPager label="快照命名" active={open}>
          <label>
            快照名称
            <input
              required
              maxLength={400}
              value={name}
              disabled={mutation.isPending}
              placeholder="为这份快照命名"
              onChange={(event) => {
                dirty.current = true;
                setSaved(false);
                setName(event.target.value);
              }}
            />
          </label>
          <small>
            名称保存在服务端；只更新名称，源码内容和已有分析引用保持原快照。
          </small>
          <Button htmlType="submit" loading={mutation.isPending}>
            保存快照名称
          </Button>
          <Feedback error={mutation.error} />
          {saved && <p role="status">快照名称已保存。</p>}
        </ContentPager>
      </form>
    </div>
  );
}
