import { Button } from 'antd';
import { ApiError } from '../api/client';
import { ContentState } from './PagePresentation';

export function Feedback({
  error,
  retry,
}: {
  error: Error | null;
  retry?: () => void;
}) {
  if (!error) return null;
  return (
    <ContentState
      kind="error"
      action={retry && <Button onClick={retry}>重新查询</Button>}
    >
      <p>{error.message}</p>
      {error instanceof ApiError && error.requestId && (
        <small>请求标识：{error.requestId}</small>
      )}
    </ContentState>
  );
}
