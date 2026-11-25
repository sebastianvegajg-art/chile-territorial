# Fórmulas del PIB · M01

Ejecutar desde la raíz con Python 3.10 o posterior.

```bash
python -m unittest discover -s analytics/territorial -v
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

## Estructura productiva, concentración y especialización (`estructura.py`)

Implementa indicadores sectoriales reproducibles sobre observaciones normalizadas de valor agregado nominal, utilizando aritmética exacta con `Decimal` (contexto fijo de 34 dígitos significativos y redondeo `ROUND_HALF_EVEN`) y el mismo contrato de trazabilidad `Resultado` (`valor`, `motivo`, `formula_version`, `insumos`, `estado`, `clase`).

| Función | Versión | Fórmula y escala |
|---|---|---|
| `participacion_sectorial(va_actividad, va_total)` | `estructura-participacion-v1` | `100 × VA_act / VA_total` (porcentaje, regional o nacional) |
| `especializacion(va_reg_act, va_reg_total, va_nac_act, va_nac_total)` | `estructura-especializacion-v1` | `(VA_reg_act / VA_reg_total) / (VA_nac_act / VA_nac_total)` (Coeficiente de Localización, LQ ≥ 0) |
| `concentracion_hhi(participaciones_o_niveles_sectoriales)` | `estructura-hhi-v1` | `∑ (100 × VA_i / ∑ VA_j)²` o `∑ s_i²` en escala estándar `0` a `10.000` |
| `indice_krugman(niveles_regionales, niveles_nacionales)` | `estructura-krugman-v1` | `0.5 × ∑ \|s_ir − s_in\|` en rango `[0, 1]` |

### Requisitos de comparabilidad y control de calidad

- **Valoración nominal obligatoria**: todos los indicadores de estructura exigen `valoracion="nominal"` y `anio_referencia=None`. Las entradas con valoración `"real"` se rechazan explícitamente debido a la no aditividad de los volúmenes encadenados fuera del año de referencia.
- **Unidades y métricas**: los niveles de valor agregado (`metrica` en `{"valor_agregado", "nivel"}`) deben expresarse homogéneamente en `"millones CLP"`. `concentracion_hhi` también acepta participaciones sectoriales (`metrica` en `{"participacion_sectorial", "participacion"}`) con unidad porcentual (`"porcentaje"` o `"%"`), siempre que concilien con `100%` (tolerancia de `0.0001` puntos porcentuales por redondeo de entrada).
- **Corte, período, clasificación y perímetro**: todas las observaciones de un cálculo deben compartir exactamente la misma `publicacion`, `anio`, `clasificacion` sectorial y `perimetro` de valor agregado. En `especializacion` e `indice_krugman`, la región debe corresponder a un código CUT válido (`01`–`16`) y la referencia nacional a `"CL"`.
- **Integridad sectorial y cobertura**: se rechazan actividades duplicadas o la mezcla del agregado `"total"` dentro de listas de componentes sectoriales (`estado="error"`). `indice_krugman` exige exactamente el mismo conjunto de actividades en la región y en el país. Si alguna actividad presenta estado `faltante`, `suprimido`, `no_aplicable` o `error`, no se omite silenciosamente ni se aproxima como cero: se retorna `valor=None` conservando el estado ausente y documentando la cobertura disponible en `motivo`.
- **Cero informado vs. faltante y denominadores**: un valor `"0"` con estado `informado` o `preliminar` participa válidamente en el numerador (`participacion_sectorial`, `especializacion`) y en desagregaciones (`concentracion_hhi`, `indice_krugman`). Cualquier denominador cero o no positivo produce `valor=None` con `estado="faltante"` y causa explícita.
- **Trazabilidad y estados**: `insumos` conserva los identificadores de las observaciones evaluadas, `estado="preliminar"` se propaga si algún insumo es preliminar y `clase="estimacion"` se propaga si algún insumo compatible corresponde a una estimación. No se permite mezclar observaciones de clase `"prueba"` con datos `"oficial"` o `"estimacion"`. La publicación en producción de indicadores sectoriales queda sujeta a la validación del catálogo sectorial oficial de la BDE y la conciliación del perímetro respecto de impuestos a los productos u otras partidas no asignadas.
