# Verificación BDE · E01

Desde la raíz, ejecuta `python pipelines/economia/verificar_bde.py` con Python 3.10 o superior. Configura `BCCH_API_TOKEN` mediante el gestor de secretos que inyecta el entorno del proceso. El comando usa el endpoint HTTPS oficial con autenticación en la consulta, deshabilita redirecciones y proxies de entorno, omite URL y cuerpos en errores y rechaza respuestas que reflejen la credencial. Solo realiza consultas de lectura.

El período predeterminado es 2013–2025. `--desde` y `--hasta` aceptan fechas ISO. El comando captura `SearchSeries` con frecuencia anual y consulta `GetSeries` para cada una de las cuatro referencias del inventario. Conserva el cuerpo original y un manifiesto local con SHA-256, títulos, fecha de actualización de catálogo, años sin fila y conteos de estados. El manifiesto solo se escribe al concluir las cuatro verificaciones. Sus conteos se refieren a disponibilidad técnica, no certifican valoración, unidad ni comparabilidad.

La evidencia queda en `data/raw/bde-e01-*`, excluida de Git, con acceso local restringido. Conserva esos insumos para E02. Antes de normalizar contrasta las unidades, la base temporal, los códigos de estado y la cobertura con las notas oficiales.

Pruebas locales sin token ni red:

```sh
python -m unittest discover -s pipelines/economia -v
```

La extracción autenticada sigue pendiente hasta disponer de un token y ejecutar el comando con éxito. Las pruebas unitarias usan respuestas fabricadas y no acreditan conectividad autenticada.

