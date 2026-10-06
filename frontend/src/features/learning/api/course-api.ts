import type {
  CurriculumProgress,
  CurriculumProgressCard,
  KnowledgeCurriculum,
  PatchedCurriculumProgressInputRequest,
} from '../../../shared/api/generated/schema';
import { patchJson, requestJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import { getCard } from './learning-api';

export const courseProgressKey = (id: string, version: string) =>
  ['learning', 'course-progress', id, version] as const;

export function parseCourseProgress(
  raw: unknown,
  course: KnowledgeCurriculum,
): CurriculumProgress {
  const item = v.object(raw);
  const cards = v.list(
    item.cards,
    (raw): CurriculumProgressCard => {
      const card = v.object(raw);
      return {
        card_id: v.uuid(card.card_id),
        slug: v.text(card.slug, 80),
        version: v.text(card.version, 40),
        title: v.text(card.title, 200),
        completed: v.boolean(card.completed),
      };
    },
    100,
  );
  const result = {
    curriculum_id: v.uuid(item.curriculum_id),
    version: v.text(item.version, 40),
    completed_count: v.integer(item.completed_count, 0, 100),
    total_count: v.integer(item.total_count, 0, 100),
    cards,
  };
  if (
    result.curriculum_id !== course.id ||
    result.version !== course.version ||
    result.total_count !== course.definition.nodes.length ||
    cards.length !== result.total_count ||
    new Set(cards.map((card) => card.card_id)).size !== cards.length ||
    result.completed_count !== cards.filter((card) => card.completed).length ||
    cards.some((card, index) => {
      const node = course.definition.nodes[index];
      return card.slug !== node?.slug || card.version !== node?.card_version;
    })
  )
    return v.invalid();
  return result;
}

export const getCourseProgress = (
  course: KnowledgeCurriculum,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/knowledge-curricula/${course.id}/progress/`,
    (raw) => parseCourseProgress(raw, course),
    { signal },
  );

export const setCourseCardProgress = (
  course: KnowledgeCurriculum,
  card: CurriculumProgressCard,
  completed: boolean,
  signal: AbortSignal,
) => {
  if (
    typeof completed !== 'boolean' ||
    !course.definition.nodes.some(
      (node) => node.slug === card.slug && node.card_version === card.version,
    )
  )
    return v.invalid();
  const input: PatchedCurriculumProgressInputRequest = { completed };
  return patchJson(
    `/api/v1/knowledge-curricula/${course.id}/progress/${v.uuid(card.card_id)}/`,
    (raw) => {
      const result = parseCourseProgress(raw, course);
      return result.cards.some(
        (item) => item.card_id === card.card_id && item.completed === completed,
      )
        ? result
        : v.invalid();
    },
    input,
    signal,
  );
};

export async function getCourseCard(
  card: CurriculumProgressCard,
  signal: AbortSignal,
) {
  const result = await getCard(card.card_id, signal);
  return result.slug === card.slug && result.version === card.version
    ? result
    : v.invalid();
}
