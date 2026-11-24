# Banco Central · agente 02

**Activación.** Inicia E01 cuando se autorice el trabajo y el token se configure fuera de Git. Para E02 espera A03. E03 espera Q01. Lee [fuentes](../DATA_SOURCES.md), [contratos](../../contracts/README.md) y [metodología](../METHODOLOGY.md). Escribe únicamente en `pipelines/economia/**`, incluidas tus pruebas.

1. Usa el catálogo oficial y reproduce las cuatro series de referencia. Conserva manifiesto, hash, versión, corte, unidades y conteos. Sanea URLs y errores. Si falta acceso marca la verificación pendiente y usa únicamente el fixture para desarrollar.
2. Normaliza nivel real/nominal nacional y regional, cubre la matriz 2013–2025, mapea vigencias territoriales y revisa duplicados, faltantes y revisiones. Entrega lotes conforme al contrato y verifica repetición idempotente. Si se proporciona Excel, contrasta por serie, año, valoración y unidad, con tolerancia justificada y discrepancias explícitas.
3. En E03 compara catálogo y línea base de 416 series identificadas. Reporta altas, bajas, cambios y faltantes por territorio y actividad. Si solo está disponible el conteo, documenta la limitación y conserva el primer inventario reproducible.

**Entrega.** Conector, comandos reproducibles, pruebas locales, matriz de cobertura y reporte saneado con referencias verificables. Pide cambios de esquema a 01.
