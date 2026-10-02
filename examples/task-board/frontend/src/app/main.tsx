import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TaskBoard } from '../features/tasks/TaskBoard';
import './global.css';

const client = new QueryClient({
  defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
});
const root = document.getElementById('root');
if (!root) throw new Error('页面缺少应用容器。');
createRoot(root).render(
  <StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#28594a',
          borderRadius: 5,
          fontFamily: '"Microsoft YaHei", sans-serif',
          controlHeight: 42,
        },
      }}
    >
      <QueryClientProvider client={client}>
        <TaskBoard />
      </QueryClientProvider>
    </ConfigProvider>
  </StrictMode>,
);
