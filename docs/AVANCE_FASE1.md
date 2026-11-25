# Avance de la primera fase

## Ola 3 — Mercado laboral (INE ENE vía BCCh SI3), tejido empresarial SII y Matriz de Dependencia Estatal completa (25 de noviembre de 2026)

Se cerró el **Plano (c)** de la **Matriz de Dependencia Estatal** y se incorporaron indicadores laborales, de productividad y de tejido empresarial comunal usando exclusivamente fuentes oficiales con `Decimal(34)`:

- **Extractor reproducible INE ENE + SII (`pipelines/laboral/mercado_laboral_live.py`)**: descarga viva y reproducción bit-a-bit con SHA-256 de **35 series INE ENE** desde la API oficial del Banco Central (`F049.OCU.PMT.INE9.*.M` y `F049.DES.TAS.INE9.*.M` para **Chile y las 16 regiones**, `2013–septiembre 2026`, más ocupación nacional en Administración Pública `F049.OCU.PMT.INE4.39B.M`) y **3 archivos oficiales SII (`PUB_REG.xlsb`, `PUB_REG_RUBR.xlsb`, `PUB_COMU.xlsb`, `2013–2025`)** con manejo estricto del secreto estadístico (`*` → `null`, nunca `0`) y denominador regional sin supresión.
- **Hallazgos verificados en Aysén 2025**: **59.525 ocupados** y **`4,19%`** de desocupación (INE ENE), **productividad laboral real de `$24.032.408 CLP/ocupado` (`#4` de Chile)**; en registros SII por domicilio tributario del empleador, **13.453 empresas** y **23.297,24 trabajadores dependientes ponderados**, donde el **Rubro `O` (Administración Pública y Defensa)** concentra el **`20,09%`** del empleo dependiente y el **`42,62%`** de la masa salarial formal en UF, más cobertura completa de las **10/10 comunas de Aysén** (`2013–2025`).
- **API, Frontend y Snapshot Público**: nuevo endpoint `GET /api/v1/laboral/resumen`, actualización de `GET /api/v1/cruces/resumen` (Plano b conectado a SINIM 10/10 comunas y Plano c activo con separación metodológica ENE vs SII) y visualización de la Matriz de 3 Planos + tabla comunal SII en `LaboratorioView.tsx` (`#laboratorio`).

## Ola 2 — Proyectos ampliados 2021–2026: DIPRES Subtítulo 31 (BIP) + MOP DGOP sin doble conteo (25 de noviembre de 2026)

Se amplió la pestaña **Proyectos** y la tarjeta **Arrastre** de **Resumen** más allá de los contratos MOP DGOP integrando las **Iniciativas de Inversión Pública (Subtítulo 31 / Código BIP)** desde DIPRES CKAN (`datos.gob.cl`, sin credenciales y con aritmética `Decimal(34)`):

- **Extractor oficial DIPRES Subt. 31 / BIP (`pipelines/inversion/dipres_bip_live.py`)**: descarga viva y reproducción bit-a-bit con SHA-256 para **6 años (`2021–2026`, corte septiembre 2026)** filtrando estrictamente `Región Destino = 11` y moneda CLP (`1.273` iniciativas-año en Aysén: `220` en 2026 por `$199.310,3 MM` identificados, `216` en 2025 por `$156.504,2 MM`, cubriendo **Gobierno Regional de Aysén FNDR** con `103` iniciativas, **MOP DGOP**, **SERVIU Aysén**, **Servicio de Salud Aysén**, **SLEP Aysén**, **Poder Judicial**, **Justicia** y **Transportes** en las **10 comunas**).
- **Cero doble conteo y separación estricta de Pregunta 1 vs Pregunta 2 (`apps/api/aysen_piloto.py`, `netlify/functions/api.mjs`)**: en 2026 los `63` Códigos BIP de MOP que ya están en los contratos MOP DGOP se enriquecen sin duplicarse; las iniciativas DIPRES BIP no inventan `fecha_contratacion` (protegiendo la **Pregunta 1** de contratos firmados antes de la administración vigente) y habilitan la **Pregunta 2** (arrastre presupuestario plurianual verificable `2022–2026`) para GORE Aysén FNDR, SERVIU, Salud, SLEP y años históricos `2022–2025` (incluyendo la tarjeta de Arrastre en **Resumen 2025**).

