# Avance de la primera fase

Base aprobada `v0.1.0`. Actualizado el 24 de noviembre de 2026. Las ramas de componentes se revisan por separado. Esta rama reúne los cambios para probarlos localmente.

| Tarea | Resultado y evidencia | Estado |
|---|---|---|
| A03 | Migración PostgreSQL, carga transaccional por corte y roles separados de ingesta y lectura. Pruebas de idempotencia, permisos y rechazo del corte sintético en la base aprobada | Implementada localmente |
| D01 | Prototipo responsive con selector de 16 regiones, estados de disponibilidad y tabla accesible. Validado a 360 y 1200 px | [PR 5](https://github.com/sebastianvegajg-art/chile-territorial/pull/5) |
| M01 | Crecimiento real y participación nominal mediante Decimal y linaje. Cinco pruebas | [PR 2](https://github.com/sebastianvegajg-art/chile-territorial/pull/2) |
| E01 | Verificador BDE con catálogo, cuatro series de referencia, originales y manifiesto SHA-256. Siete pruebas. Sin token configurado en este entorno | [PR 3](https://github.com/sebastianvegajg-art/chile-territorial/pull/3). Extracción autenticada pendiente |
| E02 | Preparación de la carga de PIB real y nominal, dimensiones regionales y contraste con el Excel | Pendiente de E01 autenticada y disponibilidad del Excel para su contraste |
| F01 | Tres billeteras y 12 filas de cobertura 2025–2028, con brechas y evidencia documental. Cuatro pruebas | [PR 7](https://github.com/sebastianvegajg-art/chile-territorial/pull/7) |
| B01 | Cinco rutas del contrato, CSV y corte. Demostración sintética y adaptador PostgreSQL de lectura | [PR 4](https://github.com/sebastianvegajg-art/chile-territorial/pull/4). Lectura con cifras oficiales pendiente de E02 |
| W01 | Comparador regional con React y datos sintéticos mediante API local | Validación integrada en esta rama |
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
npm ci --prefix apps/web
CT_PYTHON=.venv/bin/python infra/demo-local.sh
```

Abre `http://127.0.0.1:5173`. Los dos procesos escuchan solo en la interfaz local. Detén ambos con Ctrl+C. El modo demostración no requiere Docker ni credenciales.
