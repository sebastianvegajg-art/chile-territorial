import { open } from 'node:fs/promises'
import { defineConfig } from 'vite'
import type { Connect, Plugin } from 'vite'

function descargaLocal(): Plugin {
  const ruta = '/descargas/Chile_Territorial_Oficial.html'
  const archivo = new URL('../../data/published/Chile_Territorial_Oficial.html', import.meta.url)
  const descarga: Connect.NextHandleFunction = async (request, response, next) => {
    if (request.url !== ruta || (request.method !== 'GET' && request.method !== 'HEAD')) return next()
    const file = await open(archivo, 'r').catch(() => null)
    if (!file) {
      response.statusCode = 404
      return response.end()
    }
    response.setHeader('Content-Type', 'text/html; charset=utf-8')
    response.setHeader('Content-Disposition', 'attachment; filename="Chile_Territorial_Oficial.html"')
    if (request.method === 'HEAD') {
      await file.close()
      return response.end()
    }
    file.createReadStream().on('error', () => response.destroy()).pipe(response)
  }
  return {
    name: 'chile-territorial-descarga-local',
    configureServer(server) {
      server.middlewares.use(descarga)
    },
    configurePreviewServer(server) {
      server.middlewares.use(descarga)
    },
  }
}

export default defineConfig(({ mode }) => ({
  plugins: [descargaLocal()],
  server: {
    host: '127.0.0.1',
    proxy: { '/api': { target: 'http://127.0.0.1:8000' } },
  },
  define: { __CT_DEMO_DEFAULT__: JSON.stringify(mode === 'demo') },
}))
