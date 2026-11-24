# Calidad y cobertura del PIB oficial

Auditoría independiente actualizada el 24 de noviembre de 2026 (ejecución de contraste en vivo sobre el corte local `bcch-bde-publico-2026-11-24-e8fd733c80631c45`, y consistente con el corte previo `bcch-bde-publico-2026-11-24-8495c73d852708e5`). El alcance cubre PIB anual total de Chile y las 16 regiones entre 2013 y 2025. [Cuadro real BDE](https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL), [cuadro nominal BDE](https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL_N/637899740344107786).

| Serie o indicador | Ámbito | Filas | Con valor | Faltantes |
|---|---|---:|---:|---:|
| Nivel real, referencia 2018 | Chile y 16 regiones | 221 | 221 | 0 |
| Nivel nominal, precios corrientes | Chile y 16 regiones | 221 | 221 | 0 |
| Crecimiento real anual calculado | Chile y 16 regiones | 221 | 204 | 17 |
| Participación nominal calculada | 16 regiones | 208 | 208 | 0 |
| **Total** | **2013–2025** | **871** | **854** | **17** |

Los 17 faltantes corresponden al crecimiento de 2013. El cuadro comparado empieza en 2013 y el cálculo requiere un nivel de 2012 compatible. Los niveles nominales y reales suman 34 combinaciones territorio–valoración completas. Las 416 series sectoriales identificadas en la prueba Excel corresponden a otra cobertura. Queda pendiente contrastar con ese libro y con la API autenticada.

## Verificación de fuente, cálculo y revisión

