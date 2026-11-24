# Fórmulas del PIB · M01

Ejecutar desde la raíz con Python 3.10 o posterior.

```bash
python -m unittest analytics.territorial.test_pib -v
```

| Función | Versión | Cálculo |
|---|---|---|
| `crecimiento(actual, previo)` | `pib-crecimiento-v1` | 100 × (actual − previo) / previo |
| `participacion(region, chile)` | `pib-participacion-v1` | 100 × región / Chile |

Las entradas son niveles normalizados del [contrato v0.1.0](../../contracts/README.md). La unidad de entrada es millones de CLP. El resultado se expresa en porcentaje como cadena decimal, con contexto fijo de 34 dígitos significativos y redondeo al par. El consumidor decide los decimales de presentación. El cálculo de crecimiento usa un nivel auxiliar de 2012 cuando procede.

El campo `formula_version` identifica el cálculo, `insumos` conserva las observaciones utilizadas o evaluadas y `motivo` explica las ausencias. Si una entrada está preliminar, el resultado disponible conserva esa condición. Si una entrada incorpora una estimación compatible, el resultado se clasifica como estimación. Se preserva la clase de prueba de entradas sintéticas compatibles. El consumidor rotula los derivados oficiales como calculados a partir de datos oficiales.

El cargador verifica la cobertura, la vigencia geográfica y la procedencia original antes de publicar un nivel. Este módulo exige igual publicación, valoración, unidad y año de referencia cuando corresponde y aplica las restricciones de año y territorio de cada fórmula. La participación utiliza el total nacional publicado; las diferencias de cobertura y las partidas no regionalizadas se documentan en el corte.
