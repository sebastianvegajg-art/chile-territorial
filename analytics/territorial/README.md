# Fórmulas del PIB · M01

Ejecutar desde la raíz con Python 3.10 o posterior.

```bash
python -m unittest analytics.territorial.test_pib -v
```

| Función | Versión | Cálculo |
|---|---|---|
| `crecimiento(actual, previo)` | `pib-crecimiento-v1` | 100 × (actual − previo) / previo |
| `crecimiento_acumulado(actual, base)` | `pib-crecimiento-acumulado-v1` | 100 × (actual − base) / base |
| `indice_historico(actual, base)` | `pib-indice-historico-v1` | 100 × actual / base |
| `participacion(region, chile)` | `pib-participacion-v1` | 100 × región / Chile |

Las entradas son niveles normalizados del [contrato v0.1.0](../../contracts/README.md). La unidad de entrada es millones de CLP. El resultado se expresa en porcentaje o en puntos de índice según la fórmula como cadena decimal, con contexto fijo de 34 dígitos significativos y redondeo al par. El consumidor decide los decimales de presentación. El cálculo de crecimiento usa un nivel auxiliar de 2012 cuando procede.

El campo `formula_version` identifica el cálculo, `insumos` conserva las observaciones utilizadas o evaluadas y `motivo` explica las ausencias. Si una entrada está preliminar, el resultado disponible conserva esa condición. Si una entrada incorpora una estimación compatible, el resultado se clasifica como estimación. Se preserva la clase de prueba de entradas sintéticas compatibles. El consumidor rotula los derivados oficiales como calculados a partir de datos oficiales.

El cargador verifica la cobertura, la vigencia geográfica y la procedencia original antes de publicar un nivel. Este módulo exige igual publicación, valoración, unidad y año de referencia cuando corresponde y aplica las restricciones de año y territorio de cada fórmula. La participación utiliza el total nacional publicado; las diferencias de cobertura y las partidas no regionalizadas se documentan en el corte.

El acumulado y el índice usan el año de análisis elegido explícitamente como base. Ambos extremos pertenecen al mismo territorio, publicación y referencia de encadenamiento. Se admiten intervalos de varios años y se conservan los faltantes de cada extremo. La base del índice equivale a 100.

`ranking_regional(filas)` ordena valores regionales descendentes para una combinación común de publicación, año, métrica, valoración, unidad, referencia de encadenamiento, año base de análisis cuando corresponde y clase de evidencia. Los faltantes y el agregado nacional se omiten. Cada empate comparte posición y deja el salto correspondiente en la siguiente posición. El código CUT determina el orden de presentación entre empates. Cada resultado conserva el identificador de la observación. Acumulados, índices y rankings se pueden calcular sobre datos del contrato vigente.

## Indicadores sectoriales por incorporar

| Indicador | Insumos y cálculo |
|---|---|
| Estructura productiva | 100 × VA nominal de una actividad / VA nominal total del territorio, con la misma clasificación, año y corte |
| Concentración productiva | Suma de los cuadrados de las cuotas sectoriales del VA nominal en escala 0–1. Requiere una clasificación exhaustiva sin duplicaciones y un perímetro común |
| Especialización relativa | Cuota nominal de la actividad en el VA de la región / cuota nominal de la misma actividad en el VA nacional, con clasificación y perímetro equivalentes |

La validación de la estructura requiere conciliar las partidas con el total del perímetro y registrar impuestos a los productos u otras partidas que queden fuera. Documentar la clasificación, los cambios de cobertura y el tratamiento de faltantes antes de comparar regiones o períodos. Conservar la concentración y la especialización sin cálculo cuando falten componentes esenciales o falle la comparabilidad. La publicación de estos indicadores queda sujeta a la validación del catálogo sectorial de la BDE. No se agregan niveles reales encadenados para reconstruir el total.
