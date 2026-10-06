import type {
  ContextPreview,
  Explanation,
  ExplanationClaim,
  ContextConsent,
} from '../../../shared/api/generated/schema';
import { requestJson, submitJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import { parseJob } from '../../jobs';

export type Selection = {
  snapshot: string;
  analysis: string;
  endpoint: number;
};
function binding(item: Record<string, unknown>, selected: Selection) {
  if (
    item.snapshot_id !== selected.snapshot ||
    item.analysis_id !== selected.analysis ||
    item.endpoint_index !== selected.endpoint
  )
    v.invalid();
  return {
    snapshot_id: selected.snapshot,
    analysis_id: selected.analysis,
    endpoint_index: selected.endpoint,
  };
}
export function parsePreview(
  value: unknown,
  selected: Selection,
): ContextPreview {
  const item = v.object(value),
    config = v.object(item.configuration);
  return {
    ...binding(item, selected),
    id: v.uuid(item.id),
    payload_digest: v.text(item.payload_digest, 64),
    created_at: v.date(item.created_at),
    template_version: v.text(item.template_version),
    configuration: {
      base_url: v.text(config.base_url),
      model: v.text(config.model),
      ...(config.timeout === undefined
        ? {}
        : { timeout: v.integer(config.timeout, 1) }),
      ...(config.context_bytes === undefined
        ? {}
        : { context_bytes: v.integer(config.context_bytes, 1) }),
      ...(config.output_tokens === undefined
        ? {}
        : { output_tokens: v.integer(config.output_tokens, 1) }),
      ...(config.token_field === undefined
        ? {}
        : { token_field: v.text(config.token_field) }),
    },
    context_bytes: v.integer(item.context_bytes, 1),
    messages: v.list(
      item.messages,
      (value) => {
        const message = v.object(value);
        return {
          role: v.oneOf(message.role, ['system', 'user']),
          content: v.text(message.content, Infinity),
        };
      },
      2,
    ),
    snippets: v.list(
      item.snippets,
      (value) => {
        const snippet = v.object(value);
        return {
          id: v.text(snippet.id, 64),
          source_ref: v.sourceRef(snippet.source_ref, selected.snapshot),
          sha256: v.text(snippet.sha256, 64),
          content: v.text(snippet.content, Infinity),
        };
      },
      300,
    ),
    excluded_snippets: v.list(
      item.excluded_snippets,
      (value) => v.text(value, 64),
      50,
    ),
    nodes: v.list(
      item.nodes,
      (value) => {
        const node = v.object(value);
        return {
          id: v.uuid(node.id),
          name: v.text(node.name),
          kind: v.text(node.kind),
        };
      },
      50,
    ),
    omissions: v.list(item.omissions, (value) => v.text(value)),
    knowledge_cards: v.list(
      item.knowledge_cards ?? [],
      (raw) => {
        const card = v.object(raw);
        const digest = v.text(card.content_digest, 64);
        if (!/^[0-9a-f]{64}$/.test(digest)) return v.invalid();
        return {
          card_id: v.uuid(card.card_id),
          slug: v.text(card.slug),
          version: v.text(card.version),
          content_digest: digest,
          title: v.text(card.title),
          body: v.text(card.body, Infinity),
          source_refs: v.list(
            card.source_refs,
            (ref) => v.sourceRef(ref, selected.snapshot),
            100,
          ),
        };
      },
      100,
    ),
  };
}
export function parseExplanation(
  value: unknown,
  selected: Selection,
): Explanation {
  const item = v.object(value),
    content = v.object(item.content);
  const claims = (value: unknown): ExplanationClaim[] =>
    v.list(
      value,
      (raw) => {
        const claim = v.object(raw);
        return {
          kind: v.oneOf(claim.kind, [
            'source_fact',
            'static_inference',
            'general_principle',
          ]),
          text: v.text(claim.text, 4000),
          source_refs: v.list(
            claim.source_refs,
            (ref) => v.sourceRef(ref, selected.snapshot),
            8,
          ),
        };
      },
      12,
    );
  return {
    ...binding(item, selected),
    id: v.uuid(item.id),
    job_id: v.uuid(item.job_id),
    preview_id: v.uuid(item.preview_id),
    model: v.text(item.model, 200),
    template_version: v.text(item.template_version),
    created_at: v.date(item.created_at),
    usage: v.nullable(item.usage, (raw) => {
      const usage = v.object(raw);
      return {
        prompt_tokens: v.integer(usage.prompt_tokens),
        completion_tokens: v.integer(usage.completion_tokens),
        total_tokens: v.integer(usage.total_tokens),
      };
    }),
    content: {
      purpose: claims(content.purpose),
      evidence: claims(content.evidence),
      mechanism: claims(content.mechanism),
      knowledge: claims(content.knowledge),
      verification: claims(content.verification),
    },
  };
}
export const getPreview = (
  id: string,
  selected: Selection,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/context-previews/${id}/`,
    (raw) => {
      const value = parsePreview(raw, selected);
      return value.id === id ? value : v.invalid();
    },
    { signal },
  );
export const createPreview = (
  selected: Selection,
  input: { nodes: string[] | null; excluded: string[] },
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    '/api/v1/context-previews/',
    key,
    (raw) => parsePreview(raw, selected),
    {
      analysis_id: selected.analysis,
      endpoint_index: selected.endpoint,
      ...(input.nodes ? { node_ids: input.nodes } : {}),
      excluded_snippets: input.excluded,
    },
    signal,
  );
export const confirmPreview = (id: string, key: string, signal: AbortSignal) =>
  submitJson(
    `/api/v1/context-previews/${id}/consents/`,
    key,
    (raw): ContextConsent => {
      const item = v.object(raw);
      if (item.preview_id !== id) return v.invalid();
      return {
        id: v.uuid(item.id),
        preview_id: id,
        created_at: v.date(item.created_at),
      };
    },
    { accepted: true },
    signal,
  );
export const generateExplanation = (
  consent: string,
  previous: string | null,
  key: string,
  signal: AbortSignal,
) =>
  submitJson(
    previous ? `/api/v1/jobs/${previous}/retries/` : '/api/v1/explanations/',
    key,
    parseJob,
    { consent_id: consent },
    signal,
  );
export const getExplanation = (
  id: string,
  selected: Selection,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/explanations/${id}/`,
    (raw) => {
      const item = parseExplanation(raw, selected);
      return item.id === id ? item : v.invalid();
    },
    { signal },
  );
export const explanationHistory = (
  selected: Selection,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/explanations/?snapshot_id=${selected.snapshot}&analysis_id=${selected.analysis}&endpoint_index=${selected.endpoint}&page=${page}&page_size=10`,
    (raw) =>
      v.page(raw, '/api/v1/explanations/', (item) =>
        parseExplanation(item, selected),
      ),
    { signal },
  );
