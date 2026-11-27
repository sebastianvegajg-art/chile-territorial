import { open } from 'node:fs/promises'
import { Readable } from 'node:stream'
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

function apiSnapshotLocal(): Plugin {
  return {
    name: 'chile-territorial-snapshot-local',
    async configureServer(server) {
      if (process.env.BACKEND_API_URL?.trim()) {
        throw new Error('Quita BACKEND_API_URL de esta terminal para iniciar la vista previa con el corte local.')
      }
      const modulo = new URL('../../netlify/functions/api.mjs', import.meta.url)
      const { default: handle }: { default: (request: Request) => Promise<Response> } = await import(modulo.href)

      server.middlewares.use(async (request, response, next) => {
        const url = new URL(request.url ?? '/', 'http://127.0.0.1')
        if (url.pathname !== '/healthz' && !url.pathname.startsWith('/api/v1/')) return next()
        const method = request.method ?? 'GET'
        const headers = new Headers()
        for (const [name, value] of Object.entries(request.headers)) {
          if (value !== undefined) headers.set(name, Array.isArray(value) ? value.join(', ') : value)
        }
        const init: RequestInit & { duplex?: 'half' } = { method, headers }
        if (method !== 'GET' && method !== 'HEAD') {
          init.body = Readable.toWeb(request) as ReadableStream<Uint8Array>
          init.duplex = 'half'
        }
        try {
          const result = await handle(new Request(url, init))
          response.writeHead(result.status, Object.fromEntries(result.headers))
          response.end(method === 'HEAD' ? undefined : Buffer.from(await result.arrayBuffer()))
        } catch (error) {
          next(error)
        }
      })
    },
  }
}

export default defineConfig(({ mode }) => {
  const local = mode === 'local-preview'
  return {
    plugins: [descargaLocal(), ...(local ? [apiSnapshotLocal()] : [])],
    server: {
      host: '127.0.0.1',
      ...(local
        ? { port: 4173, strictPort: true, open: '/#portada' }
        : { proxy: { '/api': { target: 'http://127.0.0.1:8000' } } }),
    },
    define: {
      __CT_DEMO_DEFAULT__: JSON.stringify(mode === 'demo'),
      ...(local ? { 'import.meta.env.VITE_API_BASE': '""' } : {}),
    },
  }
})
