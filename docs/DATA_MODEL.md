# Modelo lógico

## Núcleo de publicación

| Entidad | Grano y campos principales |
|---|---|
| `source_dataset` | Conjunto por organismo y código externo. Método de acceso, restricciones y documentación |
| `ingestion_run` | Intento por fuente, con inicio, fin, estado, versión del conector y conteos |
| `source_artifact` | Insumo por conjunto y hash SHA-256. Corte, fecha original si se informa, descarga, referencia saneada y localización interna |
| `territory_version` | Código oficial, nivel y vigencia, con padre versionado y referencia de clasificación |
| `territory_entity` | Relación vigenciada entre entidad ejecutora y territorio. Admite varios territorios para una municipalidad |
| `economic_series` | Fuente y código oficial. Dimensiones de territorio, actividad, frecuencia, medida, moneda, escala y referencia; versionar cambios de definición |
| `dataset_release` | Corte publicable, cobertura, revisor, fecha y manifiesto de insumos, reglas y versiones |
| `economic_observation` | Publicación, versión de serie y período como clave única. Decimal exacto, estado, artefacto y selector de origen |
| `indicator_definition` | Indicador y versión, con fórmula, unidad, supuestos y comparabilidad |
| `derived_observation` | Publicación, versión de indicador, claves dimensionales y período. Vínculos a observaciones insumo, resultado y motivo si faltante |
| `quality_issue` | Ejecución o publicación, regla, severidad, referencia y resolución |

Los períodos incluyen límites explícitos y frecuencia. Un año publicado puede cambiar en el siguiente corte. Una corrección genera una nueva versión sin alterar observaciones ya publicadas. La clase de evidencia y el estado son campos distintos. El [contrato del MVP](../contracts/README.md) define la correspondencia y aísla lotes de prueba. Estados mínimos: informado, preliminar, faltante, suprimido, no aplicable y error. Solo informado y preliminar admiten valores en observaciones oficiales; estimaciones y proyecciones se almacenan con su propia clase y versión. Un fallo de ingesta no sustituye un dato oficial anterior. Chile se representa como territorio nacional y las etiquetas históricas se resuelven por vigencia.

## Extensión fiscal y de inversión

- `budget_snapshot` guarda saldo presupuestario por publicación, ejercicio, fecha de corte, institución, programa, clasificación, entidad financiadora y moneda. Inicial y vigente son campos distintos. Los saldos al cierre se comparan entre cortes y se prohíbe sumarlos en el tiempo.
- `fiscal_event` guarda el movimiento elemental por fuente e identificador estable, con etapa, fecha contable, moneda, monto con signo, ejecutor, financiador, contraparte y vínculo contable. Cuando el insumo sea agregado se almacena como tal, con grano, cobertura y modalidad acumulada o de período, evitando mezclarlo con el detalle superpuesto.
- `transfer_match` registra partidas vinculadas, monto conciliado, perímetro, método, evidencia y aprobación. Una correspondencia puede ser parcial o reunir varios registros.
- `project`, `project_identifier` y `project_event` conservan identidad, códigos BIP, SEA, contratos u otros, etapas, fuente, fecha y monto según concepto. Un contrato puede financiar parte de un proyecto y el proyecto admitir varios contratos.
- `territorial_allocation` conserva método y proporción por evento, territorio, versión y rol geográfico. Cada reparto suma 100 % incluyendo la fracción sin asignar. Financiador, ejecutor, ubicación física y área beneficiada son roles distintos.
- `program_result` separa programa, cohorte, período, universo, beneficiarios únicos cuando sea posible, unidad, producto y resultado.
- `scenario_run` conserva versión del modelo, horizonte, supuestos, insumos, semilla cuando aplique e intervalos.

Pruebas de integridad: unicidad, límites de vigencia, coherencia de unidad, proporciones, signos y notas de crédito; conservación de montos tras repartos y conciliación entre totales y detalle cuando sus perímetros coincidan.
