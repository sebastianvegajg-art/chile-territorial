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
