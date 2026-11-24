# Finanzas públicas · agente 03

**Activación.** Tras autorización, inicia F01 con [fuentes](../DATA_SOURCES.md), [modelo](../DATA_MODEL.md) y [metodología](../METHODOLOGY.md). F02 requiere F01 y G01. Escribe solo en `pipelines/fiscal/**`, incluidas pruebas. Las fuentes fiscales quedan fuera de la API PIB v0.1.

1. Inventaría ejercicios y cortes disponibles desde 2025 para Aysén, diferenciando las tres billeteras, fuentes y condiciones de uso. Verifica alcance, institución, clasificación, etapa, moneda y localización.
2. Distingue inicial, vigente, compromisos, devengos y pagos. Identifica flujos internos y conserva evidencia de conciliación, montos brutos y netos, partidas no asignadas y residuales. Cuando falte información de compromiso, documenta el faltante y conserva el saldo por devengar separado.
3. Prueba conciliación parcial, transferencia sin pareja, devengo/pago en cortes distintos y conservación del monto tras reparto territorial.

**Entrega.** Inventario, reglas reproducibles, pruebas y matriz de cobertura. Coordina el enlace a proyectos con 04 y las migraciones con 01.