## Ola 1 — Presupuestos completos 2018–2026 (SINIM 19 variables + DIPRES histórico, 25 de noviembre de 2026)

Se cerraron las brechas presupuestarias históricas de las tres billeteras en Aysén y la referencia nacional usando exclusivamente fuentes oficiales públicas (sin credenciales adicionales y con `Decimal(34)`):

- **SINIM Completo 2018–2025 (`pipelines/fiscal/sinim_datos_live.py`)**: extracción en vivo (y reproducción bit-a-bit con SHA-256) vía `datos.sinim.gov.cl` para las **10/10 comunas de Aysén** en **8 años (`2018–2025`)** y **19 variables oficiales** (`M$` → millones CLP): Presupuesto Inicial (`BPIGM`), Presupuesto Vigente (`BPVGM`), Tasa de Ejecución, Gasto Total Devengado (`IADM11`), Gastos Corrientes oficiales (`IADM51`), Inversión Municipal oficial (`IADM22`), Personal Subt. 21 (`Planta/Contrata/Honorarios/Programas Comunitarios`), Bienes y Servicios Subt. 22, Transferencias Corrientes Subt. 24 (`IADM60`), y **Área de Gestión Interna (`BGMAGINT`)** separada de Servicios Comunitarios (`BGMASCOM`) y Programas Sociales (`BGMAPSOC`). Ejemplo **Municipalidad de Aysén (`11201`) 2025**: Inicial `$15.734,3 MM$`, Vigente `$20.152,3 MM$`, Devengado `$13.991,9 MM$` (`69,43%`), Gasto Corriente `85,21%`, Inversión Municipal `8,73%`, Área de Gestión Interna `61,42%`.
- **DIPRES Histórico 2018–2026 (`pipelines/fiscal/dipres_ckan.py`)**: soporte de fallback automático al CSV oficial directo cuando el Datastore CKAN está vacío (`2018–2023`) y trazabilidad institucional del GORE Aysén en sus tres ubicaciones históricas: **Partida 05** (`2018–2021`), **Partida 05 Cap. 34 Sub-Asignación 011** (`2022`: `$62.640,36 MM$`, `10,15%` corriente / `89,85%` inversión, sin duplicarlo en Servicios) y **Partida 31** (`2023–2026`).
- **Snapshot oficial y despliegue público (`https://chile-territorial.netlify.app`)**: actualizado `infra/exportar-snapshot-api.py` (precalculando las 10 comunas en `2018–2026`), `apps/api/aysen_piloto.py` y `apps/web/src/services/aysenPilotoService.ts`. Pruebas: **38/38 OK** en `pipelines/fiscal`, **38/38 activas OK** en `apps/api`, compilación `tsc && vite build` OK y verificación completa de la función serverless `netlify/functions/api.mjs` con 0 fugas de secretos.

## Piloto Aysén móvil-primero en 4 pestañas con datos oficiales (25 de noviembre de 2026)

