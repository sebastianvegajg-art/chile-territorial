# Chile Territorial

Observatorio público de inteligencia económica, fiscal y territorial de Chile. Su punto de partida es la pregunta que el dato permite responder. El observatorio permitirá contrastar anuncios y compromisos con evidencia verificable y publicar también los resultados que contradigan una hipótesis.

La cobertura objetivo comprende 16 regiones y 346 comunas, con Aysén y sus 10 comunas como piloto. Las series comenzarán en 2013 según disponibilidad. El seguimiento presupuestario y de gestión abarcará 2025–2028 conforme se publiquen los cortes oficiales.

## Comparador de PIB

El comparador reúne las series de PIB anual real y nominal del Banco Central de Chile para Chile y sus 16 regiones. Permite consultar niveles, crecimiento real, participación regional, series históricas y rankings, además de descargar CSV con el corte de origen. Aysén es la selección regional inicial. La cobertura por actividad económica se aborda en una etapa posterior.

Consulta el [registro de integración](docs/AVANCE_FASE1.md) para reproducir la descarga, cargar PostgreSQL y ejecutar la aplicación local. La [auditoría de calidad](docs/CALIDAD_PIB.md) documenta cobertura, redondeo, revisiones y contrastes.

## Documentación

- [Instrucciones para agentes](AGENTS.md) y [hoja de ruta](ROADMAP.md).
- [Plan maestro](docs/MASTER_PLAN.md) y [decisiones](docs/DECISIONS.md).
- [Arquitectura](docs/ARCHITECTURE.md), [modelo de datos](docs/DATA_MODEL.md) y [metodología](docs/METHODOLOGY.md).
- [Inventario de fuentes](docs/DATA_SOURCES.md), [roles](docs/AGENT_ROLES.md) y [tareas](docs/TASK_BACKLOG.md).

`apps/` contiene API y web. `pipelines/`, `db/` y `data/` separan ingesta, esquema y almacenamiento local. `contracts/` y `tests/` reservan interfaces y verificación. `analytics/`, `research/`, `design/` e `infra/` reservan los demás componentes. Las carpetas vacías incluyen marcadores para conservarlas al versionar.

[.env.example](.env.example) documenta las variables de configuración.
