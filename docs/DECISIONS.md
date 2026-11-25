# Registro de decisiones

**ADR-001 a ADR-007 aprobadas por el titular del proyecto el 24 de noviembre de 2026.** La aprobación se otorgó en la conversación del proyecto y se registra mediante el [PR #1](https://github.com/sebastianvegajg-art/chile-territorial/pull/1). La integración del PR requiere autorización separada. Las revisiones conservarán fecha, responsable, estado y razón del cambio.

| ID | Decisión aprobada | Razón y alternativa |
|---|---|---|
| ADR-001 | React/TypeScript, FastAPI y PostgreSQL en un monolito modular | Amplía la prueba Excel a una API trazable con contratos. Una web estática es viable para exhibir un corte; DuckDB puede complementar el análisis local |
| ADR-002 | Ingesta fuera de las solicitudes web, publicaciones inmutables con promoción transaccional | Aísla fallas y permite reproducir consultas. Una consulta directa a la fuente depende de su disponibilidad y revisiones |
| ADR-003 | Catálogo BDE como autoridad de nombres y códigos, token de ejecución seguro | Reduce asociaciones erróneas y sigue la autenticación REST documentada. Excel constituye una referencia a conciliar |
| ADR-004 | Modelo fiscal por etapa, perímetro y rol territorial | Hace visibles transferencias, saldos y montos sin asignar. La suma de tres totales brutos puede duplicar financiamiento |
| ADR-005 | PIB total como primer producto local y sectorial posterior | Entrega una primera herramienta contrastable y limita la dependencia del catálogo sectorial antes de validar las 14 regiones pendientes |
| ADR-006 | Contratos y migraciones con responsable único, revisión de auditoría independiente | Permite trabajo paralelo después de la aprobación y reduce cambios incompatibles |
| ADR-007 | Desarrollo local y despliegue mediante autorización posterior | Permite verificar trazabilidad y acceso a fuentes antes de autorizar exposición pública y operación externa |
| ADR-008 | Prohibición de alias públicos de frontend (`VITE_*`, `NEXT_PUBLIC_*`) para credenciales y respaldo automático de último corte aprobado | Evita exponer tokens en el bundle del navegador y garantiza continuidad operativa si falla una actualización externa |
| ADR-009 | Extracción sectorial completa de 416 series (16 regiones × 13 actividades × 2 valoraciones) y población INE vía BDE para PIB per cápita; prohibición de imputar PIB regional a comunas | Permite LQ, HHI, diversificación, Krugman y σ-convergencia con igual perímetro nominal y rigor territorial |
| ADR-010 | Laboratorio de investigación determinista de solo lectura (sin servicios de IA pagos) y generación de dossiers reproducibles | Permite contrastar hipótesis con evidencia favorable/contraria y citas exactas sin alterar datos oficiales ni incurrir en costos externos |
