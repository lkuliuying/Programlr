import { useSyncExternalStore } from 'react';
import type { ReactNode } from 'react';
import { Table } from 'antd';
import './RecordList.css';

export type RecordColumn<T> = {
  key: string;
  title: string;
  render: (record: T) => ReactNode;
  width?: number;
};

type RecordListProps<T> = {
  label: string;
  records: readonly T[];
  columns: readonly RecordColumn<T>[];
  rowKey: (record: T) => string;
  recordTitle: (record: T) => ReactNode;
  selectedKey?: string;
  empty?: ReactNode;
  titleColumnKey?: string;
};

const compactQuery = '(max-width: 767px)';

function readCompact() {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia(compactQuery).matches
  );
}

function subscribeCompact(onChange: () => void) {
  if (typeof window.matchMedia !== 'function') return () => {};
  const media = window.matchMedia(compactQuery);
  media.addEventListener('change', onChange);
  return () => media.removeEventListener('change', onChange);
}

export function RecordList<T>({
  label,
  records,
  columns,
  rowKey,
  recordTitle,
  selectedKey,
  empty = '暂无记录。',
  titleColumnKey,
}: RecordListProps<T>) {
  const compact = useSyncExternalStore(
    subscribeCompact,
    readCompact,
    () => false,
  );

  if (compact) {
    return (
      <ul className="record-list record-list--cards" aria-label={label}>
        {!records.length && <li className="record-list__empty">{empty}</li>}
        {records.map((record) => {
          const key = rowKey(record);
          return (
            <li
              key={key}
              data-page-keep
              className={
                key === selectedKey ? 'record-list__selected' : undefined
              }
            >
              <div className="record-list__title">{recordTitle(record)}</div>
              <dl>
                {columns
                  .filter((column) => column.key !== titleColumnKey)
                  .map((column) => (
                    <div key={column.key}>
                      <dt>{column.title}</dt>
                      <dd>{column.render(record)}</dd>
                    </div>
                  ))}
              </dl>
            </li>
          );
        })}
      </ul>
    );
  }

  return (
    <div className="record-list record-list--table">
      <Table<T>
        aria-label={label}
        size="small"
        pagination={false}
        dataSource={records}
        columns={columns.map((column) => ({
          key: column.key,
          title: column.title,
          width: column.width,
          render: (_value: unknown, record: T) => column.render(record),
        }))}
        rowKey={rowKey}
        rowClassName={(record) =>
          rowKey(record) === selectedKey ? 'record-list__selected' : ''
        }
        onRow={(record) => ({
          'data-page-keep': true,
          'aria-selected':
            selectedKey === undefined
              ? undefined
              : rowKey(record) === selectedKey,
        })}
        locale={{ emptyText: empty }}
      />
    </div>
  );
}
