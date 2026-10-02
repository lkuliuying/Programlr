import { Button } from 'antd';
import { ApiError } from '../api/client';

export function Feedback({
  error,
  retry,
}: {
  error: Error | null;
  retry?: () => void;
}) {
  if (!error) return null;
  return (
    <div role="alert" className="workspace-error">
      <p>{error.message}</p>
      {error instanceof ApiError && error.requestId && (
        <small>请求标识：{error.requestId}</small>
      )}
      {retry && <Button onClick={retry}>重新查询</Button>}
    </div>
  );
}
