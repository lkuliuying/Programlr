import type { Snapshot } from '../../shared/api/generated/schema';

export function snapshotDisplayName(snapshot: Snapshot): string {
  return (
    snapshot.name ||
    `未命名快照 · ${new Date(snapshot.created_at).toLocaleString('zh-CN')}`
  );
}
