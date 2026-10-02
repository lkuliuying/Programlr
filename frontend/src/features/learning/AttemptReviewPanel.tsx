import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from 'antd';
import type {
  AttemptReview,
  ReviewInputRequest,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import * as api from './api/paths-api';

const labels = {
  revisit: '需要再看',
  practicing: '继续练习',
  understood: '自评已理解',
};
export function AttemptReviewPanel({ attemptId }: { attemptId: string }) {
  const [page, setPage] = useState(1),
    [judgement, setJudgement] = useState<ReviewInputRequest['judgement'] | ''>(
      '',
    ),
    [note, setNote] = useState('');
  const cache = useQueryClient();
  const history = useQuery({
    queryKey: ['learning', 'reviews', attemptId, page],
    queryFn: ({ signal }) => api.listReviews(attemptId, page, signal),
  });
  const operation = useIdempotentOperation<ReviewInputRequest, AttemptReview>(
    `review.${attemptId}`,
    JSON.stringify,
    api.submitReview,
    () => {
      setPage(1);
      setJudgement('');
      setNote('');
      void cache.invalidateQueries({
        queryKey: ['learning', 'reviews', attemptId],
      });
    },
  );
  return (
    <section aria-label="复习与自我判断">
      <h4>回顾这次作答</h4>
      <p>自评与答题正确性、提示使用分别保存；选择“已理解”只是你的判断。</p>
      <Feedback error={history.error ?? operation.error} />
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (judgement)
            operation.start({ attempt_id: attemptId, judgement, note });
        }}
      >
        <label>
          本次自评
          <select
            required
            value={judgement}
            onChange={(event) => {
              const value = event.target.value;
              if (
                value === '' ||
                value === 'revisit' ||
                value === 'practicing' ||
                value === 'understood'
              )
                setJudgement(value);
            }}
          >
            <option value="">请选择</option>
            {Object.entries(labels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          复习笔记
          <textarea
            maxLength={1000}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>
        <Button
          htmlType="submit"
          aria-label={
            operation.pending ? '用原输入恢复复习提交' : '保存复习记录'
          }
          loading={operation.isPending}
          disabled={!judgement}
        >
          {operation.pending ? '用原输入恢复复习提交' : '保存复习记录'}
        </Button>
        {operation.pending && (
          <p role="note">
            提交结果待确认；刷新后使用原自评和笔记恢复，不会覆盖历史。
          </p>
        )}
      </form>
      <h5>复习历史</h5>
      {history.data?.count === 0 && <p>尚无自评记录。</p>}
      <ul>
        {history.data?.results.map((item) => (
          <li key={item.id}>
            {labels[item.judgement]} ·{' '}
            {new Date(item.created_at).toLocaleString()}
            <p>{item.note || '未填写笔记'}</p>
          </li>
        ))}
      </ul>
      {history.data && (
        <PageControls
          page={page}
          previous={history.data.previous}
          next={history.data.next}
          onPage={setPage}
        />
      )}
    </section>
  );
}
