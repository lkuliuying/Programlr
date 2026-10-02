import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from 'antd';
import type {
  Exercise,
  ExerciseAttempt,
  SourceRef,
  AttemptInputRequest,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import * as api from './api/learning-api';
import { AttemptReviewPanel } from './AttemptReviewPanel';

export function LearningPanel({
  selected,
  attemptId,
  onAttempt,
  onSource,
}: {
  selected: api.LearningSelection;
  attemptId: string | null;
  onAttempt: (id: string) => void;
  onSource: (ref: SourceRef) => void;
}) {
  const [reattempt, setReattempt] = useState<{
    exercise: string;
    previous: string;
  } | null>(null);
  const [exercisePage, setExercisePage] = useState(1),
    [historyPage, setHistoryPage] = useState(1);
  const exercises = useQuery({
    queryKey: ['learning', 'exercises', selected, exercisePage],
    queryFn: ({ signal }) => api.getExercises(selected, exercisePage, signal),
  });
  const history = useQuery({
    queryKey: ['learning', 'history', selected, historyPage, attemptId],
    queryFn: ({ signal }) => api.attemptHistory(selected, historyPage, signal),
  });
  const result = useQuery({
    queryKey: ['learning', 'attempt', selected, attemptId],
    queryFn: ({ signal }) => api.getAttempt(selected, attemptId!, signal),
    enabled: !!attemptId,
  });
  return (
    <section aria-label="固定练习">
      <h3>讲解后的练习</h3>
      <p>固定题按版本核对；正确结果与使用提示分开记录，不推断已掌握。</p>
      <Feedback error={exercises.error ?? history.error ?? result.error} />
      {exercises.isPending && <p role="status">核对教学内容版本…</p>}
      {exercises.data &&
        !exercises.data.results.some((item) => item.applicable) && (
          <p role="note">
            无对应练习。固定题仅在源码摘要匹配的内置任务簿创建任务接口提供。
          </p>
        )}
      {exercises.data?.results
        .filter((item) => item.applicable)
        .map((item) => (
          <ExerciseForm
            key={`${item.id}.${item.version}.${reattempt?.exercise === item.id ? reattempt.previous : 'initial'}`}
            exercise={item}
            selected={selected}
            onAttempt={onAttempt}
            onSource={onSource}
            previousAttemptId={
              reattempt?.exercise === item.id ? reattempt.previous : null
            }
          />
        ))}
      <Pagination
        name="固定练习"
        page={exercisePage}
        data={exercises.data}
        onPage={setExercisePage}
      />
      {result.isFetching && <p role="status">读取已保存作答…</p>}
      {result.data && (
        <article className="attempt-result" aria-label="作答反馈">
          <h4>{result.data.correct ? '本次作答正确' : '本次作答不正确'}</h4>
          <p>{result.data.question}</p>
          <p>
            题目版本 {result.data.exercise_version} · 答案版本{' '}
            {result.data.answer_version} ·{' '}
            {result.data.hint_used ? '使用了提示' : '未使用提示'}
          </p>
          <p>{result.data.feedback.explanation}</p>
          {result.data.previous_attempt_id && (
            <p>重新练习自作答：{result.data.previous_attempt_id}</p>
          )}
          <Button
            disabled={
              !exercises.data?.results.some(
                (item) =>
                  item.id === result.data.exercise_id &&
                  item.version === result.data.exercise_version &&
                  item.applicable,
              )
            }
            onClick={() =>
              setReattempt({
                exercise: result.data!.exercise_id,
                previous: result.data!.id,
              })
            }
          >
            重新练习这道题
          </Button>
          <p>重新练习会新增作答，保留本次答案；需原题版本仍适用于此工作区。</p>
          <AttemptReviewPanel key={result.data.id} attemptId={result.data.id} />
          <details>
            <summary>本次答案与标准答案</summary>
            <pre>
              {JSON.stringify(
                {
                  本次答案: result.data.answer,
                  标准答案: result.data.feedback.expected_answer,
                },
                null,
                2,
              )}
            </pre>
          </details>
          {result.data.feedback.source_refs.map((ref, index) => (
            <p key={index}>
              <button
                type="button"
                className="source-link"
                onClick={() => onSource(ref)}
              >
                {ref.file_path}:{ref.start_line}–{ref.end_line}
              </button>
            </p>
          ))}
        </article>
      )}
      <h4>作答历史</h4>
      {history.data?.results.length === 0 && <p>该接口暂无作答记录。</p>}
      {history.data?.results.map((item) => (
        <p key={item.id}>
          <button
            type="button"
            className="source-link"
            onClick={() => onAttempt(item.id)}
          >
            {new Date(item.created_at).toLocaleString('zh-CN')} ·{' '}
            {item.question} · {item.correct ? '正确' : '错误'} · v
            {item.exercise_version}
          </button>
        </p>
      ))}
      <Pagination
        name="作答历史"
        page={historyPage}
        data={history.data}
        onPage={setHistoryPage}
      />
    </section>
  );
}
function Pagination({
  name,
  page,
  data,
  onPage,
}: {
  name: string;
  page: number;
  data: { next: string | null; previous: string | null } | undefined;
  onPage: (value: number) => void;
}) {
  if (!data?.next && !data?.previous) return null;
  return (
    <nav aria-label={`${name}分页`}>
      <Button disabled={!data?.previous} onClick={() => onPage(page - 1)}>
        上一页
      </Button>
      <span> 第 {page} 页 </span>
      <Button disabled={!data?.next} onClick={() => onPage(page + 1)}>
        下一页
      </Button>
    </nav>
  );
}
function ExerciseForm({
  exercise,
  selected,
  onAttempt,
  onSource,
  previousAttemptId,
}: {
  exercise: Exercise;
  selected: api.LearningSelection;
  onAttempt: (id: string) => void;
  onSource: (ref: SourceRef) => void;
  previousAttemptId: string | null;
}) {
  const [hint, setHint] = useState(false);
  const [order, setOrder] = useState(
    exercise.options.map((option) => option.id),
  );
  const [prediction, setPrediction] = useState<
    Record<string, { status: number; writes: number }>
  >(() =>
    Object.fromEntries(
      exercise.options.map((item) => [item.id, { status: 200, writes: 0 }]),
    ),
  );
  const [file, setFile] = useState(exercise.options[0]?.id ?? ''),
    [start, setStart] = useState(1),
    [end, setEnd] = useState(1);
  const operation = useIdempotentOperation<
    AttemptInputRequest,
    ExerciseAttempt
  >(
    `attempt.${selected.analysis}.${selected.endpoint}.${exercise.id}.${exercise.version}${previousAttemptId ? `.reattempt.${previousAttemptId}` : ''}`,
    JSON.stringify,
    (input, key, signal) => api.submitAttempt(selected, input, key, signal),
    (item) => onAttempt(item.id),
  );
  const answer =
    exercise.kind === 'flow_order'
      ? order
      : exercise.kind === 'error_prediction'
        ? prediction
        : { file_path: file, start_line: start, end_line: end };
  function move(index: number, direction: number) {
    const next = [...order];
    [next[index], next[index + direction]] = [
      next[index + direction],
      next[index],
    ];
    setOrder(next);
  }
  return (
    <form
      className="exercise-form"
      onSubmit={(event) => {
        event.preventDefault();
        operation.start({
          analysis_id: selected.analysis,
          snapshot_id: selected.snapshot,
          endpoint_index: selected.endpoint,
          exercise_id: exercise.id,
          exercise_version: exercise.version,
          answer,
          hint_used: hint,
          ...(previousAttemptId
            ? { previous_attempt_id: previousAttemptId }
            : {}),
        });
      }}
    >
      <h4>{exercise.question}</h4>
      {previousAttemptId && (
        <p role="status">本次重新练习关联原作答，提交后新增记录。</p>
      )}
      <small>
        {exercise.example_version} · 题目 v{exercise.version} · 答案 v
        {exercise.answer_version}
      </small>
      {exercise.kind === 'flow_order' && (
        <ol>
          {order.map((id, index) => (
            <li key={id}>
              <span>
                {exercise.options.find((option) => option.id === id)?.label}
              </span>
              <div>
                <Button
                  aria-label={`上移第 ${index + 1} 步`}
                  disabled={index === 0}
                  onClick={() => move(index, -1)}
                >
                  上移
                </Button>
                <Button
                  aria-label={`下移第 ${index + 1} 步`}
                  disabled={index === order.length - 1}
                  onClick={() => move(index, 1)}
                >
                  下移
                </Button>
              </div>
            </li>
          ))}
        </ol>
      )}
      {exercise.kind === 'error_prediction' &&
        exercise.options.map((option) => (
          <fieldset key={option.id}>
            <legend>{option.label}</legend>
            <label>
              HTTP 状态
              <input
                type="number"
                min={100}
                max={599}
                required
                value={prediction[option.id].status}
                onChange={(event) =>
                  setPrediction({
                    ...prediction,
                    [option.id]: {
                      ...prediction[option.id],
                      status: Number(event.target.value),
                    },
                  })
                }
              />
            </label>
            <label>
              新增记录
              <select
                value={prediction[option.id].writes}
                onChange={(event) =>
                  setPrediction({
                    ...prediction,
                    [option.id]: {
                      ...prediction[option.id],
                      writes: Number(event.target.value),
                    },
                  })
                }
              >
                <option value={0}>0 条</option>
                <option value={1}>1 条</option>
              </select>
            </label>
          </fieldset>
        ))}
      {exercise.kind === 'code_location' && (
        <fieldset>
          <legend>关键代码位置</legend>
          <label>
            文件
            <select
              value={file}
              onChange={(event) => setFile(event.target.value)}
            >
              {exercise.options.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            起始行
            <input
              type="number"
              required
              min={1}
              value={start}
              onChange={(event) => setStart(Number(event.target.value))}
            />
          </label>
          <label>
            结束行
            <input
              type="number"
              required
              min={start}
              value={end}
              onChange={(event) => setEnd(Number(event.target.value))}
            />
          </label>
          <Button
            disabled={
              !Number.isInteger(start) ||
              !Number.isInteger(end) ||
              start < 1 ||
              end < start
            }
            onClick={() =>
              onSource({
                snapshot_id: selected.snapshot,
                file_path: file,
                start_line: start,
                end_line: end,
              })
            }
          >
            预览作答位置
          </Button>
        </fieldset>
      )}
      <div className="panel-actions">
        <Button onClick={() => setHint(true)}>查看提示</Button>
        <Button htmlType="submit" loading={operation.isPending}>
          {operation.pending ? '恢复本次作答提交' : '提交作答'}
        </Button>
      </div>
      {hint && <p role="note">提示：{exercise.hint}</p>}
      <Feedback error={operation.error} />
      <details>
        <summary>内容维护说明</summary>
        <p>{exercise.review_note}</p>
      </details>
    </form>
  );
}
