# Backend · agente 08

**Activación.** Inicia B01 con la autorización y el [contrato y fixture](../../contracts/README.md). Coordina fórmulas con M01 y conecta persistencia al completar A03. Escribe solo en `apps/api/**`, incluidas pruebas.

1. Implementa las cinco rutas del OpenAPI. Usa el esquema común para campos, errores, filtros, límites y orden.
2. Fija el corte entre consulta, paginación y CSV. Excluye pruebas del entorno de producción. Devuelve procedencia saneada y conserva nulos y ceros.
3. Prueba ausencia de corte, combinaciones inválidas, límites, filtros, empate de fecha, paginación, formato CSV y coherencia con el resultado JSON. Verifica separación de lecturas y promoción.

**Entrega.** API, comandos locales, pruebas con fixture y evidencia de conformidad. Solicita a 01 los cambios a contratos, migraciones y pruebas compartidas.
