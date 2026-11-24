# Registro de decisiones

Estado inicial de todas las entradas: **propuesta para aprobación**. Las revisiones conservarán fecha, responsable, estado y razón del cambio.

| ID | Decisión propuesta | Razón y alternativa |
|---|---|---|
| ADR-001 | React/TypeScript, FastAPI y PostgreSQL en un monolito modular | Amplía la prueba Excel a una API trazable con contratos. Una web estática es viable para exhibir un corte; DuckDB puede complementar el análisis local |
| ADR-002 | Ingesta fuera de las solicitudes web, publicaciones inmutables con promoción transaccional | Aísla fallas y permite reproducir consultas. Una consulta directa a la fuente depende de su disponibilidad y revisiones |
| ADR-003 | Catálogo BDE como autoridad de nombres y códigos, token de ejecución seguro | Reduce asociaciones erróneas y sigue la autenticación REST documentada. Excel constituye una referencia a conciliar |
| ADR-004 | Modelo fiscal por etapa, perímetro y rol territorial | Hace visibles transferencias, saldos y montos sin asignar. La suma de tres totales brutos puede duplicar financiamiento |
| ADR-005 | PIB total como primer producto local y sectorial posterior | Entrega una primera herramienta contrastable y limita la dependencia del catálogo sectorial antes de validar las 14 regiones pendientes |
| ADR-006 | Contratos y migraciones con responsable único, revisión de auditoría independiente | Permite trabajo paralelo después de la aprobación y reduce cambios incompatibles |
| ADR-007 | Desarrollo local y despliegue mediante autorización posterior | Permite verificar trazabilidad y acceso a fuentes antes de autorizar exposición pública y operación externa |
