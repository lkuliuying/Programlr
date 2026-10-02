import type {
  KnowledgeCurriculum,
  LearningPath,
  AttemptReview,
  ReviewInputRequest,
} from '../../../shared/api/generated/schema';
import { requestJson, submitJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import { parseCard, type LearningSelection } from './learning-api';

export function parseCurriculum(raw: unknown): KnowledgeCurriculum {
  const item = v.object(raw),
    definition = v.object(item.definition);
  const nodes = v.list(
    definition.nodes,
    (raw) => {
      const node = v.object(raw);
      return {
        slug: v.text(node.slug, 80),
        card_version: v.text(node.card_version, 40),
      };
    },
    100,
  );
  const identifiers = new Set(nodes.map((node) => node.slug));
  if (!nodes.length || identifiers.size !== nodes.length) return v.invalid();
  const edges = v.list(
    definition.edges,
    (raw) => {
      const edge = v.object(raw),
        prerequisite = v.text(edge.prerequisite, 80),
        dependent = v.text(edge.dependent, 80);
      if (
        !identifiers.has(prerequisite) ||
        !identifiers.has(dependent) ||
        prerequisite === dependent
      )
        return v.invalid();
      return { prerequisite, dependent };
    },
    400,
  );
  if (
    new Set(edges.map((edge) => `${edge.prerequisite}/${edge.dependent}`))
      .size !== edges.length
  )
    return v.invalid();
  const remaining = new Set(identifiers);
  while (remaining.size) {
    const ready = [...remaining].filter(
      (node) =>
        !edges.some(
          (edge) => edge.dependent === node && remaining.has(edge.prerequisite),
        ),
    );
    if (!ready.length) return v.invalid();
    ready.forEach((node) => remaining.delete(node));
  }
  const goals = Object.fromEntries(
    Object.entries(v.object(definition.goals)).map(([key, raw]) => {
      const targets = v.list(raw, (value) => v.text(value, 80), 100);
      if (
        !targets.length ||
        new Set(targets).size !== targets.length ||
        targets.some((target) => !identifiers.has(target))
      )
        return v.invalid();
      return [v.text(key, 80), targets];
    }),
  );
  if (
    !Object.keys(goals).length ||
    Object.keys(goals).length > 20 ||
    item.slug !== definition.slug ||
    item.version !== definition.version ||
    item.title !== definition.title ||
    !/^[a-f0-9]{64}$/.test(v.text(item.content_digest, 64))
  )
    return v.invalid();
  return {
    id: v.uuid(item.id),
    slug: v.text(item.slug, 80),
    version: v.text(item.version, 40),
    title: v.text(item.title, 200),
    content_digest: v.text(item.content_digest, 64),
    definition: {
      slug: v.text(definition.slug),
      version: v.text(definition.version),
      title: v.text(definition.title),
      example_version: v.text(definition.example_version),
      review_note: v.text(definition.review_note),
      nodes,
      edges,
      goals,
    },
  };
}

export function parsePath(
  raw: unknown,
  selected: LearningSelection,
  curriculumId: string,
  goal: string,
): LearningPath {
  const item = v.object(raw),
    curriculum = parseCurriculum(item.curriculum),
    applicable = v.boolean(item.applicable);
  if (
    item.snapshot_id !== selected.snapshot ||
    item.analysis_id !== selected.analysis ||
    item.endpoint_index !== selected.endpoint ||
    curriculum.id !== curriculumId ||
    item.goal !== goal
  )
    return v.invalid();
  const targets = v.list(item.targets, (value) => v.text(value), 100),
    order = v.list(item.order, (value) => v.text(value), 100),
    steps = v.list(item.steps, parseCard, 100);
  if (
    JSON.stringify(targets) !==
      JSON.stringify(curriculum.definition.goals[goal]) ||
    order.length !== steps.length ||
    new Set(order).size !== order.length ||
    steps.some(
      (card, index) =>
        card.slug !== order[index] ||
        !curriculum.definition.nodes.some(
          (node) =>
            node.slug === card.slug && node.card_version === card.version,
        ),
    )
  )
    return v.invalid();
  if (!applicable && order.length) return v.invalid();
  if (applicable) {
    const required = new Set(targets);
    let added = true;
    while (added) {
      added = false;
      curriculum.definition.edges.forEach((edge) => {
        if (required.has(edge.dependent) && !required.has(edge.prerequisite)) {
          required.add(edge.prerequisite);
          added = true;
        }
      });
    }
    if (
      order.length !== required.size ||
      order.some((node) => !required.has(node)) ||
      curriculum.definition.edges.some(
        (edge) =>
          required.has(edge.dependent) &&
          order.indexOf(edge.prerequisite) >= order.indexOf(edge.dependent),
      )
    )
      return v.invalid();
  }
  return {
    snapshot_id: selected.snapshot,
    analysis_id: selected.analysis,
    endpoint_index: selected.endpoint,
    curriculum,
    goal,
    targets,
    order,
    steps,
    applicable,
    applicability_reason: v.text(item.applicability_reason),
  };
}
export const listCurricula = (page: number, signal: AbortSignal) =>
  requestJson(
    `/api/v1/knowledge-curricula/?page=${page}&page_size=10`,
    (raw) => v.page(raw, '/api/v1/knowledge-curricula/', parseCurriculum),
    { signal },
  );
export const getCurriculum = (id: string, signal: AbortSignal) =>
  requestJson(
    `/api/v1/knowledge-curricula/${id}/`,
    (raw) => {
      const item = parseCurriculum(raw);
      return item.id === id ? item : v.invalid();
    },
    { signal },
  );
export const getPath = (
  selected: LearningSelection,
  curriculumId: string,
  goal: string,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/learning-paths/?analysis_id=${selected.analysis}&endpoint_index=${selected.endpoint}&curriculum_id=${curriculumId}&goal=${encodeURIComponent(goal)}`,
    (raw) => parsePath(raw, selected, curriculumId, goal),
    { signal },
  );

export function parseReview(raw: unknown, attemptId: string): AttemptReview {
  const item = v.object(raw);
  if (item.attempt_id !== attemptId) return v.invalid();
  return {
    id: v.uuid(item.id),
    attempt_id: attemptId,
    judgement: v.oneOf(item.judgement, ['revisit', 'practicing', 'understood']),
    note: v.text(item.note, 1000),
    created_at: v.date(item.created_at),
  };
}
export const listReviews = (
  attemptId: string,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/attempt-reviews/?attempt_id=${attemptId}&page=${page}&page_size=10`,
    (raw) =>
      v.page(raw, '/api/v1/attempt-reviews/', (item) =>
        parseReview(item, attemptId),
      ),
    { signal },
  );
export const submitReview = (
  body: ReviewInputRequest,
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    '/api/v1/attempt-reviews/',
    key,
    (raw) => parseReview(raw, body.attempt_id),
    body,
    signal,
  );
