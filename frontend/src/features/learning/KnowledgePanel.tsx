import { useEffect, useRef, useState } from 'react';
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
  const [cardId, setCardId] = useState<string | null>(null);
  const body = useRef<HTMLDivElement>(null);
  const focusFrame = useRef(0);
  useEffect(() => () => cancelAnimationFrame(focusFrame.current), []);
  const cards = useQuery({
    queryKey: ['learning', 'cards', page],
    queryFn: ({ signal }) => getCards(page, signal),
  });
  const current =
    cards.data?.results.find((card) => card.id === cardId) ??
    cards.data?.results[0];
  function selectCard(id: string) {
    setCardId(id);
    cancelAnimationFrame(focusFrame.current);
    // 留出正文渲染和分页测量的两帧，再以焦点定位正文，不改变页面滚动。
    focusFrame.current = requestAnimationFrame(() => {
      focusFrame.current = requestAnimationFrame(() => {
        focusFrame.current = 0;
        const reading = body.current;
        if (reading?.dataset.cardId === id && !reading.closest('[hidden]'))
          reading.focus({ preventScroll: true });
      });
    });
  }
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
        <div className="knowledge-reading-grid">
          <nav className="knowledge-directory" aria-label="知识目录">
            <ul className="workspace-nav">
              {cards.data?.results.map((card) => (
                <li key={card.id}>
                  <button
                    type="button"
                    aria-pressed={current?.id === card.id}
                    onClick={() => selectCard(card.id)}
                  >
                    {card.title}
                    <small>版本 {card.version}</small>
                  </button>
                </li>
              ))}
            </ul>
          </nav>
          <div
            className="knowledge-library"
            ref={body}
            tabIndex={-1}
            data-card-id={current?.id}
            role="region"
            aria-label="知识正文区域"
          >
            {current && (
              <article key={current.id} aria-label="知识正文">
                <h4>
                  {current.title} · v{current.version}
                </h4>
                <p>{current.body}</p>
                <small>{current.applicability}</small>
                <details>
                  <summary>内容维护说明</summary>
                  <p className="muted">{current.review_note}</p>
                </details>
              </article>
            )}
          </div>
        </div>
        {cards.data && (cards.data.next || cards.data.previous) && (
          <PageControls
            page={page}
            previous={cards.data.previous}
            next={cards.data.next}
            onPage={(next) => {
              cancelAnimationFrame(focusFrame.current);
              focusFrame.current = 0;
              setPage(next);
            }}
          />
        )}
      </section>
    </section>
  );
}
