import { Button } from 'antd';

export function PageControls({
  page,
  previous,
  next,
  onPage,
}: {
  page: number;
  previous: string | null;
  next: string | null;
  onPage: (page: number) => void;
}) {
  return (
    <nav className="workspace-pagination" aria-label="分页">
      <Button
        size="small"
        disabled={!previous}
        onClick={() => onPage(page - 1)}
      >
        上一页
      </Button>
      <span>第 {page} 页</span>
      <Button size="small" disabled={!next} onClick={() => onPage(page + 1)}>
        下一页
      </Button>
    </nav>
  );
}
