# Plan de evolución y trazabilidad

## Alcance de esta primera etapa

- Reforzar la identidad institucional en la portada y exponer las cinco áreas estratégicas con estados reales.
- Conservar módulos, mapas, lentes, datos, fuentes y metodología existentes.
- Registrar la publicación observada y las cuestiones de conciliación fiscal sin alterar fórmulas ni datos oficiales.
- Mantener el trabajo en una rama independiente; toda publicación o fusión requiere autorización expresa.

## Evidencia de la aplicación publicada

Revisión realizada el 27 de noviembre de 2026 en `https://chile-territorial.netlify.app/#portada` y en rutas públicas de la misma aplicación.

- `/healthz` responde `estado: ok`, servicio `chile-territorial-netlify-api`, `modo: snapshot_oficial_verificado` y publicación PIB `bcch-bde-api-2026-11-24-66e9899b3037a598`.
- `/api/v1/publicaciones` identifica una publicación BCCh-BDE del 24-11-2026, con 855 de 871 observaciones (98,16%) y el mismo identificador de generación. Esto es evidencia pública de que la API expone una publicación verificada en modo snapshot.
- El endpoint público no permite probar de forma concluyente si existe además un backend upstream activo mediante `BACKEND_API_URL`, pues la variable y los metadatos privados del despliegue Netlify no son visibles.
- No fue posible identificar el SHA exacto desplegado. Los nombres de activos JS/CSS publicados (`index-C4JA_sll.js`, `index-Brxw4hiw.css`) difieren de los producidos localmente desde el `main` revisado (`index-C7cihoLf.js`, `index-B7RU1Pqp.css`). Esta diferencia demuestra que los artefactos no son idénticos; por sí sola no identifica el commit de producción.

Conclusión limitada: hay evidencia verificable de modo snapshot en el endpoint público; no hay acceso suficiente para acreditar el commit de Netlify ni excluir una configuración adicional de backend. La reconciliación requiere acceso de solo lectura al panel o metadatos de despliegue y configuración de entorno.

## Inconsistencias fiscales que requieren conciliación

Los valores siguientes se documentan como observaciones de auditoría sobre pantallas y snapshot revisados. No son una corrección ni una validación de cifras oficiales.

| Distinción necesaria | Hallazgo y tratamiento requerido |
|---|---|
| Arrastre entre administraciones | Pregunta política: identificar fecha de inicio de administración, contratos/proyectos contratados antes de esa fecha y pagos posteriores. Es distinta del saldo anual presupuestario no ejecutado. No atribuir pagos a la administración que contrató la obra ni a la que los pagó sin mostrar ambas fechas. |
| Arrastre presupuestario entre ejercicios | Pregunta fiscal: recursos, compromisos o proyectos que continúan de un ejercicio a otro. La vista de proyectos mostró $139.963 millones sobre $156.544 millones (89,4%) para el corte presentado. El resumen público mostró 94,9% y $5.529 millones; el snapshot revisado en `main` mostraba, en cambio, 89,41%, $139.963 millones y $156.544 millones en el resumen y en proyectos. Los universos/definiciones detrás de los $5.529 millones no quedan conciliados con evidencia disponible; no deben compararse como la misma medida hasta conocer numerador, denominador, corte y etapa. |
| Presupuesto inicial y vigente | El inicial es la autorización al inicio del ejercicio; el vigente incorpora modificaciones presupuestarias a un corte. Reportarlos por separado, con fuente, institución, clasificador, fecha y universo homogéneos. Un vigente no equivale a caja disponible. |
| Compromisos, devengos y pagos | El compromiso reserva o formaliza obligaciones; el devengo reconoce obligación por bienes/servicios recibidos; el pago registra salida de caja. No son intercambiables. Mostrar etapa, corte y desfases. El saldo no comprometido requiere compromisos pendientes completos; si faltan, informar solo vigente menos devengo como saldo por devengar, con advertencia. |
| Sumas brutas y consolidadas | La pantalla presupuestaria presenta $545.070 millones como total “consolidado”, sumando Gobierno Central $381.693 millones, GORE $79.897 millones y municipios $83.480 millones, y advierte que no se han eliminado transferencias internas. Hasta conciliar transferencias entre financiador y receptor, el total debe entenderse como suma bruta y no como gasto público consolidado. |

La metodología vigente en [METHODOLOGY.md](METHODOLOGY.md) ya exige identificar el perímetro fiscal, separar etapas y eliminar solo transferencias internas conciliadas. La discrepancia reportada requiere recuperar definición, consulta, datos de entrada, corte y commit de cada pantalla antes de proponer cambios.

## Secuencia posterior sugerida

1. Recuperar metadatos verificables de Netlify y enlazar cada publicación a un SHA, sin modificar producción.
2. Reproducir las cifras presupuestarias por pantalla desde sus fuentes y registrar filtros, cortes, etapas, denominadores y unidades.
3. Diseñar una conciliación bruta a neta con identificadores de transferencia, financiador, receptor, ejecutor y devengo final; publicar cobertura y partidas no conciliadas.
4. Presentar una propuesta metodológica al fundador antes de modificar fórmulas o datos.
5. Evaluar de forma incremental cobertura municipal, investigación y laboratorio, manteniendo estados y alternativas explícitas.

## Decisiones pendientes

- Acceso de solo lectura al registro de despliegues Netlify para identificar el SHA publicado y las variables de entorno relevantes, sin exponer secretos.
- Definición y trazabilidad del indicador público que muestra $5.529 millones/94,9% frente a la vista de proyectos.
- Validación de universos y transferencias para denominar consolidado al agregado presupuestario.
- Criterios institucionales para cuándo un piloto pasa a operativo.