- Las 442 celdas coincidieron exactamente con una segunda descarga analizada con un lector independiente. Se cotejaron los códigos tal como aparecen en cada cuadro, la unidad, el año y la huella SHA-256 de cada original usado para generar el lote. El código de serie del cuadro puede terminar en `.A` o `.T`. El período observado es el año de la columna publicada. Por ejemplo, Aysén real 2025 proviene de `F035.PIB.FLU.R.CLP.2018.Z.Z.Z.11.0.T` y el código del total nacional real es `F032.PIB.FLU.R.CLP.EP18.Z.Z.0.T`.
- El Banco Central muestra niveles en miles de millones de pesos con cero decimales. El lote conserva esa precisión y expresa los niveles en millones de CLP al multiplicar por 1.000. Aysén 2025 registra 1.431.000 millones de CLP reales y 1.991.000 millones nominales. Chile registra 215.645.000 millones reales y 339.978.000 millones nominales. Las cifras reales se encadenan con referencia 2018. La participación divide por el total nominal nacional del mismo cuadro, que incluye partidas extrarregionales.
- Se verificaron 429 filas derivadas, incluidos los 17 faltantes con motivo. Se reprodujeron 204 crecimientos y 208 participaciones a partir de sus insumos. Aysén en 2025 crece aproximadamente 8,49% y representa aproximadamente 0,59% del PIB nominal nacional. Las cifras derivadas conservan decimales para reproducir los cálculos. Su precisión económica depende de la de los niveles.
- Los 17 crecimientos de 2025 tienen el mismo signo que en la nota anual del Banco Central. La mayor diferencia absoluta del cálculo a partir de niveles públicos redondeados es 0,05746 puntos porcentuales en Tarapacá, −8,35746% frente a −8,3% en la nota. Aysén coincide a una cifra decimal con el 8,5% de la nota. La discrepancia puede reflejar el redondeo y las revisiones de la fuente. [Nota de PIB regional del 23 de abril de 2026](https://www.bcentral.cl/contenido/-/detalle/prensa/nota-de-prensa/pib-regional-2025).
- La nota anual presenta 2025 como preliminar y describe revisiones de las series regionales. La fecha registrada en el lote corresponde a la extracción local. Los cuadros consultados carecen de fecha de revisión por celda. La comparación histórica de Ñuble y Biobío usa el empalme del Banco Central en los cuadros de referencia 2018 y conserva su clasificación territorial. Las tasas describen cambios observados sin atribuir causas a gobiernos, políticas o acontecimientos. [Política de publicaciones y revisiones](https://www.bcentral.cl/documents/d/banco-central/calendario_cnn_bp).

## Persistencia, aplicación y descarga

- La carga PostgreSQL fue repetible. La suite de persistencia comprobó migración y carga idempotentes, reversión de lote inválido, permisos del lector y rechazo de datos sintéticos en la base de cortes aprobados.
- En la auditoría del corte `bcch-bde-publico-2026-11-24-e8fd733c80631c45`, el cargador validó el contrato JSON Schema y las huellas SHA-256 de ambos HTML originales (`Contrato y huellas validados`), y el modo de lectura local validado (`CT_LOTE_OFICIAL`) entregó las 871 filas (221 reales, 221 nominales, 221 crecimientos con 17 nulos explícitos de 2013 y 208 participaciones) con coincidencia exacta entre lote, API JSON, descarga CSV y procedencia.
- El paquete autónomo `data/published/Chile_Territorial_Oficial.html` (953.871 bytes) fue regenerado contra la API oficial en vivo incluyendo los 17 territorios, la publicación aprobada (con cobertura y notas de versión), las 871 observaciones y sus 871 registros de procedencia, sin datos sintéticos.
- La suite automatizada completa superó 87 pruebas activas (`20` economía territorial, `26` Banco Central con conector API `bde_api.py` preparado para credenciales `.env`, `13` finanzas públicas, `6` inversión, `16` API/cargador y `6` auditoría HTTP caja negra Q01), además de la compilación `tsc && vite build`. Las 2 pruebas de PostgreSQL (`test_publicacion_postgres.py`) permanecen activables al configurar una instancia local con `DATABASE_URL`.
- Playwright y Chromium locales verificaron la app y el HTML autónomo en contexto sin conexión. En ambos casos se comprobaron las 17 series comparadas, 221 niveles en CSV, 136 índices recalculados con base 2018, ranking, procedencia, vista de 360 px y manejo del foco con teclado. El navegador compartido de la conversación no estuvo disponible. La evaluación con lectores de pantalla asistivos queda pendiente.

## Verificación con API autenticada del Banco Central (`bcch-bde-api-2026-11-24-66e9899b3037a598`)

El 24 de noviembre de 2026 se ejecutó la extracción oficial autenticada contra `https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx` (`SearchSeries` anual + 34 consultas `GetSeries` 2012–2025) mediante `python -m pipelines.economia.bde_api --env .env --completo`, verificando además reproducción bit-a-bit sin red (`--reproducir`). Las respuestas de la API utilizan codificación `ISO-8859-1`, normalizada a UTF-8 en la ingesta; los originales y credenciales quedan fuera de Git.

- **Cobertura del corte API oficial**: **871 observaciones publicables (2013–2025)**, de las cuales **855 tienen valor** y **16 son faltantes explícitos** (crecimiento real 2013 de las 16 regiones, cuyas series regionales oficiales comienzan en `01-01-2013`). A diferencia de los cuadros públicos, la serie histórica nacional `F032.PIB.FLU.R.CLP.HIST18.Z.Z.0.A` aporta el nivel real auxiliar de 2012 (`164.423,907015138` miles de millones CLP, actualizado el `18-03-2026`), permitiendo calcular con linaje exacto el crecimiento real 2013 de Chile (`3,31%`, exacto `3.308508...%`).
- **Conciliación exacta contra cuadros públicos BDE**: los 442 niveles anuales 2013–2025 de la API (con precisión decimal plena de 9 a 12 dígitos), redondeados al millar de millones más cercano, presentan una **diferencia máxima de 0 millones CLP** respecto de los cuadros públicos HTML.
- **Conciliación exacta contra la nota anual 2025 del Banco Central**: con la precisión decimal completa de la API, **las 17 tasas de crecimiento real 2025 (Chile y 16 regiones) coinciden exactamente a una cifra decimal (`0` discrepancias)** con la nota oficial del 23 de abril de 2026 (diferencia absoluta máxima `0,0496` pp, estrictamente atribuible al redondeo a un decimal de la nota de prensa). En Aysén 2025: PIB real `1.430.527,610188` millones CLP, nominal `1.990.584,3398972` millones CLP, crecimiento real `8,49%` (`8,5%` en la nota) y participación nominal `0,59%`.
- **Inventario reproducible de series sectoriales (`bcch-bde-sectorial-2026-11-24-d56997ee753ef473`)**: sobre 5.812 series anuales del catálogo BDE se verificaron exactamente **416 series sectoriales regionales** (`208` reales + `208` nominales; **16 de 16 regiones** con exactamente 13 actividades reales y 13 nominales = 26 series por región, `diferencia_total = 0`). El catálogo confirmó una heterogeneidad real de sufijos de código en Tarapacá (`.21.Z` en 7 actividades reales y 8 nominales frente al código base en las demás regiones), validando la regla metodológica de mapear códigos literalmente desde `SearchSeries` sin inferirlos por patrón.
- **API oficial y HTML autónomo regenerados**: `apps/api` en modo `CT_LOTE_OFICIAL` sirvió las 871 observaciones publicables y sus procedencias (incluido el insumo auxiliar 2012 para `CL.2013.crecimiento.real`) con paridad exacta JSON/CSV, y se regeneró `data/published/Chile_Territorial_Oficial.html` (968.203 bytes) con el corte de precisión plena `bcch-bde-api-2026-11-24-66e9899b3037a598`.

## Reproducción

Con el lote y sus originales en las rutas indicadas, instala en tu entorno de auditoría `beautifulsoup4` y `jsonschema`. Inicia la aplicación oficial con la conexión de solo lectura según el [README](../README.md). Ejecuta estos comandos desde la raíz del repositorio.

```sh
python -m pip install beautifulsoup4 jsonschema
fuentes_auditoria=$(mktemp -d)
base_bde=https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76
curl -fsSL "$base_bde/CCNN2018_PIB_REGIONAL" -o "$fuentes_auditoria/real.html"
curl -fsSL "$base_bde/CCNN2018_PIB_REGIONAL_N/637899740344107786" -o "$fuentes_auditoria/nominal.html"
python tests/auditoria/contrastar_pib_oficial.py \
  data/published/pib-bde-publico.json "$fuentes_auditoria" data/raw/bde-pib-publico \
  --api http://127.0.0.1:8000/api/v1
```

El contraste con la descarga en vivo revelará cualquier diferencia si el Banco Central revisa los datos. Las copias exactas de cada extracción y sus manifiestos permiten reproducir el corte sin conexión.

Para comprobar el frontend oficial y el HTML generado, instala también `playwright` y configura un Chromium local con `CT_CHROMIUM` o instala Chromium para Playwright con `python -m playwright install chromium`.

```sh
python tests/auditoria/comparador_oficial_browser.py \
  data/published/pib-bde-publico.json --html data/published/Chile_Territorial_Oficial.html
```
