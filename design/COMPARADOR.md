# Diseño del comparador regional · D01

El [prototipo HTML](comparador.html) demuestra el flujo de selección, comparación, tabla, procedencia y descarga. Puede abrirse directamente. Sus cifras son ilustrativas. La implementación deberá consumir el [contrato v0.1.0](../contracts/README.md) y usar el catálogo de territorios de la API.

## Flujo principal

1. Abrir el comparador con Aysén y la referencia Chile para la vista de nivel. Seleccionar el intervalo disponible en el último corte aprobado. En la modalidad de prueba, identificar el corte sintético en todo momento.
2. Consultar valores nominales, reales, crecimiento real o participación en el PIB nacional. Mostrar la valoración y la unidad efectivas. La participación admite únicamente regiones. Al cambiar a participación, deshabilitar Chile y explicar la restricción junto al control.
3. Añadir regiones desde un selector con las 16 opciones y conservar todas las selecciones en la tabla. En la gráfica se pueden destacar hasta cuatro regiones, más Chile cuando aplique. Si hay más, indicar cuántas se muestran y permitir elegir cuáles destacar. Las selecciones de la gráfica no condicionan la exportación.
4. Mostrar los años consecutivos del intervalo y mantener los huecos sin unir tramos separados por nulos. Presentar cero como valor informado. Usar un gráfico temporal con marcas para cada punto, unidad en el eje y etiquetas legibles. En la tabla, ordenar por año y código territorial como la API, con un vínculo de procedencia por fila.
5. Mantener fijo el identificador de publicación al paginar y descargar, incluso si aparece un nuevo corte. La acción «Descargar CSV» usa el filtro aplicado y todas sus filas, incluidas las que están fuera de la página visible.

## Diseño visual y adaptable

- Fondo arena claro `#f3f0e9`, paneles blancos, texto verde oscuro `#112b29`, controles activos `#08785e`, texto secundario `#485d57` y bordes `#becbc5`. Usa una tipografía sans serif de sistema con números tabulares en la tabla.
- Escritorio: filtros en columna de 270–300 px y resultado en el área principal. El encabezado y el corte ocupan el ancho del contenido. Móvil: una columna desde 760 px, filtros antes de resultados, controles de al menos 44 px y desbordamiento lateral confinado a la tabla.
- Titular «Comparador regional» y rótulo corto para la métrica aplicada. La procedencia se consulta desde cada fila. Conservar el subtítulo solo cuando haga falta aclarar unidad, base de referencia o alcance.
- La leyenda combina color, rótulo visible y estilo de marca. Los nombres de región permanecen disponibles en tabla y leyenda. No depender del color para señalar valores o estados.

## Estados de la consulta

| Estado | Interfaz | Acción |
|---|---|---|
| Carga | Conservar visibles los filtros y anunciar «Consultando datos» con una región de estado cortés. Mantener identificado el resultado previo hasta que se aplique la consulta nueva | Al finalizar, anunciar el total y actualizar corte y resultado juntos |
| Vacío | «No hay observaciones para esta selección» e indicar el período consultado | Ajustar los filtros |
| Falla de red | «No se pudo consultar el PIB» y conservar filtros y último resultado válido | Reintentar la consulta |
| Corte no disponible | «El corte solicitado no está disponible» | Elegir una publicación disponible o volver a cargar el último corte aprobado |
| Dato sin valor | Mostrar «Faltante», «Suprimido», «No aplicable» o «Error», según estado | Consultar la causa por fila |
| Dato disponible | Mostrar valor, unidad y etiqueta «Oficial», «Calculado a partir de datos oficiales», «Estimación» o «Prueba». Añadir «Preliminar» cuando aplique | Consultar procedencia |

## Verificación para frontend

- Con Tab y Mayús+Tab, acceder a los filtros, aplicar, CSV, tabla y vínculos de procedencia. Mantener foco visible. Los botones y campos tienen nombres accesibles y se operan con teclado nativo.
- A 360 px, leer encabezado, filtros y estados sin desbordamiento horizontal de página. Desplazar la tabla dentro de su contenedor cuando sea necesario.
- Recorrer la selección Aysén → segunda región → participación → descarga y comprobar que el CSV conserva filtros y corte. Probar cero, faltante, estado vacío y fallo de red por separado.
- Verificar que un lector de pantalla pueda obtener los valores y su estado desde la tabla, incluso cuando no estén en la selección visual de la gráfica.
