import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import type { LearningSelection } from './api/learning-api';
import * as api from './api/paths-api';

const titles: Record<string, string> = {
  'create-task': '创建任务',
  'container-network': '容器网络',
  subprocess: '子进程',
  prerequisites: '先修图算法',
};
export function LearningPathPanel({
  selected,
  curriculumId,
  goal,
  onSelect,
}: {
  selected: LearningSelection;
  curriculumId: string | null;
  goal: string;
  onSelect: (id: string, goal: string) => void;
}) {
  const [page, setPage] = useState(1);
  const curricula = useQuery({
    queryKey: ['learning', 'curricula', page],
    queryFn: ({ signal }) => api.listCurricula(page, signal),
  });
  const currentId =
    curriculumId ??
    (curricula.data?.count === 1 ? curricula.data.results[0]?.id : null);
  const curriculum = useQuery({
    queryKey: ['learning', 'curriculum', currentId],
    queryFn: ({ signal }) => api.getCurriculum(currentId!, signal),
    enabled: !!currentId,
  });
  const path = useQuery({
    queryKey: ['learning', 'path', selected, currentId, goal],
    queryFn: ({ signal }) => api.getPath(selected, currentId!, goal, signal),
    enabled: !!currentId,
  });
  return (
    <section aria-label="知识先修路径">
      <h3>从先修知识开始</h3>
      <p>路径来自已发布课程，作答或自评不会自动改变先修关系。</p>
      <Feedback error={curricula.error ?? curriculum.error ?? path.error} />
      <label>
        课程版本
        <select
          value={currentId ?? ''}
          onChange={(event) => {
            if (event.target.value) onSelect(event.target.value, 'create-task');
          }}
        >
          <option value="">请选择课程版本</option>
          {curricula.data?.results.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title} · {item.version}
            </option>
          ))}
          {curriculum.data &&
            !curricula.data?.results.some(
              (item) => item.id === curriculum.data.id,
            ) && (
              <option value={curriculum.data.id}>
                {curriculum.data.title} · {curriculum.data.version}
              </option>
            )}
        </select>
      </label>
      {curricula.data && (
        <PageControls
          page={page}
          previous={curricula.data.previous}
          next={curricula.data.next}
          onPage={setPage}
        />
      )}
      {curriculum.data && (
        <label>
          学习目标
          <select
            value={goal}
            onChange={(event) =>
              onSelect(curriculum.data!.id, event.target.value)
            }
          >
            {Object.keys(curriculum.data.definition.goals).map((id) => (
              <option key={id} value={id}>
                {titles[id] ?? id}
              </option>
            ))}
          </select>
        </label>
      )}
      {path.isFetching && <p role="status">核对先修关系…</p>}
      {path.data && (
        <>
          <p role="note">{path.data.applicability_reason}</p>
          <ol>
            {path.data.steps.map((card) => (
              <li key={card.id}>
                <h4>{card.title}</h4>
                <p>{card.body}</p>
                <small>
                  卡片 {card.version} · 先修：
                  {path.data.curriculum.definition.edges
                    .filter((edge) => edge.dependent === card.slug)
                    .map(
                      (edge) =>
                        path.data.steps.find(
                          (item) => item.slug === edge.prerequisite,
                        )?.title ?? edge.prerequisite,
                    )
                    .join('、') || '无'}
                </small>
              </li>
            ))}
          </ol>
          <details>
            <summary>查看知识图与维护依据</summary>
            <ul>
              {path.data.curriculum.definition.edges.map((edge) => (
                <li key={`${edge.prerequisite}/${edge.dependent}`}>
                  {edge.prerequisite} → {edge.dependent}
                </li>
              ))}
            </ul>
            <p>{path.data.curriculum.definition.review_note}</p>
          </details>
        </>
      )}
      {curricula.data?.count === 0 && <p>暂无已发布知识课程。</p>}
    </section>
  );
}
