import { defineConfig } from 'vite'

export default defineConfig(({ mode }) => ({
  server: {
    host: '127.0.0.1',
    proxy: { '/api': { target: 'http://127.0.0.1:8000' } },
  },
  define: { __CT_DEMO_DEFAULT__: JSON.stringify(mode === 'demo') },
}))
