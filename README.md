# Chile Territorial

Observatorio público de inteligencia económica, fiscal y territorial de Chile. Su punto de partida es la pregunta que el dato permite responder. El observatorio permitirá contrastar anuncios y compromisos con evidencia verificable y publicar también los resultados que contradigan una hipótesis.

La cobertura objetivo comprende 16 regiones y 346 comunas, con Aysén y sus 10 comunas como piloto. Las series comenzarán en 2013 según disponibilidad. El seguimiento presupuestario y de gestión abarcará 2025–2028 conforme se publiquen los cortes oficiales.

## Primera versión funcional definida

Consultas de PIB anual real y nominal nacional y regional, comparación de las 16 regiones, crecimiento real, participación nominal y exportación CSV con procedencia. Aysén será la selección regional inicial. La incorporación de las 13 actividades económicas vendrá en una segunda entrega. Este repositorio contiene los cimientos documentales y la estructura de trabajo.

## Documentación

- [Instrucciones para agentes](AGENTS.md) y [hoja de ruta](ROADMAP.md).
- [Plan maestro](docs/MASTER_PLAN.md) y [decisiones](docs/DECISIONS.md).
- [Arquitectura](docs/ARCHITECTURE.md), [modelo de datos](docs/DATA_MODEL.md) y [metodología](docs/METHODOLOGY.md).
- [Inventario de fuentes](docs/DATA_SOURCES.md), [roles](docs/AGENT_ROLES.md) y [tareas](docs/TASK_BACKLOG.md).

`apps/` contiene API y web. `pipelines/`, `db/` y `data/` separan ingesta, esquema y almacenamiento local. `contracts/` y `tests/` reservan interfaces y verificación. `analytics/`, `research/`, `design/` e `infra/` reservan los demás componentes. Las carpetas vacías incluyen marcadores para conservarlas al versionar.

En la fase de implementación se prepararán la configuración local y los comandos reproducibles. [.env.example](.env.example) documenta la configuración propuesta.
