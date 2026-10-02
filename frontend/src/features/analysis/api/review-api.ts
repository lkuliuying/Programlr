import { requestJson, submitJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import type {
  RelationDecision,
  RelationReview,
  RelationReviewInputRequest,
  RelationReviewPage,
  RelationReviewResult,
  RelationReviewState,
} from '../../../shared/api/generated/schema';

export function parseReviewInput(
  value: unknown,
  requestId: string,
): RelationReviewInputRequest {
  const item = v.object(value);
  const result = {
    request_id: v.uuid(item.request_id),
    target_id: v.uuid(item.target_id),
    action: v.oneOf(item.action, ['confirm', 'exclude', 'reset']),
    expected_revision: v.integer(item.expected_revision, 0, 2147483646),
  };
  return result.request_id === requestId && Object.keys(item).length === 4
    ? result
    : v.invalid();
}

export function parseDecision(value: unknown): RelationDecision {
  const item = v.object(value);
  const result = {
    request_id: v.uuid(item.request_id),
    target_id: v.uuid(item.target_id),
    revision: v.integer(item.revision, 0, 2147483647),
    decision: v.oneOf(item.decision, ['confirmed', 'excluded', 'undecided']),
  };
  return result.revision > 0 || result.decision === 'undecided'
    ? result
    : v.invalid();
}

function parseState(
  value: unknown,
  analysis: string,
  request: string,
): RelationReviewState {
  const item = v.object(value);
  const result = {
    analysis_id: v.uuid(item.analysis_id),
    request_id: v.uuid(item.request_id),
    revision: v.integer(item.revision, 0, 2147483647),
    confirmed_target_id: v.nullable(item.confirmed_target_id, v.uuid),
    excluded_target_ids: v.list(item.excluded_target_ids, v.uuid),
  };
  return result.analysis_id === analysis &&
    result.request_id === request &&
    new Set(result.excluded_target_ids).size ===
      result.excluded_target_ids.length &&
    !result.excluded_target_ids.includes(result.confirmed_target_id ?? '') &&
    (result.revision > 0 ||
      (!result.confirmed_target_id && !result.excluded_target_ids.length))
    ? result
    : v.invalid();
}

function parseRecord(
  value: unknown,
  analysis: string,
  request: string,
): RelationReview {
  const item = v.object(value);
  const result = {
    id: v.uuid(item.id),
    analysis_id: v.uuid(item.analysis_id),
    request_id: v.uuid(item.request_id),
    target_id: v.uuid(item.target_id),
    action: v.oneOf(item.action, ['confirm', 'exclude', 'reset']),
    revision: v.integer(item.revision, 1, 2147483647),
    created_at: v.date(item.created_at),
  };
  return result.analysis_id === analysis && result.request_id === request
    ? result
    : v.invalid();
}

export function parseReviewPage(
  value: unknown,
  analysis: string,
  request: string,
): RelationReviewPage {
  const path = `/api/v1/analyses/${analysis}/relation-reviews/`;
  const page = v.page(value, path, (item) =>
    parseRecord(item, analysis, request),
  );
  const state = parseState(v.object(value).state, analysis, request);
  if (
    page.count !== state.revision ||
    new Set(page.results.map((item) => item.id)).size !== page.results.length ||
    page.results.some(
      (item, index) =>
        item.revision > state.revision ||
        (index > 0 && item.revision >= page.results[index - 1].revision),
    ) ||
    [page.next, page.previous].some(
      (link) =>
        link !== null &&
        new URL(link, window.location.origin).searchParams.get('request_id') !==
          request,
    )
  )
    return v.invalid();
  return { ...page, state };
}

export function parseReviewResult(
  value: unknown,
  analysis: string,
  input: RelationReviewInputRequest,
): RelationReviewResult {
  const item = v.object(value);
  const record = parseRecord(item.record, analysis, input.request_id);
  const state = parseState(item.state, analysis, input.request_id);
  return record.target_id === input.target_id &&
    record.action === input.action &&
    record.revision === input.expected_revision + 1 &&
    state.revision >= record.revision
    ? { record, state }
    : v.invalid();
}

export const listReviews = (
  analysis: string,
  request: string,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/analyses/${analysis}/relation-reviews/?request_id=${request}&page=${page}&page_size=10`,
    (value) => parseReviewPage(value, analysis, request),
    { signal },
  );

export const submitReview = (
  analysis: string,
  input: RelationReviewInputRequest,
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    `/api/v1/analyses/${analysis}/relation-reviews/`,
    key,
    (value) => parseReviewResult(value, analysis, input),
    input,
    signal,
  );
