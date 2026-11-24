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