[Documentación oficial REST](https://si3.bcentral.cl/estadisticas/Principal1/Web_Services/documentacion.html)

## Extracción pública de PIB anual

```sh
python -m pipelines.economia.bde_publico
python -m pipelines.economia.bde_publico --reproducir
```

El primer comando descarga dos cuadros de acceso público sin autenticación. Guarda
cada HTML original y un registro de extracción en `data/raw/bde-pib-publico/`.
Genera `data/published/pib-bde-publico.json` con el contrato de datos del MVP. Para
capturar otra versión, asigna rutas nuevas con `--insumos` y `--salida`. El segundo
comando reconstruye el lote desde los bytes y la fecha ya archivados. Los
archivos originales y el lote quedan fuera de Git.

La captura del 24 de noviembre de 2026 contiene 442 niveles, 204 crecimientos
reales anuales disponibles y 208 participaciones nominales. Los 17 crecimientos
de 2013 figuran como faltantes porque ambos cuadros comienzan en 2013. La tabla
de valores reales presenta las series de referencia 2018. Las tablas informan
miles de millones de pesos con cero decimales y el lote multiplica exactamente
por 1.000 para normalizar a millones. El crecimiento y la participación calculados
sobre niveles redondeados pueden diferir de las tasas publicadas por el BCCh.
Los códigos de fila se preservan literalmente. En estos cuadros, el sufijo
`.T` identifica series de origen trimestral mostradas en la vista anual de la
BDE. La vista por región utiliza la geografía de 16 regiones a lo largo de la
serie, incluido el histórico reconstruido de Ñuble y Biobío.

La fecha del lote identifica la extracción. Los HTML carecen de una fecha de
corte estadístico explícita y de marcas de revisión por celda. El estado
`informado` acredita un dato legible en el cuadro. La nota original del PIB
regional de 2025 describió ese lanzamiento como preliminar. Esa nota no permite
asignar el mismo estado a la versión dinámica consultada en noviembre.
Consulta el calendario de revisión y archiva cada descarga antes de comparar
dos versiones.

El Banco Central de Chile es dueño de los datos de origen. La adaptación
corresponde a Chile Territorial y es de su responsabilidad. El conector API
`verificar_bde.py` quedó preparado para una prueba autorizada y el contraste
con los códigos anuales de referencia. Queda pendiente la comparación con las
series u observaciones de la prueba Excel original, cuyo archivo no se recibió.

Fuentes. [Cuadro real](https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL),
[cuadro nominal](https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL_N/637899740344107786),
[nota anual 2025](https://www.bcentral.cl/contenido/-/detalle/prensa/nota-de-prensa/pib-regional-2025),
[calendario de publicación y revisiones](https://www.bcentral.cl/documents/d/banco-central/calendario_cnn_bp),
[términos y atribución BDE](https://si3.bcentral.cl/estadisticas/Principal1/Web_Services/terminos_condiciones.html).

Las [condiciones generales del sitio del Banco Central](https://www.bcentral.cl/web/banco-central/condiciones-de-uso)
permiten la consulta, descarga y uso directo de datos estadísticos de la BDE y
remiten a las condiciones particulares de cada servicio. Los términos
específicos BDE detallan el alcance de la reutilización y la atribución.

### Comprobación preliminar de PIB por actividad

El menú de Cuentas Nacionales expuesto por el cuadro real enlaza 32 cuadros
anuales por actividad y región de referencia 2018, 16 reales y 16 nominales.
La muestra de Arica y Parinacota en volumen fue accesible públicamente y
presentó 13 actividades y la fila separada del PIB total, con códigos BDE
individuales. La actividad agropecuario-silvícola figura como
`F035.PIB.FLU.R.CLP.2018.01.Z.Z.15.0.A`. La muestra ilustra cómo inventariar
los códigos sin inferirlos. Quedan pendientes la extracción y auditoría de
todos los cuadros y el contraste por identificador con el Excel original.
[Cuadro real de Arica y Parinacota por actividad](https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_XV_ACT/637899746466172546).

## Extracción oficial autenticada vía API REST (`bde_api.py`)

El módulo `pipelines/economia/bde_api.py` ejecuta la extracción autenticada de
solo lectura sobre `https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx` sin
dependencias externas adicionales. Admite los dos mecanismos oficiales del BCCh:

- **Token**: `BCCH_API_TOKEN`
- **Usuario y contraseña**: `BCCH_API_USER` + `BCCH_API_PASS`

Las credenciales pueden inyectarse por variables de entorno o cargarse desde un
archivo `.env` local excluido de Git (`.gitignore` ignora `.env` y `.env.*`):

```dotenv
# Opción A: token de API BDE
BCCH_API_TOKEN=tu_token_aqui

# Opción B: usuario y contraseña de API BDE
# BCCH_API_USER=tu_usuario_aqui
# BCCH_API_PASS=tu_clave_aqui
```

Si existen variables de entorno y `.env` simultáneamente, las variables de
entorno tienen precedencia; si se configuran ambos mecanismos, `BCCH_API_TOKEN`
prevalece sobre `BCCH_API_USER`/`BCCH_API_PASS`. El extractor deshabilita
redirecciones y proxies de entorno, nunca registra credenciales en errores,
URLs, manifiestos ni lotes publicados, y rechaza respuestas que reflejen
cualquier credencial.

### Comandos principales

```sh
# 1) Extraer las 34 series anuales de PIB total (Chile + 16 regiones, real y nominal, desde 2012-01-01)
python -m pipelines.economia.bde_api --env .env

# 2) Generar únicamente el inventario reproducible de series sectoriales regionales (416 de referencia)
python -m pipelines.economia.bde_api --env .env --inventario-sectorial

# 3) Ejecutar ambos en una sola sesión (un único SearchSeries para ambos productos)
python -m pipelines.economia.bde_api --env .env --completo

# 4) Comparar el inventario sectorial contra un corte o lista base de identificadores oficiales
python -m pipelines.economia.bde_api --env .env --inventario-sectorial --referencia-sectorial data/published/catalogo-sectorial-base.json

# 5) Reproducir bit-a-bit sin red ni credenciales desde insumos archivados
python -m pipelines.economia.bde_api --reproducir --insumos data/raw/bde-api-<stamp>
python -m pipelines.economia.bde_api --reproducir --completo --insumos data/raw/bde-api-<stamp>
```

### Artefactos producidos

- **Evidencia original (`data/raw/bde-api-*/`)**: guarda los bytes exactos de
  `catalogo-anual.json` (`SearchSeries`, `frequency=ANNUAL`), cada respuesta
  `series/<codigo>.json` (`GetSeries`) y `manifiesto.json` con SHA-256 por
  archivo y URL base sin parámetros de consulta. En `--reproducir`, todos los
  hashes SHA-256 se validan antes de reconstruir.
- **Lote PIB total (`data/published/pib-bde-api.json`)**: cumple estrictamente
  `contracts/pib-datos.schema.json`. Descubre y valida las 34 series totales
  (`CL` con `HIST18` y regiones `01`–`16` referencia `2018`, real y nominal)
  directamente desde `SearchSeries`, convierte exactamente con `Decimal` a
  `millones CLP` preservando todos los decimales entregados por la API, e
  incorpora el nivel real de 2012 cuando existe en la serie para calcular el
  crecimiento real de 2013 (o deja explícito `estado="faltante"` si 2012 no
  está disponible). Distingue cero informado (`"0"`, `statusCode="OK"`) de
  faltante (`statusCode="ND"` o año ausente).
- **Inventario sectorial (`data/published/catalogo-sectorial-bde.json`)**:
  inventaría literalmente las series sectoriales regionales presentes en
  `SearchSeries` sin derivar códigos fuera del catálogo, reporta hashes
  SHA-256, cobertura por región, actividad y valoración, brecha frente a la
  línea base de 416 series (16 regiones × 13 actividades × 2 valoraciones) y,
  cuando se entrega `--referencia-sectorial`, altas, bajas y cambios de
  metadatos por identificador oficial.

### Contraste con los cuadros públicos (`bde_publico.py`)

| Dimensión | Cuadros públicos (`bde_publico.py`) | API oficial (`bde_api.py`) |
|---|---|---|
| Acceso | HTML público sin autenticación | REST oficial (`BCCH_API_TOKEN` o `BCCH_API_USER`+`BCCH_API_PASS`) |
| Precisión de niveles | Miles de millones redondeados a 0 decimales (× 1.000 exacto) | Precisión decimal completa entregada por `GetSeries` (convertida con `Decimal` a `millones CLP`) |
| Códigos de serie | Sufijo `.T` (vista anual de series trimestrales) y `EP18` nacional | Códigos anuales `.A` (`HIST18` nacional y `2018` regional) descubiertos en `SearchSeries` |
| Crecimiento real 2013 | Siempre `faltante` (los cuadros parten en 2013) | Calculado cuando la serie real informa 2012; `faltante` explícito si 2012 no existe |
| Inventario sectorial | Requiere auditar 32 cuadros HTML por región/valoración | Descubrimiento reproducible desde `SearchSeries(frequency=ANNUAL)` con hashes SHA-256 |
| Salida publicada | `data/published/pib-bde-publico.json` | `data/published/pib-bde-api.json` y `data/published/catalogo-sectorial-bde.json` |

### Pruebas unitarias sin red

```sh
python -m unittest discover -s pipelines/economia -v
```

Las pruebas en `test_bde_api.py`, `test_verificar_bde.py` y `test_bde_publico.py`
se ejecutan completamente sin red ni credenciales reales y validan el esquema
`contracts/pib-datos.schema.json`.

