import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { getCards, type LearningSelection } from './api/learning-api';
import { LearningPathPanel } from './LearningPathPanel';

export function KnowledgePanel({
  selected,
  curriculumId,
  goal,
  onPath,
}: {
  selected: LearningSelection | null;
  curriculumId: string | null;
  goal: string;
  onPath: (id: string, goal: string) => void;
}) {
  const [page, setPage] = useState(1);
  const cards = useQuery({
    queryKey: ['learning', 'cards', page],
    queryFn: ({ signal }) => getCards(page, signal),
  });
  return (
    <section className="knowledge-panel" aria-label="知识与学习">
      <h2>知识卡片与学习路径</h2>
      <p>按已发布内容学习；先修关系与自评分别保存，不据此推断已掌握。</p>
      {selected ? (
        <LearningPathPanel
          selected={selected}
          curriculumId={curriculumId}
          goal={goal}
          onSelect={onPath}
        />
      ) : (
        <section aria-label="知识先修路径">
          <h3>从先修知识开始</h3>
          <p role="note">
            先在 API
            分析选择接口，再查看当前源码适用的学习路径。全局知识卡片可直接阅读。
          </p>
        </section>
      )}
      <section aria-label="知识卡片">
        <h3>知识卡片</h3>
        <Feedback error={cards.error} />
        {cards.isPending && <p role="status">读取知识卡片…</p>}
        {cards.data?.count === 0 && <p>暂无已发布知识卡片。</p>}
        <div className="knowledge-library">
          {cards.data?.results.map((card) => (
            <article key={card.id}>
              <h4>
                {card.title} · v{card.version}
              </h4>
              <p>{card.body}</p>
              <small>{card.applicability}</small>
              <details>
                <summary>内容维护说明</summary>
                <p className="muted">{card.review_note}</p>
              </details>
            </article>
          ))}
        </div>
        {cards.data && (cards.data.next || cards.data.previous) && (
          <PageControls
            page={page}
            previous={cards.data.previous}
            next={cards.data.next}
            onPage={setPage}
          />
        )}
      </section>
    </section>
  );
}
