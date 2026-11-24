# Arquitectura aprobada

## Componentes y alternativas

React con TypeScript permite un comparador interactivo y accesible con tipos generados desde OpenAPI. Vite simplifica el desarrollo de una aplicación de página única. Evaluar renderizado en servidor si la indexación de fichas se vuelve prioritaria. Una web estática con CSV sería suficiente para una demostración de PIB, pero la consulta versionada, la auditoría y la expansión fiscal justifican API y almacenamiento relacional.

Python concentra ingesta, validación y análisis. FastAPI ofrece validación tipada y un contrato OpenAPI consumible por el frontend. Django sería razonable si un panel administrativo y permisos editoriales complejos pasan a ser centrales. PostgreSQL conserva integridad referencial, transacciones y concurrencia para datos revisables. DuckDB es una opción para análisis local y validación de archivos, con PostgreSQL como registro de publicación. Se propone un monolito modular, procesos de carga independientes y ejecución local con contenedores reproducibles. El programador del entorno podrá ejecutar comandos idempotentes cuando se autorice su operación. Una cola se evaluará cuando volumen o duración lo justifiquen.

## Flujo y operación

1. Descargar por lote con límites de la fuente, tiempo máximo y reintento acotado para fallas transitorias. Registrar identificador de ejecución y manifiesto con hash. Quitar parámetros sensibles de URLs registradas. En local, conservar insumos fuera de Git.
2. Validar esquema, identidad, cobertura y consistencia de valores. Aislar archivos o filas con fallas, registrar causa y alertar por deriva del esquema. Mantener los faltantes legítimos con estado.
3. Cargar con claves naturales y comparar cambios frente al corte anterior. Publicar dentro de una transacción con exclusión de promociones concurrentes por conjunto; conservar el último corte aprobado ante fallas. Asignar a cada publicación un manifiesto inmutable.
4. Servir vistas de solo lectura por corte explícito o por la última versión aprobada. API y frontend conservan el identificador devuelto al navegar, comparar y descargar. Separar permisos de ingesta y consulta.

## Contrato inicial

La especificación versionada, el esquema de datos y el ejemplo sintético están en [contratos del MVP](../contracts/README.md).

| Operación | Parámetros y salida |
|---|---|
| `GET /api/v1/territorios` | Nivel nacional o regional, vigencia y código oficial |
| `GET /api/v1/publicaciones` | Identificador, fecha, estado, cobertura, cambios y fuente |
| `GET /api/v1/pib` | Territorios, año inicial/final, valoración, métrica y publicación, con paginación y orden estable |
| `GET /api/v1/pib.csv` | Mismos filtros, todo el resultado filtrado dentro de límites documentados |
| `GET /api/v1/observaciones/{id}/procedencia` | Código oficial, corte, fechas, referencia de origen y versión de cálculo |

Cada fila devuelve identificador, período, territorio, indicador, valor decimal como texto o nulo, unidad, valoración, año de referencia si aplica, estado y publicación. El crecimiento pide valoración real y la participación pide nominal. Validar combinaciones, años y límites, y documentar errores en OpenAPI. Los faltantes pueden retornar filas con valor nulo y estado. Una consulta válida sin resultados devuelve una colección vacía. Un corte inexistente devuelve 404.

Frontend con tabla semántica y gráfica equivalente, estados de carga y error, filtros accesibles y adaptación móvil. Probar teclado, lectores de pantalla, contraste y tamaños de pantalla. La fuente y el corte deben quedar visibles y en CSV. Los cálculos tienen una definición compartida y se ejecutan en backend o en la capa publicada.

La futura asistencia de IA consultará vistas publicadas de solo lectura, conservará citas y supuestos y requerirá revisión humana antes de publicar. Puerto, infraestructura y destino de despliegue se decidirán tras la autorización correspondiente.
