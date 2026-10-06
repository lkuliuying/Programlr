import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['tooling/test-dom-setup.ts'],
    include: ['tooling/**/*.test.tsx', 'src/**/*.test.ts', 'src/**/*.test.tsx'],
    maxWorkers: 1,
    testTimeout: 60000,
  },
});
