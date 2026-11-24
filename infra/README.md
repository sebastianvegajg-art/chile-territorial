# PostgreSQL local · MVP de PIB

Requiere Docker Compose v2 y Python 3. Los dos modos usan proyectos, volúmenes y puertos separados. Solo escuchan en la interfaz local.

```sh
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
infra/pib-db.sh iniciar
infra/pib-db.sh ejemplo
infra/pib-db.sh ejemplo
infra/pib-db.sh consulta 'SELECT codigo, nombre FROM pib.api_territorio ORDER BY codigo'
infra/pib-db.sh consulta 'SELECT * FROM pib.api_observacion ORDER BY anio'
```

La primera carga devuelve `t`. La segunda devuelve `f` si el contenido coincide. Guarda el valor de entorno fuera de Git para reutilizar el mismo volumen. Docker solo aplica la contraseña de inicialización en un volumen nuevo. `infra/pib-db.sh detener` conserva los datos. El modo `prueba` usa el puerto 54327. El modo `aprobada` se selecciona con `PIB_DB_MODE=aprobada` y usa 54328. Puedes cambiar el puerto con `PIB_DB_PORT` o aislar volúmenes de otras pruebas con `PIB_DB_PROJECT_PREFIX`.

## Lectura y carga

- Base local `chile_territorial`, esquema `pib`. Las vistas `api_territorio`, `api_publicacion`, `api_observacion` y `api_procedencia` tienen nombres y campos del OpenAPI. La cobertura, cambios e insumos son JSONB, y el valor decimal se expone como texto. La consulta de observaciones empieza en 2013. El año auxiliar de 2012 conserva su procedencia. El catálogo base incluye 16 regiones y Chile. Sus vigencias desconocidas quedan vacías hasta verificar una fuente territorial versionada.
- Configura `DATABASE_URL` fuera de Git con un login que pertenezca a `ct_pib_reader` y use ese rol. Para probar con el login administrativo local, activa explícitamente `ct_pib_reader` en la sesión con `SET ROLE ct_pib_reader`. El rol tiene acceso de lectura a las cuatro vistas. Reserva el login administrativo para migraciones y gestión local.
- Da acceso de carga mediante `ct_pib_ingest`. Valida primero el [contrato](../contracts/README.md) y ejecuta `infra/pib-db.sh cargar RUTA_AL_LOTE` con el modo adecuado, o llama `pib.cargar_lote(jsonb)` como ese rol. La carga es atómica. El identificador de publicación y la huella permiten repetir el mismo lote e impiden reemplazar su contenido. El modo de la base queda fijo durante la inicialización.
- Las migraciones bajo `db/migrations/` se aplican por nombre y se registran de forma transaccional. Agrega una migración nueva para evolucionar el esquema. Usa `infra/pib-db.sh migrar` para aplicar cambios con la base en ejecución.

## Verificación local

Con `POSTGRES_PASSWORD` configurada, ejecuta `infra/verificar-pib.sh`. Arranca ambos modos, ejecuta las migraciones dos veces, prueba la carga repetida, comprueba permisos del lector y verifica que un error de procedencia revierta todo el corte. La comprobación del modo aprobado intenta cargar el ejemplo sintético y confirma su rechazo.
