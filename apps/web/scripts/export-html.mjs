import { readFile, rename, rm, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const [target, endpoint = 'http://127.0.0.1:8000/api/v1', cut] = process.argv.slice(2)
if (!target) throw new Error('Indica la ruta de salida del HTML.')

async function request(path) {
  const response = await fetch(endpoint.replace(/\/$/, '') + path, { signal: AbortSignal.timeout(30_000) })
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`)
  return response.json()
}

const [publications, territories] = await Promise.all([request('/publicaciones'), request('/territorios')])
const publication = publications.find(item => item.estado === 'aprobada' && (!cut || item.id === cut))
if (!publication) throw new Error('La API no ofrece el corte oficial solicitado.')

async function readSeries(metrica, valoracion) {
  const parameters = new URLSearchParams({
    anio_desde: '2013', anio_hasta: String(new Date().getFullYear()),
    metrica, valoracion, publicacion: publication.id, limite: '500',
  })
  const rows = []
  for (let page = 1; ; page++) {
    parameters.set('pagina', String(page))
    const result = await request(`/pib?${parameters}`)
    if (result.publicacion !== publication.id || result.datos.some(row => row.publicacion !== publication.id || row.clase === 'prueba')) {
      throw new Error('La consulta devolvió un corte distinto o datos de prueba.')
    }
    rows.push(...result.datos)
    if (rows.length === result.total) return rows
    if (!result.datos.length || rows.length > result.total) throw new Error('Paginación inconsistente.')
  }
}

const rows = (await Promise.all([
  readSeries('nivel', 'real'), readSeries('nivel', 'nominal'),
  readSeries('crecimiento', 'real'), readSeries('participacion', 'nominal'),
])).flat()
if (!rows.some(row => row.clase === 'oficial' && row.metrica === 'nivel' && row.valor !== null)) {
  throw new Error('No se encontraron valores oficiales para exportar.')
}

const provenance = Object.create(null)
for (let index = 0; index < rows.length; index += 8) {
  await Promise.all(rows.slice(index, index + 8).map(async ({ id }) => {
    const entry = await request(`/observaciones/${encodeURIComponent(id)}/procedencia`)
    if (entry.publicacion !== publication.id || entry.observacion !== id) throw new Error('Procedencia inconsistente.')
    provenance[id] = entry
  }))
}

const dist = new URL('../dist/', import.meta.url)
const index = await readFile(new URL('index.html', dist), 'utf8')
const js = index.match(/<script type="module"[^>]*src="\/?([^"]+)"[^>]*><\/script>/)
const css = index.match(/<link rel="stylesheet"[^>]*href="\/?([^"]+)"[^>]*>/)
if (!js || !css) throw new Error('Ejecuta npm run build antes de exportar el HTML.')
const [code, styles] = await Promise.all([
  readFile(new URL(js[1], dist), 'utf8'), readFile(new URL(css[1], dist), 'utf8'),
])
const snapshot = JSON.stringify({ territories, publication, rows, provenance }).replaceAll('<', '\\u003c')
const html = index
  .replace(js[0], '')
  .replace(css[0], () => `<style>${styles}</style>`)
  .replace('</body>', () => `<script type="application/json" id="ct-snapshot">${snapshot}</script>
<script type="module">${code.replace(/<\/script/gi, '<\\/script')}</script>
</body>`)
const output = resolve(target)
const temporary = `${output}.tmp-${process.pid}`
try {
  await writeFile(temporary, html, { flag: 'wx' })
  await rename(temporary, output)
} finally {
  await rm(temporary, { force: true })
}
console.log(`${publication.id}: ${rows.length} observaciones incluidas en ${output}`)
