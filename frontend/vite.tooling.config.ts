import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../.runtime/frontend-tooling-dist',
    emptyOutDir: false,
    lib: {
      entry: fileURLToPath(
        new URL('./tooling/ToolchainProbe.tsx', import.meta.url),
      ),
      formats: ['es'],
      fileName: 'toolchain-probe',
    },
    rolldownOptions: { external: ['react', 'react-dom', 'react/jsx-runtime'] },
  },
});
