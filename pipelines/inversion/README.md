# Arquitectura de enlace de inversión pública territorial (`pipelines/inversion/`)

Revisión documental al 24 de noviembre de 2026. Este módulo implementa el inventario inicial y las reglas de enlace por etapas de la cartera de inversión pública (hito **I01**) y su articulación con la consolidación fiscal (`pipelines/fiscal/`, hitos **F01**, **F02** y **P01**).

## Principio rector: trazabilidad sin sumar etapas incompatibles

Cada iniciativa de inversión transita por registros administrativos distintos que reflejan **etapas diferentes** del ciclo de inversión pública. Sumar montos provenientes de etapas distintas produce doble contabilización e invalida cualquier comparación contra el PIB regional o el presupuesto ejecutado.

```text
[1. Planificación]        [2. Evaluación ex-ante]    [3. Contratación]               [4. Ejecución devengada]
ChileIndica ARI       ->  BIP / SNI (Código IDI) ->  MOP Contratos de Obras      ->  DIPRES Subtítulo 31 / GORE
ChileIndica PROPIR        (Evaluación / RS)          Mercado Público (OCDS/OC)       SINIM (BEP municipal)
                                                                                     [Contraste: SUBDERE FNDR]
```

### Reglas por etapa

1. **Planificación y programación (`ChileIndica ARI` -> `ChileIndica PROPIR`)**
   - **ARI** recoge identificación de necesidades y anteproyecto regional de inversiones.
   - **PROPIR** registra la programación y seguimiento de iniciativas informadas por los servicios en la región.
   - Regla: enlazar ARI con PROPIR para auditar variaciones de cartera, pero **nunca sumar** ambos montos ni tratarlos como ejecución devengada.

2. **Evaluación ex-ante (`BIP / SNI`)**
   - El **Código BIP / IDI** constituye la llave canónica de identidad de las iniciativas de inversión pública.
   - Regla: una ficha IDI o recomendación técnica favorable (`RS`) acredita evaluación, **no desembolso**. Conservar separadas las distintas etapas de un mismo proyecto (prefactibilidad, diseño, ejecución) y registrar explícitamente proyectos multicomunales o multirregionales.

3. **Contratación y adjudicación (`MOP Contratos de Obras` y `Mercado Público / ChileCompra OCDS`)**
   - El visor y servicio geográfico del **MOP** permite enlazar contratos sectoriales de obras por código BIP, conservando vigencia plurianual y modificaciones de contrato.
   - **Mercado Público / ChileCompra OCDS** aporta trazabilidad de licitaciones, adjudicaciones y órdenes de compra (`ocid`, número de licitación y orden de compra).
   - Regla: una licitación adjudicada, contrato de obra u orden de compra acredita contratación o compromiso contractual, **no acredita devengo ni pago**. Mantener separados el identificador de iniciativa (`codigo_bip`) y el identificador contractual (`id_contrato_mop`, `ocid`), y no sumar contratos plurianuales con devengos anuales.

4. **Ejecución presupuestaria devengada (`DIPRES Subtítulo 31`, `GORE`, `SINIM`, contrastado con `SUBDERE FNDR`)**
   - Constituye la única etapa válida para calcular el numerador del cruce `inversion_publica_pib` y para consolidar gasto de capital bruto-a-neto en `pipelines/fiscal/conciliacion.py`.
   - Dentro de esta etapa deben mantenerse separados los estados contables: **inicial**, **vigente**, **compromiso**, **devengo** y **pago**. Cuando un informe SIAP reporte únicamente «ejecutado», se conserva esa etiqueta hasta validar su base contable exacta.
   - Los reportes mensuales de **SUBDERE FNDR** se elaboran sobre cifras de DIPRES y se emplean exclusivamente como **contraste**, contabilizando una sola vez el monto subyacente.

## Llaves de enlace y tratamiento de ambigüedades

- **Identidad de iniciativa**: `codigo_bip_idi` (puente entre ARI/PROPIR, BIP, MOP y DIPRES Subtítulo 31).
- **Identidad contractual**: `id_contrato_mop` y `ocid` / `orden_compra` (Mercado Público), siempre vinculados explícitamente al asiento contable antes de inferir ejecución.
- **Identidad territorial**: código regional y comunal oficial DPA/CUT (`codigo_region`, `codigo_comuna_cut`), separando explícitamente montos `localizado`, `multirregional` y `sin_asignacion`.
- **Enlaces ambiguos**: todo vínculo entre contrato, iniciativa y asiento contable sin identificador documental coincidente queda marcado como pendiente de revisión y excluido de fusiones automáticas por monto o fecha.

## Inventario de fuentes

El archivo [fuentes-inversion.csv](fuentes-inversion.csv) inventaría las siete fuentes oficiales base (`bip-sni`, `chileindica-ari`, `chileindica-propir`, `mop-contratos-obras`, `mercado-publico-ocds`, `subdere-fndr` y `dipres-subtitulo-31`) con su billetera, etapa contable, llave primaria, llave territorial, acceso, periodicidad, límite metodológico y URL oficial HTTPS.

## Verificación

Ejecutar las pruebas unitarias del módulo sin red ni dependencias externas:

```sh
python -m unittest discover -s pipelines/inversion -v
```
