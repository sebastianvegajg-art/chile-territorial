# Plan maestro

## Propósito y alcance

Chile Territorial convierte fuentes oficiales dispersas en respuestas auditables. Cada investigación comienza con pregunta, población, territorio, período y criterio de contraste. La ficha pública enlaza la formulación del anuncio, fecha, métrica verificable, evidencia favorable y contraria, cobertura y conclusión revisable. Si la información disponible no permite decidir, registra qué evidencia falta.

La cobertura objetivo incluye 16 regiones y 346 comunas. Aysén parte con Coyhaique, Lago Verde, Aysén, Cisnes, Guaitecas, Cochrane, O’Higgins, Tortel, Chile Chico y Río Ibáñez. Se abordarán series desde 2013 según disponibilidad y seguimiento 2025–2028 por corte, incluyendo años futuros solo como planificación o escenarios hasta contar con ejecución observada.

| Dimensión | Pregunta inicial | Requisito para publicar |
|---|---|---|
| Crecimiento y especialización | ¿Cómo crecen Chile y sus regiones y qué actividades explican su estructura productiva? | Series comparables, unidades y valoración |
| Trabajo, remuneraciones y productividad | ¿Cómo evolucionan empleo público y privado, ingresos reales y producto por hora? | Dominios muestrales, horas y deflactor |
| Estado, presupuesto e inversión | ¿Cuánto se ejecuta, dónde y mediante qué fuentes de financiamiento? | Perímetro, etapas y eliminación de duplicidades |
| Gestión y bienestar | ¿Cuánto cuesta entregar prestaciones y qué cobertura y resultados se observan? | Criterios de atribución, población elegible y equivalencia |
| Escenarios | ¿Cómo cambian PIB e inversión bajo supuestos alternativos? | Escenario base, incertidumbre y evaluación retrospectiva |

## Producto inicial

Tablero nacional y comparador regional con selector de año, región y tipo de medida, gráfica y tabla, detalle de unidad y revisión, descarga CSV y estados de faltantes. La comparación admite las 16 regiones y la referencia nacional. Aysén abre el detalle territorial. El historial de PIB comunal queda fuera del producto inicial. Los cruces fiscales, sectoriales y de inversión se incorporan por etapas.

La prueba Excel/Power Query reporta PIB anual nacional y regional real y nominal 2013–2025, catálogo anual, 416 series sectoriales identificadas y 52 series con 676 observaciones en Aysén y Los Lagos. El adjunto contiene la descripción, sin libro ni extractos. Reproducir y conciliar la extracción antes de publicar. La recuperación de las otras 14 regiones es un hito posterior. Las 416 series identificadas son la línea base de la prueba. Las altas, bajas y cambios de metadatos del catálogo se registrarán por corte.

## Gobierno del proyecto

El coordinador mantiene [decisiones](DECISIONS.md) y [contratos](../contracts/README.md). Cada responsable entrega con evidencia y auditoría revisa en forma independiente. Los hitos se aceptan mediante matriz de cobertura, pruebas y revisión de metodología. Las correcciones generan una nueva versión publicada con registro del cambio. La autorización de despliegue se decide por separado.

Dependencias críticas: acceso BDE vigente, catálogo y códigos territoriales oficiales, comparabilidad histórica de Ñuble y Biobío, granularidad fiscal conciliable, restricciones de reutilización y localización de la ejecución. El piloto fiscal cuantificará filas y montos asignados, multirregionales y sin asignación.