Sobre la misma rama `fase2/estructura-y-auditoria` (preservando intactas todas las vistas modulares `#comparar`, `#estructura`, `#demografia`, `#laboratorio` y `#metodologia`, el PR #11 y `main`), se reorganizó la vista de Aysén (`#politica`) en **4 pestañas exclusivas pensadas primero para celular (`360×800`)** —**Resumen**, **Economía**, **Presupuestos** y **Proyectos**— con conservación del año seleccionado, filtro comunal cuando la cobertura lo permite, lenguaje radial cotidiano y enlace directo a la fuente oficial en cada bloque:

| Componente | Archivos | Datos oficiales verificados (cero mocks) | Pruebas |
|---|---|---|---|
| **SINIM Ficha Comunal en vivo** | `pipelines/fiscal/sinim_ficha_live.py`, `test_piloto_fiscal.py` | Extracción viva y reproducción bit-a-bit con SHA-256 de las **10/10 comunas de Aysén** (`11101`–`11402`, columna estrictamente `Comunal` BEP 2025). Piloto **Municipalidad de Aysén (`11201`)**: `$13.991,9 MM$` devengados, **`75,56%`** gasto corriente observable (Subt. 21 `$6.881,9 MM$` + Subt. 22 `$3.691,0 MM$`), **`35,59%`** costo administración interna (Planta + Contrata + Honorarios, separado de Programas Comunitarios) y enlace oficial `datos.sinim.gov.cl` | 36/36 OK en `pipelines/fiscal` |
| **DIPRES CKAN Piloto (4 entidades + mismo mes)** | `pipelines/fiscal/dipres_ckan.py` (`obtener_presupuestos_piloto_live`), `test_piloto_fiscal.py` | **2025 (cierre dic)**: Gobierno Central Nacional (`$98.802.752,8 MM$`, `66,96%` corriente, 38 filas USD excluidas), **GORE Aysén** (Inicial `$90.662,8 MM$`, Vigente `$88.494,5 MM$`, Ejecutado `$79.897,0 MM$`, `10,75%` corriente / `89,25%` inversión), **Dirección de Vialidad MOP** (`$2.476.648,9 MM$`, `8,83%` corriente / `83,61%` inversión) y **Servicios Públicos en Aysén** (`$686.763,8 MM$`). **2026 (corte agosto)**: comparación homogénea `enero–agosto 2026 vs enero–agosto 2025` (GORE Aysén `-2,78%`) | Incluido en 36/36 OK |
| **MOP DGOP Obras y Arrastre** | `pipelines/inversion/mop_proyectos.py`, `test_mop_proyectos.py` | Extracción viva y reproducción bit-a-bit de **354 registros → 78 contratos únicos** en Aysén (**43 Dirección de Vialidad**), `Decimal(34)` miles→millones CLP, línea de tiempo de 4 hitos, oración radial por obra y **2 preguntas separadas**: pagos de contratos anteriores al `11-03-2026` (**`94,53%`** regional / **`96,96%`** Vialidad) vs arrastre presupuestario comprometido (**`80,39%`** regional / **`82,92%`** Vialidad), aislando proyectos con información insuficiente | 13/13 OK en `pipelines/inversion` |
| **API Piloto Aysén (4 rutas)** | `apps/api/aysen_piloto.py`, `test_aysen_piloto.py`, `main.py` | `GET /api/v1/aysen/{resumen,economia,presupuestos,proyectos}`: consolidación anti-duplicación (`$780.652,7 MM$` neto en 3 billeteras territorializadas, excluyendo Gobierno Central Nacional), aporte sectorial aproximado con advertencia de volúmenes encadenados y degradación honesta `Sin dato disponible` (sin inventar PIB 2026 ni SINIM 2026) | 37/37 activas OK en `apps/api` |
| **UI Móvil-Primero (4 pestañas)** | `apps/web/src/PoliticalView.tsx`, `services/aysenPilotoService.ts`, `styles.css` | Auditoría real en navegador a **`360×800`** (0 errores consola, 0 HTTP ≥ 400, 0 desborde horizontal, 1 pestaña activa a la vez): verificadas **Prueba 1** (gasto corriente Muni Aysén `75,6%`, cálculo, desglose y fuente SINIM) y **Prueba 2** (obra real Vialidad MOP con oración radial, 4 hitos y registro SIPRO) + regresión `1280×800` en `#comparar` OK | `tsc && vite build` OK + auditoría 360px OK |

## Segunda fase — Estabilización, 416 series sectoriales, PIB per cápita INE y Laboratorio (24 de noviembre de 2026)

Sobre nueva rama independiente `fase2/estructura-y-auditoria` (preservando intactos el PR #11 y `main`), se ejecutó la auditoría técnica inmediata ([AUDITORIA_FASE2.md](AUDITORIA_FASE2.md)) y la Etapa 2–6 incremental coordinando 6 agentes especializados en rutas disjuntas:

| Agente | Módulos y archivos | Entregables verificados | Pruebas |
|---|---|---|---|
| **Seguridad y Auditoría** | `docs/AUDITORIA_FASE2.md`, `DECISIONS.md` (ADR-008 a ADR-010), `bcch_live.py`, `conectores.py`, `bcchService.ts`, `PoliticalView.tsx` | Eliminación total de alias públicos `VITE_BCENTRAL_TOKEN` / `NEXT_PUBLIC_BCENTRAL_TOKEN` (`0` ocurrencias en código ejecutable), respaldo automático de último corte aprobado ante fallas, `0` fugas en HTML y distinción explícita VA Administración Pública vs gasto presupuestario vs empleo público | Verificado + pruebas de rechazo OK |
| **Agente 2 · Banco Central Sectorial** | `pipelines/economia/bde_sectorial.py`, `test_bde_sectorial.py` | Extracción viva y reproducción bit-a-bit de las **416/416 series sectoriales oficiales** (`bcch-bde-sectorial-2026-11-25-1147e0cd557c8003`, 16 regiones × 13 actividades × 2 valoraciones, 2013–2025) con LQ, HHI, diversificación y Krugman | 42/42 OK en `pipelines/economia` |
| **Agente Demografía INE** | `pipelines/demografia/ine_poblacion.py`, `test_ine_poblacion.py` | Extracción viva y reproducción bit-a-bit de **17/17 series de población INE** (`ine-poblacion-bde-2026-11-25-21f6af6737da8eaf`, 306/306 obs. 2013–2030), **PIB per cápita real y nominal** (Aysén 2025 `#3` real de Chile con `$13.155.003 CLP/hab`, `122,2%` de Chile), σ-convergencia (`57,55%` → `45,70%` real) e importador comunal validado (346 comunas, prohibiendo imputar PIB regional a comunas) | 11/11 OK en `pipelines/demografia` |
| **Agente Economía y Evaluación** | `analytics/territorial/convergencia.py`, `test_convergencia.py`, `analytics/gestion/evaluacion.py`, `test_evaluacion.py` | Motores `Decimal(34)` para PIB per cápita, diversificación (`1 − HHI/10000`), σ-convergencia, simulación aritmética de Cruce 2 (`crecimiento_requerido_participacion`) y Cruces 3 y 4 (`intensidad_beneficiario`, `cobertura_programa`, `eficiencia_administrativa`) | 36/36 OK (`30` territorial + `6` gestión) |
| **Agente Finanzas Públicas** | `pipelines/fiscal/dipres_ckan.py`, `conciliacion.py`, `test_dipres_sinim.py`, `test_conciliacion.py` | Comparabilidad por meses equivalentes (`mes_corte`, `es_cierre_anual`, `advertencia_comparabilidad_meses`), respaldo automático ante fallas CKAN y motor **Cruce 1** (`analizar_disponibilidad_presupuestaria` con arrastre y advertencia de caja) | 30/30 OK en `pipelines/fiscal` |
| **Agente Backend y Laboratorio** | `apps/api/fase2.py`, `laboratorio.py`, `test_fase2.py`, `main.py` | Endpoints `/api/v1/sectorial/regiones`, `/demografia/poblacion`, `/cruces/resumen` (incl. Matriz de Dependencia Estatal) y `POST /api/v1/laboratorio/consultar` (protocolo determinista de 10 pasos en solo lectura sin IA de pago + dossier Markdown exportable) | 32/32 activas OK en `apps/api` (2 Postgres omitidas) |
| **Agente Frontend Modular** | `apps/web/src/EstructuraView.tsx`, `DemografiaView.tsx`, `LaboratorioView.tsx`, `services/fase2Service.ts`, `PoliticalView.tsx`, `main.tsx`, `styles.css` | Barra modular con 3 nuevas vistas operativas (**Estructura 16 Regiones**, **PIB per Cápita** y **Laboratorio y Dossiers** con exportación `.md`/`.html`), preservando `Vista Contable`, `Vista Política` y `Metodología` + actualización de Eje 1 con PIB per cápita oficial BCCh+INE | `tsc && vite build` OK (0 errores) |

**Total automatizado en Fase 2**: **157 pruebas Python activas aprobadas** (`30` territorial + `6` gestión + `42` economía + `11` demografía + `30` fiscal + `6` inversión + `32` API/laboratorio; `2` pruebas PostgreSQL omitidas sin Docker), compilación TypeScript/Vite limpia y verificación en vivo de todos los endpoints.

## Evolución a Lectura Política y Conectores Oficiales en Vivo (24 de noviembre de 2026)

Se eliminó cualquier cifra fija o mockeada de la capa analítica de Aysén y se integraron conectores en vivo contra las APIs oficiales del Estado de Chile (manteniendo el token exclusivamente en el servidor FastAPI fuera del navegador y de Git):

- **Conector BCCh SI3 en vivo (`pipelines/economia/bcch_live.py`, 8 pruebas nuevas; 34/34 total en `economia`)**: búsqueda dinámica `SearchSeries` (`ANNUAL`/`QUARTERLY`), descarga `GetSeries` y extracción de las **13 actividades económicas oficiales de Aysén** + 3 series trimestrales + índice HHI (`1.420,87`) y pesos exactos 2025 (**Pesca `27,16%`**, **Administración pública `16,05%`**, **Servicios personales `14,79%`**).
- **Conector DIPRES CKAN + Presupuesto Abierto (`pipelines/fiscal/dipres_ckan.py`, 12 pruebas nuevas junto con SINIM; 25/25 total en `fiscal`)**: consulta dinámica a `datos.gob.cl/api/3/action/package_search` y `datastore_search` para 2025 (cierre diciembre: GORE Aysén Partida 31 con **`8.585,033 MM$`** en Subtítulos 21–26 y **`71.312,001 MM$`** en Subtítulo 33) y 2026, separando subtítulos de gasto corriente (`21–26`), inversión (`29–31`), transferencias de capital (`33`) e ingresos/financiamiento (`01–15`), más verificación en vivo de `api.presupuestoabierto.gob.cl`.
- **Importador oficial SINIM (`pipelines/fiscal/sinim_importer.py`)**: validador de esquema e importador CSV/JSON para las 10 comunas de la Región de Aysén (CUT `11101`–`11402`) con plantilla descargable sin cifras inventadas y reporte de cobertura (`X/10`).
- **Backend FastAPI (`apps/api/conectores.py`, 10 pruebas nuevas; 26/26 activas en `apps/api`)**: expone `/api/v1/bcch/search`, `/api/v1/bcch/series/{series_id}`, `/api/v1/territorial/aysen/estructura`, `/api/v1/fiscal/dipres`, `/api/v1/fiscal/sinim`, `/api/v1/fiscal/sinim/importar` y `/api/v1/fiscal/sinim/plantilla.csv`, conservando 100% de compatibilidad OpenAPI v0.1.0.
- **Frontend `Vista Contable` / `Vista Política` (`apps/web/src/PoliticalView.tsx` y `apps/web/src/services/`)**: selector en el header, 4 ejes estratégicos de Aysén con tarjetas **Clave Territorial** junto a los gráficos, simulador interactivo de variación del gasto operativo público sobre el PIB de Aysén alimentado exclusivamente por cifras oficiales del BCCh, importador SINIM, explorador vivo de series BCCh y pie de fuente dinámico en cada tarjeta y gráfico. Compilación `tsc && vite build` aprobada (311 ms). **Total: 111 pruebas Python activas aprobadas.**

## Consolidación multiagente (24 de noviembre de 2026)

Se recuperó el repositorio completo desde GitHub (`sebastianvegajg-art/chile-territorial`), auditando las 12 ramas remotas y los PR #1 a #10. Se confirmó que **`fase1/integracion-oficial`** (`7104e01`) ya consolidaba PR #10 (`fase1/preview-local`), la demo `demo/preview-v0.2.0` y una primera integración de cuadros públicos BDE, pero carecía de PR integrado hacia `main`, de conector completo para la API autenticada del BCCh, de indicadores de estructura productiva, de adaptador local oficial sin Docker en Windows, de motor de conciliación fiscal y de inventario de fuentes de inversión.

Sobre la misma rama común **`fase1/integracion-oficial`** se coordinó a los 7 agentes especializados en rutas disjuntas conforme a [roles](AGENT_ROLES.md):

| Agente | Área y archivos | Entregables verificados | Pruebas |
|---|---|---|---|
| **Agente 1** · Recuperación y arquitectura | Raíz, `.env.example`, `infra/demo-local.ps1`, `infra/demo-local.sh`, `docs/AVANCE_FASE1.md` | Recuperación de 12 ramas/PRs sin duplicar trabajo, validación del corte oficial vigente, lanzador nativo Windows PowerShell (`demo-local.ps1`) y PR integrado para revisión | Flujo completo validado |
| **Agente 2** · Banco Central | `pipelines/economia/bde_api.py`, `verificar_bde.py`, `test_bde_api.py`, `README.md` | Extracción viva y reproducción bit-a-bit tanto de cuadros públicos BDE (`bcch-bde-publico-2026-11-24-e8fd733c80631c45`, 871 filas) como de la **API oficial autenticada del BCCh** (`bcch-bde-api-2026-11-24-66e9899b3037a598`, precisión decimal completa, 855/871 disponibles incluido crecimiento 2013 de Chile vía 2012) + inventario verificado de **416/416 series sectoriales regionales** (`bcch-bde-sectorial-2026-11-24-d56997ee753ef473`, 16/16 regiones con 26 series c/u) y soporte `ISO-8859-1` | 26/26 OK + extracción API viva OK |
| **Agente 3** · Economía territorial | `analytics/territorial/estructura.py`, `test_estructura.py`, `README.md` | Conservación de métricas PIB (`crecimiento`, `crecimiento_acumulado`, `indice_historico`, `participacion`, `ranking_regional`) + nuevos indicadores `Decimal(34)` de estructura productiva (`participacion_sectorial`), especialización (`especializacion` LQ), concentración (`concentracion_hhi` 0–10.000) e `indice_krugman` con rechazo estricto de valoración real no aditiva | 20/20 OK |
| **Agente 4** · Desarrollo frontend | `apps/web/src/main.tsx`, `history.tsx`, `api.ts`, `styles.css` | Tarjetas KPI resumen del corte activo, atajos territoriales por macrozona (`Aysén`, `Austral`, `Norte`, `Centro-Sur`), gráfico histórico interactivo con guía vertical e inspector accesible por año, vista de `#metodologia` con cobertura y notas del corte activo, responsividad móvil 360px y exportación offline intacta | `tsc && vite build` OK (163 ms) |
| **Agente 5** · Backend y almacenamiento | `apps/api/lote_oficial.py`, `main.py`, `test_lote_oficial.py`, `README.md` | Adaptador de lectura oficial validado contra `pib-datos.schema.json` (`CT_LOTE_OFICIAL`) que rechaza tajantemente cualquier dato `prueba`/`estimacion`/`error`, preservando PostgreSQL (`DATABASE_URL`) como almacén principal y modo `demo` aislado | 16/16 activas OK (2 Postgres omitidas sin Docker) |
| **Agente 6** · Finanzas públicas | `pipelines/fiscal/cruces-investigacion.json`, `conciliacion.py`, `test_conciliacion.py`; `pipelines/inversion/fuentes-inversion.csv`, `README.md`, `test_inversion.py` | Especificación formal de los 4 cruces maestros, motor `Decimal` de saldos (`saldo_por_devengar`, `saldo_no_comprometido`, `tasa_ejecucion`) y consolidación bruto-a-neto de 3 billeteras sin doble contabilización + inventario estructurado de 7 fuentes oficiales de inversión (`BIP/SNI`, `ChileIndica ARI/PROPIR`, `MOP`, `Mercado Público OCDS`, `SUBDERE FNDR`, `DIPRES Subtítulo 31`) | 19/19 OK (13 fiscal + 6 inversión) |
| **Agente 7** · Auditoría independiente | `docs/CALIDAD_PIB.md`, `tests/auditoria/contrastar_pib_oficial.py`, `test_api_pib.py` | Contraste de las 442 celdas oficiales frente a segunda descarga independiente en vivo del BCCh, verificación de 429 filas derivadas y variación 2025 vs nota anual BCCh, paridad exacta 871/871 en API + CSV + procedencia, aislamiento de modo sintético (6/6) y generación/verificación de `data/published/Chile_Territorial_Oficial.html` (953 KB) | 6/6 Q01 + auditoría oficial completa OK |

**Total automatizado en esta integración**: **87 pruebas ejecutadas y aprobadas** (`20` economía territorial + `26` Banco Central + `13` fiscal + `6` inversión + `16` API/cargador + `6` auditoría caja negra Q01; `2` pruebas de integración PostgreSQL omitidas cuando no hay instancia PostgreSQL local configurada), más compilación TypeScript/Vite y auditoría en vivo contra el Banco Central.

### Ejecución rápida en Windows (datos oficiales, sin Docker)

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r apps/api/requirements.txt
npm.cmd ci --prefix apps/web

# 1. Extraer corte oficial desde cuadros públicos BDE (o usar bde_api.py --env .env con credenciales API)
.\.venv\Scripts\python.exe -m pipelines.economia.bde_publico

# 2. Iniciar API oficial (solo lectura validada) + Frontend en http://127.0.0.1:5173
.\infra\demo-local.ps1 -Modo oficial
```

Para ejecutar con tus credenciales de la API oficial del Banco Central (fuera de Git): copia `.env.example` a `.env`, completa `BCCH_API_TOKEN` (o `BCCH_API_USER` y `BCCH_API_PASS`) y ejecuta:

```powershell
.\.venv\Scripts\python.exe -m pipelines.economia.bde_api --env .env --completo
```

## Reactivación del 24 de noviembre de 2026 (base previa en esta rama)

`fase1/integracion-oficial` parte del PR #10 (`b3145c3`) e incorpora el commit de `demo/preview-v0.2.0`. Se revisaron 12 ramas y los PR #1 a #10. `main` conserva la arquitectura `v0.1.0`. La rama de la demo aportaba una presentación descargable con datos sintéticos. Las referencias revisadas no contenían una carga oficial posterior.

| Frente | Resultado en la rama de integración |
|---|---|
| Recuperación y arquitectura | Base común con las contribuciones previas, arranque local explícito y contratos v0.1.0. |
| Banco Central | Ingesta de los cuadros públicos de PIB anual real y nominal, conservación de originales, códigos BDE y huellas. La igualdad a precisión de serie con la API autenticada y el Excel experimental queda por verificar. |
| Economía territorial | Fórmulas, linaje y pruebas para crecimiento acumulado, índice histórico y ranking. Los indicadores sectoriales quedan definidos a la espera de datos comparables. |
| Frontend | Selección múltiple, navegación por año e historial, rankings y descargas con corte de origen. Demostración autónoma regenerable con el mismo corte. |
| Backend y almacenamiento | Cargador que valida esquema y huellas antes de cargar el corte oficial en PostgreSQL. FastAPI sirve los datos y la procedencia con roles separados. |
| Finanzas públicas | Inventario y cuatro cruces del piloto de Aysén, con límites de cobertura y conciliación en [el registro fiscal](../pipelines/fiscal/README.md). |
| Auditoría | Cobertura, contraste de cifras, revisión de fórmulas y pruebas de integración en [calidad del PIB](CALIDAD_PIB.md). |

## Ejecución local con datos oficiales

Desde la raíz, prepara las dependencias:

```sh
python -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt
npm --cache "${TMPDIR:-/tmp}/ct-npm" ci --prefix apps/web
```

Sigue la [ingesta pública](../pipelines/economia/README.md) para obtener el lote y sus originales en `data/`. Inicializa PostgreSQL con `PIB_DB_MODE=aprobada infra/pib-db.sh iniciar` y la configuración descrita en [infraestructura](../infra/README.md). Con `DATABASE_URL` de ingesta, carga el lote según las [instrucciones de la API](../apps/api/README.md).

Cambia `DATABASE_URL` a la conexión de lectura y ejecuta `CT_PYTHON=.venv/bin/python infra/demo-local.sh oficial`. Abre `http://127.0.0.1:5173`. Los archivos oficiales quedan en el directorio de datos local, fuera de Git. El CSV de la aplicación identifica el corte usado para consultarlos.

Con la API activa, exporta la versión autónoma desde la raíz:

```sh
npm --prefix apps/web run build
node apps/web/scripts/export-html.mjs data/published/Chile_Territorial_Oficial.html
```

Abre el archivo en un navegador o usa «Descargar HTML autónomo» en el comparador local. La copia incluye los datos y su procedencia, y permite consultar el corte sin conexión.

## Estado anterior a la reactivación

Base aprobada `v0.1.0`. Actualizado el 24 de noviembre de 2026. Las ramas de componentes se revisan por separado. Esta rama reúne los cambios para probarlos localmente.

| Tarea | Resultado y evidencia | Estado |
|---|---|---|
| A03 | Migración PostgreSQL, carga transaccional por corte y roles separados de ingesta y lectura. Pruebas de idempotencia, permisos y rechazo del corte sintético en la base aprobada | [PR 8](https://github.com/sebastianvegajg-art/chile-territorial/pull/8) |
| D01 | Prototipo responsive con selector de 16 regiones, estados de disponibilidad y tabla accesible. Validado a 360 y 1200 px | [PR 5](https://github.com/sebastianvegajg-art/chile-territorial/pull/5) |
| M01 | Crecimiento real y participación nominal mediante Decimal y linaje. Cinco pruebas | [PR 2](https://github.com/sebastianvegajg-art/chile-territorial/pull/2) |
| E01 | Verificador BDE con catálogo, cuatro series de referencia, originales y manifiesto SHA-256. Siete pruebas. Sin token configurado en este entorno | [PR 3](https://github.com/sebastianvegajg-art/chile-territorial/pull/3). Extracción autenticada pendiente |
| E02 | Preparación de la carga de PIB real y nominal, dimensiones regionales y contraste con el Excel | Pendiente de E01 autenticada y disponibilidad del Excel para su contraste |
| F01 | Tres billeteras y 12 filas de cobertura 2025–2028, con brechas y evidencia documental. Cuatro pruebas | [PR 7](https://github.com/sebastianvegajg-art/chile-territorial/pull/7) |
| B01 | Cinco rutas del contrato, CSV y corte. Demostración sintética y adaptador PostgreSQL de lectura | [PR 4](https://github.com/sebastianvegajg-art/chile-territorial/pull/4). Conexión PostgreSQL con rol lector verificada. Lectura de cifras oficiales pendiente de E02 |
| W01 | Comparador regional con React y datos sintéticos mediante API local | [PR 9](https://github.com/sebastianvegajg-art/chile-territorial/pull/9). Prueba integrada en Chromium |
| Q01 | Seis controles HTTP sobre cobertura, filtro, CSV, corte, faltantes y procedencia | [PR 6](https://github.com/sebastianvegajg-art/chile-territorial/pull/6). Contraste oficial pendiente de E02 |

## Decisiones y problemas

- La demostración se inicia con modo explícito y corte `prueba-local`. Los valores generados sirven para probar filtros, fórmulas y presentación. La base aprobada conserva separados sus cortes.
- Las pruebas de Docker agotaron temporalmente el almacenamiento. Se retiraron únicamente los contenedores y volúmenes descartables creados en esta fase.
- F01 documenta ejecución observada, proyectos, proyecciones y faltantes por separado. El piloto fiscal queda fuera de la ruta crítica para comparar el PIB regional.

## Ejecutar el comparador

Desde la raíz de esta rama, con Python 3 y Node instalados:

```sh
python -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt
npm --cache "${TMPDIR:-/tmp}/ct-npm" ci --prefix apps/web
CT_PYTHON=.venv/bin/python infra/demo-local.sh
```

Abre `http://127.0.0.1:5173`. Los dos procesos escuchan solo en la interfaz local. Detén ambos con Ctrl+C. El modo demostración no requiere Docker ni credenciales.

## Verificar la demostración

Con los procesos en ejecución, ejecuta `python -m unittest discover -s tests/auditoria -v` para la API. Para el flujo web instala Playwright en el entorno de pruebas y ejecuta `python tests/integration/comparador_browser.py` con Chromium de Playwright o define `CT_CHROMIUM` con la ruta a Chromium local. La prueba verifica selección, navegación, procedencia, CSV, aislamiento del modo oficial y vista de 360 px. La interfaz compara un año a la vez. La auditoría completa con cifras oficiales y accesibilidad asistida queda pendiente.
