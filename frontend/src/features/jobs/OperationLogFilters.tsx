import { useRef, useState } from 'react';
import type { ReactNode, Ref } from 'react';
import { Button, DatePicker, Popover } from 'antd';
import type { DatePickerProps } from 'antd';
import datePickerLocale from 'antd/es/date-picker/locale/zh_CN';

const calendarLocale = {
  ...datePickerLocale,
  lang: {
    ...datePickerLocale.lang,
    shortWeekDays: ['日', '一', '二', '三', '四', '五', '六'],
    shortMonths: Array.from({ length: 12 }, (_, index) => `${index + 1}月`),
  },
};
const calendarPopupAlign = {
  offset: [0, 0],
  overflow: { adjustX: true, adjustY: true, shiftX: true, shiftY: true },
};
type LogDate = Exclude<DatePickerProps['value'], unknown[] | undefined>;
export type LogTimeRange = { after: LogDate; before: LogDate };
export const emptyLogTimeRange: LogTimeRange = { after: null, before: null };

function filterButton(
  label: string,
  filtered: boolean,
  ref: Ref<HTMLButtonElement>,
  open: boolean,
) {
  return (
    <button
      ref={ref}
      type="button"
      className="operation-column-filter"
      aria-label={`${label}筛选`}
      aria-pressed={filtered}
      aria-haspopup="dialog"
      aria-expanded={open}
      title={`${label}筛选${filtered ? '（已筛选）' : ''}`}
    >
      <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
        <path d="M2 3h12L9.5 8v5l-3-1.5V8Z" fill="currentColor" />
      </svg>
    </button>
  );
}

function FilterHeader({
  label,
  summary,
  children,
}: {
  label: string;
  summary: string;
  children: ReactNode;
}) {
  return (
    <span className="operation-column-heading">
      <span className="operation-filter-caption">
        <span>{label}</span>
        {summary && <small title={summary}>{summary}</small>}
      </span>
      {children}
    </span>
  );
}

export function LogValueFilter({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Record<string, string>;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(value);
  const trigger = useRef<HTMLButtonElement>(null);
  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };
  return (
    <FilterHeader
      label={label}
      summary={value ? (options[value] ?? value) : ''}
    >
      <Popover
        trigger="click"
        destroyOnHidden
        placement="bottom"
        open={open}
        onOpenChange={(next) => {
          if (next) setDraft(value);
          setOpen(next);
        }}
        content={
          <form
            className="operation-filter-dialog"
            role="dialog"
            aria-label={`${label}筛选条件`}
            onSubmit={(event) => {
              event.preventDefault();
              onChange(draft);
              close();
            }}
            onKeyDown={(event) => {
              if (event.key === 'Escape') close();
            }}
          >
            <label>
              {label}条件
              <select
                autoFocus
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
              >
                <option value="">全部</option>
                {Object.entries(options).map(([key, text]) => (
                  <option key={key} value={key}>
                    {text}
                  </option>
                ))}
              </select>
            </label>
            <div className="operation-filter-actions">
              <Button
                size="small"
                onClick={() => {
                  onChange('');
                  close();
                }}
              >
                清除{label}筛选
              </Button>
              <Button size="small" type="primary" htmlType="submit">
                应用{label}筛选
              </Button>
            </div>
          </form>
        }
      >
        {filterButton(label, !!value, trigger, open)}
      </Popover>
    </FilterHeader>
  );
}

export function LogTimeFilter({
  label,
  value,
  onChange,
}: {
  label: string;
  value: LogTimeRange;
  onChange: (value: LogTimeRange) => void;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(value);
  const [error, setError] = useState('');
  const trigger = useRef<HTMLButtonElement>(null);
  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };
  const changeDate = (field: keyof LogTimeRange, date: LogDate | LogDate[]) => {
    if (Array.isArray(date)) return;
    // 由外层统一应用范围，日历有效草稿无需等待内部弹层关闭再提交。
    setDraft((previous) => ({ ...previous, [field]: date }));
    setError('');
  };
  return (
    <FilterHeader
      label={label}
      summary={
        value.after || value.before
          ? `${value.after?.format('YYYY-MM-DD HH:mm:ss') ?? '不限'} 至 ${value.before?.format('YYYY-MM-DD HH:mm:ss') ?? '不限'}`
          : ''
      }
    >
      <Popover
        trigger="click"
        destroyOnHidden
        placement="bottom"
        open={open}
        onOpenChange={(next) => {
          if (next) {
            setDraft(value);
            setError('');
          }
          setOpen(next);
        }}
        content={
          <form
            className="operation-filter-dialog"
            role="dialog"
            aria-label={`${label}筛选条件`}
            onKeyDownCapture={(event) => {
              if (event.key === 'Escape') {
                event.preventDefault();
                event.stopPropagation();
                close();
              }
            }}
            onSubmit={(event) => {
              event.preventDefault();
              if (
                [draft.after, draft.before].some(
                  (date) => date && !date.isValid(),
                )
              ) {
                setError('请输入有效时间。');
                return;
              }
              if (
                draft.after &&
                draft.before &&
                draft.after.valueOf() > draft.before.valueOf()
              ) {
                setError('时间上界不能早于下界。');
                return;
              }
              onChange(draft);
              close();
            }}
          >
            <p>按本地时间筛选，可仅填写一端。</p>
            <label>
              {label}从
              <DatePicker
                autoFocus
                aria-label={`${label}从`}
                locale={calendarLocale}
                format="YYYY-MM-DD HH:mm:ss"
                showTime={{ format: 'HH:mm:ss' }}
                needConfirm
                popupAlign={calendarPopupAlign}
                placeholder="选择下界日期和时间"
                value={draft.after}
                classNames={{ popup: { root: 'operation-calendar-popup' } }}
                getPopupContainer={(node) =>
                  node.closest<HTMLElement>('.operation-filter-dialog') ??
                  document.body
                }
                onCalendarChange={(date) => changeDate('after', date)}
                onChange={(date) => changeDate('after', date)}
                onBlur={(event) => {
                  if (
                    event.target instanceof HTMLInputElement &&
                    !event.target.value.trim()
                  )
                    changeDate('after', null);
                }}
              />
            </label>
            <label>
              {label}至
              <DatePicker
                aria-label={`${label}至`}
                locale={calendarLocale}
                format="YYYY-MM-DD HH:mm:ss"
                showTime={{ format: 'HH:mm:ss' }}
                needConfirm
                popupAlign={calendarPopupAlign}
                placeholder="选择上界日期和时间"
                value={draft.before}
                classNames={{ popup: { root: 'operation-calendar-popup' } }}
                getPopupContainer={(node) =>
                  node.closest<HTMLElement>('.operation-filter-dialog') ??
                  document.body
                }
                onCalendarChange={(date) => changeDate('before', date)}
                onChange={(date) => changeDate('before', date)}
                onBlur={(event) => {
                  if (
                    event.target instanceof HTMLInputElement &&
                    !event.target.value.trim()
                  )
                    changeDate('before', null);
                }}
              />
            </label>
            {error && <p role="alert">{error}</p>}
            <div className="operation-filter-actions">
              <Button
                size="small"
                onClick={() => {
                  onChange(emptyLogTimeRange);
                  close();
                }}
              >
                清除{label}筛选
              </Button>
              <Button size="small" type="primary" htmlType="submit">
                应用{label}筛选
              </Button>
            </div>
          </form>
        }
      >
        {filterButton(label, !!(value.after || value.before), trigger, open)}
      </Popover>
    </FilterHeader>
  );
}
