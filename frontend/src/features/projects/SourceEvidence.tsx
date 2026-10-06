import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { SourceFile, SourceRef } from '../../shared/api/generated/schema';
import { requestJson } from '../../shared/api/client';
import * as v from '../../shared/api/validation';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';

export function SourceEvidence({
  file,
  analysisId,
  scanId,
  onSource,
}: {
  file: SourceFile;
  analysisId?: string | null;
  scanId?: string | null;
  onSource: (reference: SourceRef) => void;
}) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const path = `/api/v1/snapshots/${file.snapshot_id}/files/${file.id}/evidence/`;
  const parameters = new URLSearchParams({
    page: String(page),
    page_size: '20',
  });
  if (analysisId) parameters.set('analysis_id', analysisId);
  // 选择分析时由服务端使用其绑定扫描，不混入快照的较新扫描。
  else if (scanId) parameters.set('scan_id', scanId);
  const query = useQuery({
    queryKey: [
      'projects',
      'source-evidence',
      file.snapshot_id,
      file.id,
      analysisId,
      scanId,
      page,
    ],
    enabled: !!analysisId || !!scanId,
    queryFn: ({ signal }) =>
      requestJson(
        path + '?' + parameters,
        (raw) => {
          const item = v.object(raw);
          v.nullable(item.scan_id, v.uuid);
          if (
            v.uuid(item.snapshot_id) !== file.snapshot_id ||
            v.uuid(item.file_id) !== file.id ||
            v.nullable(item.analysis_id, v.uuid) !== (analysisId ?? null) ||
            (!analysisId &&
              v.nullable(item.scan_id, v.uuid) !== (scanId ?? null))
          )
            return v.invalid();
          v.oneOf(item.scope, ['persisted_source_evidence']);
          return v.page(
            item,
            path,
            (raw) => {
              const value = v.object(raw);
              const reference = v.sourceRef(value.source_ref, file.snapshot_id);
              if (
                reference.file_path !== file.file_path ||
                reference.end_line > file.line_count
              )
                return v.invalid();
              return {
                id: v.text(value.id, 64),
                kind: v.oneOf(value.kind, [
                  'interface',
                  'frontend',
                  'relation',
                  'knowledge',
                ]),
                label: v.text(value.label),
                source_ref: reference,
              };
            },
            ['scan_id'],
          );
        },
        { signal },
      ),
  });
  return (
    <section className="source-evidence" aria-label="相关源码依据">
      <button
        className="source-evidence-toggle"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        相关源码依据{query.data ? `（${query.data.count}）` : ''}
        <span>{open ? '收起' : '展开'}</span>
      </button>
      {open && (
        <div className="source-evidence-body">
          <p>仅包含所选分析与扫描已保存的源码事实，不代表完整调用索引。</p>
          <Feedback error={query.error} retry={() => void query.refetch()} />
          {!analysisId && !scanId ? (
            <p>尚无可用识别结果，可先阅读源码。</p>
          ) : query.isPending ? (
            <p role="status">正在读取源码依据…</p>
          ) : null}
          {query.data && (
            <>
              <ul>
                {query.data.results.map((item) => (
                  <li key={item.id}>
                    <span>
                      {
                        {
                          interface: '接口',
                          frontend: '前端来源',
                          relation: '关系',
                          knowledge: '知识',
                        }[item.kind]
                      }
                    </span>
                    <button onClick={() => onSource(item.source_ref)}>
                      {item.label}
                      <small>
                        第 {item.source_ref.start_line}–
                        {item.source_ref.end_line} 行
                      </small>
                    </button>
                  </li>
                ))}
              </ul>
              {!query.data.count && <p>当前文件没有已记录的相关源码依据。</p>}
              <PageControls page={page} {...query.data} onPage={setPage} />
            </>
          )}
        </div>
      )}
    </section>
  );
}
