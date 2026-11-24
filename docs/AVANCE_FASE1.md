# Avance de la primera fase

## Reactivación del 24 de noviembre de 2026

`fase1/integracion-oficial` parte del PR #10 (`b3145c3`) e incorpora el commit de `demo/preview-v0.2.0`. Se revisaron 12 ramas y los PR #1 a #10. `main` conserva la arquitectura `v0.1.0`. La rama de la demo aportaba una presentación descargable con datos sintéticos. Las referencias revisadas no contenían una carga oficial posterior.

| Frente | Resultado en la rama de integración |
|---|---|
| Recuperación y arquitectura | Base común con las contribuciones previas, arranque local explícito y contratos v0.1.0. |
| Banco Central | Ingesta de los cuadros públicos de PIB anual real y nominal, conservación de originales, códigos BDE y huellas. La igualdad a precisión de serie con la API autenticada y el Excel experimental queda por verificar. |
| Economía territorial | Fórmulas, linaje y pruebas para crecimiento acumulado, índice histórico y ranking. Los indicadores sectoriales quedan definidos a la espera de datos comparables. |
| Frontend | Selección múltiple, navegación por año e historial, rankings y descargas con corte de origen. Demostración autónoma regenerable con el mismo corte. |
| Backend y almacenamiento | Cargador que valida esquema y huellas antes de cargar el corte oficial en PostgreSQL. FastAPI sirve los datos y la procedencia con roles separados. |
| Finanzas públicas | Inventario y cuatro cruces del piloto de Aysén, con límites de cobertura y conciliación en [el registro fiscal](../pipelines/fiscal/README.md). |
| Auditoría | Cobertura, contraste de cifras, revisión de fórmulas y pruebas de integración en [calidad del PIB](CALIDAD_PIB.md). |

## Ejecución local con datos oficiales

Desde la raíz, prepara las dependencias:

```sh
python -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt
npm --cache "${TMPDIR:-/tmp}/ct-npm" ci --prefix apps/web
```

Sigue la [ingesta pública](../pipelines/economia/README.md) para obtener el lote y sus originales en `data/`. Inicializa PostgreSQL con `PIB_DB_MODE=aprobada infra/pib-db.sh iniciar` y la configuración descrita en [infraestructura](../infra/README.md). Con `DATABASE_URL` de ingesta, carga el lote según las [instrucciones de la API](../apps/api/README.md).

Cambia `DATABASE_URL` a la conexión de lectura y ejecuta `CT_PYTHON=.venv/bin/python infra/demo-local.sh oficial`. Abre `http://127.0.0.1:5173`. Los archivos oficiales quedan en el directorio de datos local, fuera de Git. El CSV de la aplicación identifica el corte usado para consultarlos.

Con la API activa, exporta la versión autónoma desde la raíz:

```sh
npm --prefix apps/web run build
node apps/web/scripts/export-html.mjs data/published/Chile_Territorial_Oficial.html
```

Abre el archivo en un navegador o usa «Descargar HTML autónomo» en el comparador local. La copia incluye los datos y su procedencia, y permite consultar el corte sin conexión.

## Estado anterior a la reactivación

Base aprobada `v0.1.0`. Actualizado el 24 de noviembre de 2026. Las ramas de componentes se revisan por separado. Esta rama reúne los cambios para probarlos localmente.

| Tarea | Resultado y evidencia | Estado |
|---|---|---|
| A03 | Migración PostgreSQL, carga transaccional por corte y roles separados de ingesta y lectura. Pruebas de idempotencia, permisos y rechazo del corte sintético en la base aprobada | [PR 8](https://github.com/sebastianvegajg-art/chile-territorial/pull/8) |
| D01 | Prototipo responsive con selector de 16 regiones, estados de disponibilidad y tabla accesible. Validado a 360 y 1200 px | [PR 5](https://github.com/sebastianvegajg-art/chile-territorial/pull/5) |
| M01 | Crecimiento real y participación nominal mediante Decimal y linaje. Cinco pruebas | [PR 2](https://github.com/sebastianvegajg-art/chile-territorial/pull/2) |
| E01 | Verificador BDE con catálogo, cuatro series de referencia, originales y manifiesto SHA-256. Siete pruebas. Sin token configurado en este entorno | [PR 3](https://github.com/sebastianvegajg-art/chile-territorial/pull/3). Extracción autenticada pendiente |
| E02 | Preparación de la carga de PIB real y nominal, dimensiones regionales y contraste con el Excel | Pendiente de E01 autenticada y disponibilidad del Excel para su contraste |
| F01 | Tres billeteras y 12 filas de cobertura 2025–2028, con brechas y evidencia documental. Cuatro pruebas | [PR 7](https://github.com/sebastianvegajg-art/chile-territorial/pull/7) |
| B01 | Cinco rutas del contrato, CSV y corte. Demostración sintética y adaptador PostgreSQL de lectura | [PR 4](https://github.com/sebastianvegajg-art/chile-territorial/pull/4). Conexión PostgreSQL con rol lector verificada. Lectura de cifras oficiales pendiente de E02 |
| W01 | Comparador regional con React y datos sintéticos mediante API local | [PR 9](https://github.com/sebastianvegajg-art/chile-territorial/pull/9). Prueba integrada en Chromium |
| Q01 | Seis controles HTTP sobre cobertura, filtro, CSV, corte, faltantes y procedencia | [PR 6](https://github.com/sebastianvegajg-art/chile-territorial/pull/6). Contraste oficial pendiente de E02 |

## Decisiones y problemas

- La demostración se inicia con modo explícito y corte `prueba-local`. Los valores generados sirven para probar filtros, fórmulas y presentación. La base aprobada conserva separados sus cortes.
- Las pruebas de Docker agotaron temporalmente el almacenamiento. Se retiraron únicamente los contenedores y volúmenes descartables creados en esta fase.
- F01 documenta ejecución observada, proyectos, proyecciones y faltantes por separado. El piloto fiscal queda fuera de la ruta crítica para comparar el PIB regional.

## Ejecutar el comparador

Desde la raíz de esta rama, con Python 3 y Node instalados:

```sh
python -m venv .venv
.venv/bin/pip install -r apps/api/requirements.txt
npm --cache "${TMPDIR:-/tmp}/ct-npm" ci --prefix apps/web
CT_PYTHON=.venv/bin/python infra/demo-local.sh
```

Abre `http://127.0.0.1:5173`. Los dos procesos escuchan solo en la interfaz local. Detén ambos con Ctrl+C. El modo demostración no requiere Docker ni credenciales.

## Verificar la demostración

Con los procesos en ejecución, ejecuta `python -m unittest discover -s tests/auditoria -v` para la API. Para el flujo web instala Playwright en el entorno de pruebas y ejecuta `python tests/integration/comparador_browser.py` con Chromium de Playwright o define `CT_CHROMIUM` con la ruta a Chromium local. La prueba verifica selección, navegación, procedencia, CSV, aislamiento del modo oficial y vista de 360 px. La interfaz compara un año a la vez. La auditoría completa con cifras oficiales y accesibilidad asistida queda pendiente.
