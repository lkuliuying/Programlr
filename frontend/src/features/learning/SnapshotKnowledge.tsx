import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from 'antd';
import type {
  MatchedKnowledgeCard,
  SourceRef,
} from '../../shared/api/generated/schema';
import { requestJson } from '../../shared/api/client';
import * as v from '../../shared/api/validation';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { parseCard } from './api/learning-api';

function parseMatch(raw: unknown, snapshot: string): MatchedKnowledgeCard {
  const item = v.object(raw);
  const result = {
    concept_key: v.text(item.concept_key),
    mapped: v.boolean(item.mapped),
    card: v.nullable(item.card, parseCard),
    hit_count: v.integer(item.hit_count, 1),
    hits: v.list(
      item.hits,
      (raw) => {
        const hit = v.object(raw);
        return {
          reason: v.text(hit.reason),
          source_ref: v.sourceRef(hit.source_ref, snapshot),
        };
      },
      3,
    ),
    package: v.nullable(item.package, (raw) => {
      const pack = v.object(raw);
      return {
        name: v.text(pack.name),
        kind: v.oneOf(pack.kind, ['local', 'stdlib', 'third_party', 'unknown']),
        distribution: v.nullable(pack.distribution, (value) => v.text(value)),
      };
    }),
  };
  if (
    result.mapped !== (result.card !== null) ||
    result.hits.length > result.hit_count
  )
    return v.invalid();
  return result;
}
export function SnapshotKnowledge({
  snapshotId,
  scanId,
  filePath,
  analysisId,
  endpoint,
  onSource,
  onRescan,
}: {
  snapshotId: string;
  scanId: string | null;
  filePath: string | null;
  analysisId: string | null;
  endpoint: number | null;
  onSource: (source: SourceRef) => void;
  onRescan: () => void;
}) {
  const [scope, setScope] = useState<'snapshot' | 'file' | 'interface'>(
    'snapshot',
  );
  const [page, setPage] = useState(1),
    [selected, setSelected] = useState<string | null>(null),
    [hitPage, setHitPage] = useState(1);
  const effective =
    (scope === 'file' && !filePath) ||
    (scope === 'interface' && (!analysisId || endpoint === null))
      ? 'snapshot'
      : scope;
  const query = new URLSearchParams({ page: String(page), page_size: '20' });
  if (scanId && effective !== 'interface') query.set('scan_id', scanId);
  if (effective === 'file') query.set('file_path', filePath!);
  if (effective === 'interface') {
    query.set('analysis_id', analysisId!);
    query.set('endpoint_index', String(endpoint));
  }
  const path = `/api/v1/snapshots/${snapshotId}/knowledge-cards/`;
  const cards = useQuery({
    queryKey: ['knowledge', snapshotId, scanId, query.toString()],
    queryFn: ({ signal }) =>
      requestJson(
        path + '?' + query,
        (raw) => {
          const item = v.object(raw);
          return {
            ...v.page(item, path, (raw) => parseMatch(raw, snapshotId), [
              'scan_id',
              'file_path',
            ]),
            scan_id: v.uuid(item.scan_id),
            rule_version: v.text(item.rule_version),
            coverage: (() => {
              const coverage = v.object(item.coverage);
              return {
                parsed_files: v.integer(coverage.parsed_files),
                python_files: v.integer(coverage.python_files),
                syntax_failed_files: v.integer(coverage.syntax_failed_files),
                complete: v.boolean(coverage.complete),
                truncated: v.boolean(coverage.truncated),
              };
            })(),
            diagnostics: v.list(item.diagnostics, v.object),
          };
        },
        { signal },
      ),
    enabled: !!scanId,
  });
  const current = cards.data?.results.find(
    (item) => item.concept_key === selected,
  );
  const declarations = useQuery({
    queryKey: ['knowledge', snapshotId, cards.data?.scan_id, 'declarations'],
    queryFn: ({ signal }) =>
      requestJson(
        `/api/v1/source-scans/${cards.data!.scan_id}/`,
        (raw) => {
          const scan = v.object(raw);
          if (
            v.uuid(scan.id) !== cards.data!.scan_id ||
            v.uuid(scan.snapshot_id) !== snapshotId
          )
            return v.invalid();
          return v.list(
            v.object(scan.knowledge).declarations,
            (raw) => {
              const declaration = v.object(raw);
              return {
                distribution: v.text(declaration.distribution, 200),
                specifier: v.text(declaration.specifier),
                conditional: v.boolean(declaration.conditional),
                optional: v.boolean(declaration.optional),
                source_ref: v.sourceRef(declaration.source_ref, snapshotId),
              };
            },
            2000,
          );
        },
        { signal },
      ),
    enabled: !!cards.data?.scan_id,
  });
  const hitsPath = `/api/v1/snapshots/${snapshotId}/knowledge-hits/`;
  const hitQuery = new URLSearchParams(query);
  hitQuery.set('page', String(hitPage));
  if (selected) hitQuery.set('concept_key', selected);
  const hits = useQuery({
    queryKey: ['knowledge', snapshotId, 'hits', hitQuery.toString()],
    queryFn: ({ signal }) =>
      requestJson(
        hitsPath + '?' + hitQuery,
        (raw) =>
          v.page(
            raw,
            hitsPath,
            (raw) => {
              const item = v.object(raw);
              return {
                concept_key: v.text(item.concept_key),
                rule_id: v.text(item.rule_id),
                source_ref: v.sourceRef(item.source_ref, snapshotId),
              };
            },
            ['concept_key', 'scan_id', 'file_path'],
          ),
        { signal },
      ),
    enabled: !!scanId && !!current,
  });
  return (
    <section className="snapshot-knowledge" aria-label="源码知识卡片">
      <h2>源码知识</h2>
      <p>卡片来自版本化规则内容；每项均展示实际源码命中。未知导入只列事实。</p>
      <div className="mainline-choice">
        <label>
          知识范围
          <select
            value={effective}
            onChange={(event) => {
              setScope(event.target.value as typeof scope);
              setPage(1);
              setSelected(null);
              setHitPage(1);
            }}
          >
            <option value="snapshot">整个快照</option>
            <option value="file" disabled={!filePath}>
              当前文件
            </option>
            <option
              value="interface"
              disabled={!analysisId || endpoint === null}
            >
              当前接口
            </option>
          </select>
        </label>
        <Button onClick={onRescan}>重新识别知识</Button>
      </div>
      {!scanId && (
        <p>
          此历史快照尚无源码扫描结果。请显式重新识别，旧分析结果不会自动回填。
        </p>
      )}
      <Feedback error={cards.error} retry={() => void cards.refetch()} />
      {scanId && cards.isPending && <p role="status">读取知识命中…</p>}
      <div className="knowledge-layout">
        <div className="knowledge-directory">
          {cards.data && (
            <>
              <p className="mainline-help">
                规则 {cards.data.rule_version} · {cards.data.count} 项匹配
                {' · '}已解析 {cards.data.coverage.parsed_files}/
                {cards.data.coverage.python_files} 个 Python 文件
              </p>
              {(!cards.data.coverage.complete ||
                cards.data.coverage.truncated) && (
                <p role="status">
                  识别范围有限
                  {cards.data.coverage.truncated ? '，结果已截断' : ''}；
                  {cards.data.coverage.syntax_failed_files}{' '}
                  个文件无法解析。请查看诊断。
                </p>
              )}
              <ul className="knowledge-matches">
                {cards.data.results.map((item) => (
                  <li key={item.concept_key}>
                    <button
                      aria-expanded={selected === item.concept_key}
                      onClick={() => {
                        setSelected(
                          item.concept_key === selected
                            ? null
                            : item.concept_key,
                        );
                        setHitPage(1);
                      }}
                    >
                      <strong>
                        {item.card?.title ??
                          item.package?.name ??
                          item.concept_key}
                      </strong>
                      <span>
                        {item.card ? `版本 ${item.card.version}` : '未映射'} ·{' '}
                        {item.hit_count} 处命中
                      </span>
                    </button>
                    {item.package && (
                      <small>
                        {{
                          local: '本地模块',
                          stdlib: '标准库',
                          third_party: '已知第三方包',
                          unknown: '未知导入',
                        }[item.package.kind] ?? item.package.kind}
                      </small>
                    )}
                    {item.hits.map((hit, i) => (
                      <div className="knowledge-hit" key={i}>
                        <code>{hit.reason}</code>
                        <button onClick={() => onSource(hit.source_ref)}>
                          {hit.source_ref.file_path}:{hit.source_ref.start_line}
                        </button>
                      </div>
                    ))}
                  </li>
                ))}
              </ul>
              {!cards.data.count && <p>当前范围没有规则命中。</p>}
              <PageControls
                page={page}
                {...cards.data}
                onPage={(next) => {
                  setPage(next);
                  setSelected(null);
                }}
              />
              {cards.data.diagnostics.length > 0 && (
                <details>
                  <summary>识别诊断（{cards.data.diagnostics.length}）</summary>
                  {cards.data.diagnostics.map((item, i) => (
                    <p key={i}>
                      {typeof item.message === 'string'
                        ? item.message
                        : String(item.code ?? '识别范围有限')}
                    </p>
                  ))}
                </details>
              )}
            </>
          )}
        </div>
        <div className="knowledge-reading">
          {!current && (
            <div className="content-state">
              从左侧选择一个知识点，阅读正文和源码依据。
            </div>
          )}
          {current && (
            <article className="surface knowledge-card-detail">
              <h3>
                {current.card?.title ??
                  current.package?.name ??
                  current.concept_key}
              </h3>
              {current.card ? (
                <>
                  <p className="knowledge-body">{current.card.body}</p>
                  <p>适用范围：{current.card.applicability}</p>
                  <small>{current.card.review_note}</small>
                </>
              ) : (
                <p>
                  当前导入没有可信卡片映射。这里只保留实际 import
                  和源码位置，未生成知识正文。
                </p>
              )}
              <h4>全部命中位置</h4>
              <Feedback error={hits.error} />
              {hits.data?.results.map((hit, index) => (
                <p key={index}>
                  <code>{hit.rule_id}</code>
                  <button onClick={() => onSource(hit.source_ref)}>
                    {hit.source_ref.file_path}:{hit.source_ref.start_line}–
                    {hit.source_ref.end_line}
                  </button>
                </p>
              ))}
              {hits.data && (
                <PageControls
                  page={hitPage}
                  {...hits.data}
                  onPage={setHitPage}
                />
              )}
            </article>
          )}
        </div>
      </div>
      <Feedback
        error={declarations.error}
        retry={() => void declarations.refetch()}
      />
      {!!declarations.data?.length && (
        <details className="dependency-declarations">
          <summary>依赖声明事实（{declarations.data.length}）</summary>
          <p>
            来自受控声明文件，仅表示声明；未安装或查询运行环境。外部地址已脱敏。
          </p>
          {declarations.data.map((declaration, index) => (
            <p key={index}>
              <code>
                {declaration.distribution}
                {declaration.specifier || '（未指定版本）'}
              </code>
              {declaration.conditional && ' · 有条件'}
              {declaration.optional && ' · 可选'}{' '}
              <button onClick={() => onSource(declaration.source_ref)}>
                {declaration.source_ref.file_path}:
                {declaration.source_ref.start_line}
              </button>
            </p>
          ))}
        </details>
      )}
    </section>
  );
}
