import { useQuery } from '@tanstack/react-query';
import { Icon } from '../../shared/components/Icon';
import { Feedback } from '../../shared/components/Feedback';
import { getCards } from './api/learning-api';
export function KnowledgeSummary({
  onLearning,
  onLab,
  enabled = true,
}: {
  onLearning: () => void;
  onLab: () => void;
  enabled?: boolean;
}) {
  const query = useQuery({
    queryKey: ['learning', 'cards', 1],
    queryFn: ({ signal }) => getCards(1, signal),
    enabled,
  });
  return (
    <section className="surface knowledge-summary" aria-label="知识与练习总览">
      <div className="panel-title">
        <Icon name="learning" />
        <h2>知识卡片与学习实验</h2>
        <button className="text-button" onClick={onLearning}>
          查看学习
        </button>
      </div>
      <div className="panel-body">
        <Feedback error={query.error} />
        <div className="knowledge-cards">
          {query.data?.results.slice(0, 3).map((card, index) => (
            <button
              key={card.id}
              className={`knowledge-card card-${index}`}
              onClick={onLearning}
            >
              <small>知识卡片 · v{card.version}</small>
              <strong>{card.title}</strong>
              <span>{card.applicability}</span>
            </button>
          ))}
        </div>
        {(!enabled || query.data?.count === 0) && (
          <p className="muted">选择接口后查看适用内容、固定练习和学习路径。</p>
        )}
        {query.isPending && enabled && <p role="status">读取知识卡片…</p>}
        <div className="learning-shortcuts">
          <button onClick={onLearning}>
            <Icon name="learning" />
            固定练习与复习
          </button>
          <button onClick={onLab}>
            <Icon name="labs" />
            预测并运行内置实验
          </button>
        </div>
      </div>
    </section>
  );
}
