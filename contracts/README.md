# Contratos del MVP · v0.1.0

[Datos](pib-datos.schema.json), [API OpenAPI 3.1](openapi.json) y [ejemplo exclusivamente sintético](pib-prueba.json). El contrato de datos describe el lote normalizado que entrega el conector. PostgreSQL y las migraciones implementarán su persistencia. Los archivos JSON se leen sin instalar dependencias del proyecto.

## Integridad del lote

- Una publicación tiene un identificador inmutable. Los identificadores de observación son únicos entre cortes. Dentro de cada publicación es única la combinación territorio, año, métrica y valoración. La fecha de extracción y el corte provienen del insumo. Hash SHA-256 calculado sobre los bytes del insumo.
- Para niveles oficiales, la procedencia exige código BDE, artefacto y selector verificable. Para indicadores derivados exige fórmula versionada e identificadores de insumos del mismo corte. Un cálculo reproducible con insumos oficiales se rotula «calculado a partir de datos oficiales» en la interfaz. Los supuestos o imputaciones producen estimaciones. El MVP de producción publica niveles oficiales y cálculos documentados, y reserva la clase estimación para ampliaciones.
- Cada observación tiene una procedencia. Los nulos conservan la causa, incluyendo ausencia, supresión, no aplicabilidad y error. Un cero informado conserva su valor. Un error de ingesta bloqueante impide promover el lote y mantiene disponible el último corte aprobado.
- El contrato conserva valores decimales como cadenas para evitar pérdida de precisión. Los niveles se normalizan a millones de CLP con conversión exacta y trazable. Los niveles reales requieren el año de referencia oficial. El lote puede incluir un nivel real auxiliar de 2012 para calcular el crecimiento de 2013 si existe una base comparable. Sus identificadores sirven para linaje. Se excluye de resultados de consulta y conteos de cobertura desde 2013.
- Las publicaciones de prueba se cargan en un entorno aislado. Cualquier respuesta demo debe identificar el corte sintético de forma visible. La procedencia pública devuelve solo identificadores y metadatos saneados. Los insumos, rutas privadas y credenciales quedan fuera de los recursos públicos.
- Validar el objeto con JSON Schema y verificar por separado unicidad, integridad de referencias, cobertura, coherencia de corte y restricciones de publicación. Las proyecciones e hipótesis quedan fuera de este contrato.

## Consulta

Si se omite `publicacion`, resolver el último corte aprobado por fecha e identificador. Fijar ese corte en la respuesta JSON y en la cabecera `X-Publicacion` de JSON y CSV. Frontend reutiliza el identificador en paginación y descarga. Si se omiten los territorios, consultar Chile y las 16 regiones. Usar `CL` para Chile y códigos regionales CUT de dos dígitos. Los códigos BDE se mapean desde el catálogo, con la vigencia documentada.

El límite de consulta es de 100 años inclusivos. Los años invertidos, intervalos mayores, paginación inválida y métricas incompatibles devuelven 422. Participación solo para regiones. Si se omite el filtro territorial en esa métrica, consultar las 16 regiones. Conservar nulos con su estado. Una consulta válida sin filas devuelve 200 con colección vacía o CSV con cabecera. Sin corte disponible, devolver 404. CSV usa la cabecera y el orden explícitos de OpenAPI, comas, celdas vacías para nulos y cabecera.

Fórmulas y restricciones de comparabilidad en [metodología](../docs/METHODOLOGY.md). Un cambio incompatible de esquema, campos o significado requiere revisión del coordinador y versión de contrato.
