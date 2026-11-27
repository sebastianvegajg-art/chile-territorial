# Instrucciones para agentes de Chile Territorial

Trabaja en español, dentro de los archivos asignados en [roles](docs/AGENT_ROLES.md) y conforme a los criterios del [backlog](docs/TASK_BACKLOG.md). El coordinador integra cambios de contratos, migraciones compartidas, asignaciones y decisiones. Antes de implementar una modificación de contrato, acuerda con el coordinador el cambio y la verificación de compatibilidad. Mantén revisiones pequeñas y anuncia conflictos antes de editar archivos de otro rol.

- Registra fuente oficial, versión, corte, extracción, unidad y método para cada observación. Conserva el insumo original y el vínculo auditable a la transformación.
- Distingue observaciones oficiales, estimaciones, proyecciones e hipótesis. Incluye evidencia favorable y contraria y declara límites de inferencia. Una correlación exige una estrategia adicional para atribuir causalidad.
- Diferencia valores nominales y reales, documenta fórmulas y respeta la no aditividad de volúmenes encadenados. Controla cambios geográficos, series revisadas y rupturas metodológicas.
- Distingue cero informado, faltante, supresión, no aplicabilidad y error. Registra y aísla fallas de ingesta. Conserva los descartes y su motivo fuera de la publicación.
- Identifica perímetro fiscal, etapa contable y transferencias internas antes de agregar. Presenta cobertura y partidas sin asignación territorial.
- Usa credenciales solo en ejecución del conector. Exclúyelas de Git, consultas registradas, exportaciones y frontend. Respeta condiciones de reutilización y minimiza datos personales.
- Valida la disponibilidad y cobertura de cada fuente antes de declarar una integración operativa. Registra evidencia reproducible de la prueba con fecha y sin secretos.
- Implementa pruebas automatizadas de regresión, deduplicación, revisiones, faltantes, contratos y fórmulas donde corresponda. Entrega resultados verificables, referencias, supuestos y pendientes.
- Diseña para teclado, lectores de pantalla, móvil y lectura clara. Ofrece tablas equivalentes a los gráficos y explica el significado de cada indicador.
- La arquitectura común está aprobada. Inicia la implementación paralela cuando el titular autorice activar los agentes. Aplica la [matriz de archivos compartidos](docs/AGENT_ROLES.md). El despliegue público, contratación y modificación de recursos externos requieren autorización expresa.

## Memoria institucional de Confía Sur

Aplica estas referencias junto con las instrucciones técnicas anteriores:

- [Identidad institucional](docs/IDENTIDAD_INSTITUCIONAL.md): propósito, públicos y lenguaje institucional.
- [Sistema visual](docs/SISTEMA_VISUAL.md): paleta, tipografías, componentes y continuidad gráfica.
- [Contexto estratégico](docs/CONTEXTO_ESTRATEGICO.md): áreas estratégicas, funcionalidades y estados reales.
- [Plan de evolución](docs/PLAN_EVOLUCION.md): trazabilidad pública, límites metodológicos y etapas de trabajo.

Describe cada capacidad como operativa, piloto o en desarrollo según evidencia presente en el código y las fuentes. No atribuyas capacidades futuras a módulos existentes. No llames consolidado a un total fiscal si no se han identificado y conciliado transferencias internas. La identidad institucional orienta la evolución, pero no autoriza a sustituir módulos, metodologías ni datos.
