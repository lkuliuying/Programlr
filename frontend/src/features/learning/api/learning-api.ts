import type {
  KnowledgeCard,
  Exercise,
  ExerciseAttempt,
  AttemptInputRequest,
} from '../../../shared/api/generated/schema';
import { requestJson, submitJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';

export type LearningSelection = {
  snapshot: string;
  analysis: string;
  endpoint: number;
};
export function parseCard(raw: unknown): KnowledgeCard {
  const item = v.object(raw);
  return {
    id: v.uuid(item.id),
    slug: v.text(item.slug),
    version: v.text(item.version),
    title: v.text(item.title),
    body: v.text(item.body),
    applicability: v.text(item.applicability),
    review_note: v.text(item.review_note),
  };
}
export function parseExercise(raw: unknown): Exercise {
  const item = v.object(raw);
  return {
    id: v.uuid(item.id),
    slug: v.text(item.slug),
    version: v.text(item.version),
    answer_version: v.text(item.answer_version),
    example_version: v.text(item.example_version),
    kind: v.oneOf(item.kind, [
      'flow_order',
      'error_prediction',
      'code_location',
    ]),
    question: v.text(item.question),
    hint: v.text(item.hint),
    options: v.list(
      item.options,
      (raw) => {
        const option = v.object(raw);
        return { id: v.text(option.id), label: v.text(option.label) };
      },
      20,
    ),
    review_note: v.text(item.review_note),
    applicable: v.boolean(item.applicable),
    applicability_reason: v.text(item.applicability_reason),
  };
}
export function typedAnswer(raw: unknown, kind: string): unknown {
  if (kind === 'flow_order') return v.list(raw, (item) => v.text(item), 20);
  const item = v.object(raw);
  if (kind === 'code_location') {
    const start = v.integer(item.start_line, 1),
      end = v.integer(item.end_line, start);
    return {
      file_path: v.sourcePath(item.file_path),
      start_line: start,
      end_line: end,
    };
  }
  if (kind !== 'error_prediction' || Object.keys(item).length > 20)
    return v.invalid();
  return Object.fromEntries(
    Object.entries(item).map(([key, raw]) => {
      const value = v.object(raw);
      return [
        v.text(key, 40),
        {
          status: v.integer(value.status, 100, 599),
          writes: v.integer(value.writes, 0, 1),
        },
      ];
    }),
  );
}
export function parseAttempt(
  raw: unknown,
  selected: LearningSelection,
): ExerciseAttempt {
  const item = v.object(raw),
    feedback = v.object(item.feedback),
    kind = v.oneOf(item.kind, [
      'flow_order',
      'error_prediction',
      'code_location',
    ]);
  if (
    item.snapshot_id !== selected.snapshot ||
    item.analysis_id !== selected.analysis ||
    item.endpoint_index !== selected.endpoint
  )
    return v.invalid();
  return {
    id: v.uuid(item.id),
    exercise_id: v.uuid(item.exercise_id),
    exercise_version: v.text(item.exercise_version),
    answer_version: v.text(item.answer_version),
    example_version: v.text(item.example_version),
    question: v.text(item.question),
    kind,
    snapshot_id: selected.snapshot,
    analysis_id: selected.analysis,
    endpoint_index: selected.endpoint,
    answer: typedAnswer(item.answer, kind),
    hint_used: v.boolean(item.hint_used),
    correct: v.boolean(item.correct),
    created_at: v.date(item.created_at),
    previous_attempt_id: v.nullable(item.previous_attempt_id ?? null, v.uuid),
    feedback: {
      expected_answer: typedAnswer(feedback.expected_answer, kind),
      explanation: v.text(feedback.explanation),
      source_refs: v.list(
        feedback.source_refs,
        (ref) => v.sourceRef(ref, selected.snapshot),
        20,
      ),
    },
  };
}
const params = (selected: LearningSelection) =>
  `analysis_id=${selected.analysis}&endpoint_index=${selected.endpoint}`;
export const getCards = (page: number, signal: AbortSignal) =>
  requestJson(
    `/api/v1/knowledge-cards/?page=${page}&page_size=10`,
    (raw) => v.page(raw, '/api/v1/knowledge-cards/', parseCard),
    { signal },
  );
export const getExercises = (
  selected: LearningSelection,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/exercises/?${params(selected)}&page=${page}&page_size=10`,
    (raw) => v.page(raw, '/api/v1/exercises/', parseExercise),
    { signal },
  );
export const submitAttempt = (
  selected: LearningSelection,
  input: AttemptInputRequest,
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    '/api/v1/exercise-attempts/',
    key,
    (raw) => parseAttempt(raw, selected),
    input,
    signal,
  );
export const getAttempt = (
  selected: LearningSelection,
  id: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/exercise-attempts/${id}/`,
    (raw) => {
      const item = parseAttempt(raw, selected);
      return item.id === id ? item : v.invalid();
    },
    { signal },
  );
export const attemptHistory = (
  selected: LearningSelection,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/exercise-attempts/?snapshot_id=${selected.snapshot}&${params(selected)}&page=${page}&page_size=10`,
    (raw) =>
      v.page(raw, '/api/v1/exercise-attempts/', (item) =>
        parseAttempt(item, selected),
      ),
    { signal },
  );
