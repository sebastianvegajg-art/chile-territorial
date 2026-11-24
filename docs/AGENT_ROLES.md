# Mandatos de trabajo por agente

La arquitectura está aprobada. Ejecuta estos mandatos cuando el titular autorice la activación. Cada fila indica qué leer, dónde entregar y cómo se aceptará la entrega. Las tareas y sus dependencias se detallan en el [backlog](TASK_BACKLOG.md).

| Rol | Encargo y archivos propios | Insumos y criterio de aceptación |
|---|---|---|
| 01 Arquitectura y coordinación | Mantener raíz, contratos, migraciones, infraestructura y documentos comunes. Integrar decisiones y cambios | Propuesta aprobada, esquema migrable y contratos con versión y ejemplos |
| 02 Ingeniería de datos económicos | Implementar catálogo, conector BDE y carga reproducible en `pipelines/economia/` | OpenAPI para contexto, contrato de datos de 01 y acceso seguro. Cobertura, unidades, versiones y conciliación de Excel/BDE demostradas |
| 03 Ingeniería de datos fiscales | Implementar inventario, normalización y conciliación en `pipelines/fiscal/` | Perímetro acordado con 01, metodología de 06 y fuentes. Partidas trazables, transferencias y residuales cuantificados |
| 04 Inversión pública y privada | Mapear BIP, SEA, MOP y Mercado Público en `pipelines/inversion/` | Grano y claves acordados con 01 y 03. Distinguir montos y etapas, documentar coincidencias ambiguas |
| 05 Economía territorial y econometría | Versionar indicadores y protocolos de inferencia en `analytics/territorial/` | Metadatos de 02 y 04. Fórmulas reproducibles y pruebas de unidades, faltantes y comparabilidad |
| 06 Administración pública y evaluación | Definir cohortes, costos atribuibles, calidad y comparaciones en `analytics/gestion/` | Alcance de 03 y pregunta de 11. Indicadores con denominador válido y criterios equivalentes |
| 07 Auditoría estadística y metodológica | Verificar fuentes, series, duplicidades y reproducibilidad en `tests/auditoria/` | Contratos y salidas de todos los dominios. Evidencia independiente y defectos bloqueantes registrados |
| 08 Backend | Implementar API de lectura, exportación y procedencia en `apps/api/` | Contratos de 01, datos de 02 y métricas de 05. Pruebas de filtros, corte fijo, estados y CSV |
| 09 Frontend | Implementar comparador y detalle regional en `apps/web/` | Contrato de 01, API de 08 y pautas de 10. Flujo completo en móvil y escritorio, teclado, tabla y trazabilidad |
| 10 Diseño visual y editorial | Crear patrones, textos, gráfica y tabla en `design/` | Alcance del MVP y definiciones de 05. Especificaciones de estados, contraste y lectura clara |
| 11 Coordinación de investigaciones | Mantener preguntas, registro de anuncios y fichas de evidencia en `research/` | Métodos de 05, 06 y revisión de 07. Hipótesis falsable, evidencia contraria y estado editorial documentados |

## Trabajo en paralelo

01 mantiene el [contrato inicial](../contracts/README.md) antes de abrir ramas de implementación. Cada rol trabaja solo en su ruta, entrega pruebas unitarias con su componente y pide cambios compartidos a 01 por escrito. 01 coordina `tests/integration/` con los roles afectados. 08 y 09 usan los mismos ejemplos sintéticos versionados y rotulados mientras se valida la ingesta. 03 y 04 pueden investigar fuentes en paralelo y acuerdan el enlace proyecto–movimiento sin compartir archivos. 07 conserva sus verificaciones en su ruta y solicita correcciones al responsable. 01 integra revisiones tras verificar compatibilidad y ejecutar las pruebas de integración.

## Mandatos ejecutables y archivos compartidos

| Agente | Instrucción independiente | Única ruta de escritura |
|---|---|---|
| 02 · Banco Central | [E01, E02 y E03](agentes/banco-central.md) | `pipelines/economia/**` |
| 08 · Backend | [B01](agentes/backend.md) | `apps/api/**` |
| 09 · Frontend | [W01](agentes/frontend.md) | `apps/web/**` |
| 03 · Finanzas públicas | [F01 y F02](agentes/finanzas-publicas.md) | `pipelines/fiscal/**` |
| 07 · Auditoría metodológica | [Q01 y Q02](agentes/auditoria-metodologica.md) | `tests/auditoria/**` |

Los cinco roles leen `AGENTS.md`, `docs/**`, `contracts/**`, `db/migrations/**`, `infra/**`, `tests/integration/**` y configuración raíz. Solo 01 integra cambios en esas rutas. Las pruebas unitarias viven bajo la ruta del agente. Los artefactos reales se manejan en el entorno de datos fuera de Git. Si se necesita cambiar un archivo compartido, entregar a 01 la propuesta, los consumidores afectados y los casos de verificación.
