import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './ThemeProvider';
import { WorkspacePage } from './WorkspacePage';
import { ApiError } from '../shared/api/client';
import { AppErrorBoundary } from './AppErrorBoundary';
import './global.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) =>
        count < 1 &&
        error instanceof ApiError &&
        (error.status === 0 || error.status >= 500),
    },
    mutations: { retry: false },
  },
});
const root = document.getElementById('root');
if (!root) throw new Error('页面入口缺失。');
createRoot(root, {
  onCaughtError: () => console.error('WORKSPACE_RENDER_FAILED'),
}).render(
  <StrictMode>
    <ThemeProvider>
      <AppErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <WorkspacePage />
        </QueryClientProvider>
      </AppErrorBoundary>
    </ThemeProvider>
  </StrictMode>,
);
