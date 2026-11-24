# Tareas y criterios de aceptación

Cada rol inicia con su mandato en [roles](AGENT_ROLES.md). P0 habilita la primera entrega, P1 amplía cobertura y P2 corresponde a investigación y expansión. A01 está aprobada y A02 entrega el contrato inicial en el PR #1. La implementación comienza mediante autorización de activación. E01 requiere acceso seguro a BDE.

| ID | Prioridad · responsable | Tarea | Depende de | Aceptación |
|---|---|---|---|---|
| A01 | P0 · 01 | Aprobar arquitectura común | — | Aprobación explícita y decisiones registradas |
| A02 | P0 · 01 | Definir contrato API/datos v0.1.0 | A01 | OpenAPI, esquema y ejemplo sintético versionados |
| A03 | P0 · 01 | Preparar entorno y persistencia local | A02 | Migraciones, configuración y comandos reproducibles |
| E01 | P0 · 02 | Verificar acceso BDE y catálogo | A01 | Extracción de cuatro referencias, coincidencia de catálogo, manifiesto y logs saneados |
| E02 | P0 · 02 | Cargar PIB total y dimensiones regionales | A03, E01 | 34 series esperadas o discrepancias explicadas, matriz 2013–2025, revisiones y comparación oficial |
| M01 | P0 · 05 | Formalizar métricas del MVP | A02 | Casos de crecimiento, participación, unidad incompatible, denominador cero y año previo faltante |
| D01 | P0 · 10 | Diseñar comparador | A01 | Prototipo con móvil, tabla equivalente, filtros accesibles y procedencia |
| B01 | P0 · 08 | Implementar API, CSV y procedencia | A02, M01; A03 para persistencia | Respuestas tipadas, validación y pruebas de corte, paginación y CSV. Puede empezar con ejemplos |
| W01 | P0 · 09 | Construir tablero y comparador | A02, D01 | Arranque con Aysén, 16 regiones seleccionables, referencia nacional, datos/ausencias, teclado y CSV |
| Q01 | P0 · 07 | Auditar entrega local | E02, B01, W01 | Carga repetida idempotente, contraste con publicación oficial y flujo accesible extremo a extremo |
| E03 | P1 · 02 | Completar PIB sectorial | Q01 | Reproducir Aysén y Los Lagos, comparar el catálogo con las 416 series identificadas inicialmente, registrar altas, bajas y cambios y cubrir otras 14 regiones con faltantes explícitos |
| F01 | P1 · 03 | Validar datos de las tres billeteras de Aysén | A02 | Cortes 2025–2028 disponibles inventariados, etapas, entidades, transferencias y brechas documentadas |
| F02 | P1 · 03 | Conciliar y territorializar piloto fiscal | F01, G01 | Reparto geográfico, brutos a neto, residuales y reglas para compromisos reproducibles |
| I01 | P1 · 04 | Obtener cartera de inversión | A02 | Identidad y eventos por BIP, SEA, MOP y Mercado Público con cobertura y enlaces ambiguos pendientes de revisión |
| G01 | P1 · 06 | Definir gestión, beneficiarios y costos | A01 | Cohortes, bases de reparto y comparación aprobadas por revisión metodológica |
| P01 | P1 · 05 | Construir cruces del piloto fiscal y de inversión | E02, F02, I01, G01 | Indicadores con fuentes y denominadores compatibles. Cobertura, saldos y montos sin asignar visibles |
| Q02 | P1 · 07 | Auditar sectorial y piloto | E03, P01 | Revisión de cambios respecto de las 416 series identificadas inicialmente y conciliación fiscal muestral, con evidencia reproducible |
| R01 | P2 · 11 | Diseñar investigación piloto y ficha de compromisos | A01, M01 | Protocolo falsable y criterios editoriales definidos. Publicación tras auditar evidencia |
| M02 | P2 · 05 | Proponer escenarios y evaluación | Q02, R01 | Supuestos, validación retrospectiva, rangos e identificación causal solo si el diseño la sustenta |
| X01 | P2 · 01 | Ampliar cobertura comunal y preparar puesta en servicio | Q02 | Matriz de cobertura nacional, controles de acceso y operación. Despliegue sujeto a autorización |

El objetivo de las 34 series de PIB total surge de 17 territorios por dos valoraciones. Las 416 series sectoriales surgen de 16 regiones por 13 actividades por dos valoraciones. El conteo sectorial documenta la cobertura identificada en la prueba, con base en el catálogo de ese momento. Registrar fecha, hash, diferencias y su efecto sobre cobertura. La publicación con años ausentes requiere estado y explicación por serie y período.
