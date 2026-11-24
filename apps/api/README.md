# API de PIB

Desde la raíz, instala `python -m pip install -r apps/api/requirements.txt`.
Para la demostración sintética inicia `CT_MODO=demo python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`.

PostgreSQL sigue siendo el almacén principal versionado de la API: cuando `DATABASE_URL` está configurado (y `CT_MODO` no es `demo`), el servicio consulta las vistas de lectura de PostgreSQL y expone únicamente cortes aprobados. La demo (`CT_MODO=demo`) es optativa, independiente de PostgreSQL y devuelve el corte `prueba-local` con datos artificiales. La documentación interactiva está en `/docs`. El contrato compartido está en `contracts/openapi.json`.

## Lectura local de un corte oficial sin Docker (`CT_LOTE_OFICIAL`)

En entornos Windows o Linux sin Docker ni PostgreSQL, la API puede servir de solo lectura un lote oficial aprobado desde un archivo JSON explícito mediante `CT_LOTE_OFICIAL` (siempre que `CT_MODO` no sea `demo` y `DATABASE_URL` no esté configurado).

Al iniciar, la API valida estrictamente el archivo contra `contracts/pib-datos.schema.json` y verifica las reglas de publicación oficial: exige `publicacion.estado == "aprobada"`, integridad de procedencias y cobertura, y rechaza cualquier observación con `clase` igual a `"prueba"` o `"estimacion"`, o con `estado == "error"`. Si el archivo incumple alguna regla, el arranque falla con un error explícito.

En PowerShell (Windows):

```powershell
$env:CT_LOTE_OFICIAL = "data/published/pib-bde-publico.json"
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

En sh/bash (Linux/macOS):

```sh
CT_LOTE_OFICIAL=data/published/pib-bde-publico.json \
  python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Prioridad de configuración:
1. `CT_MODO=demo` (o `crear_app(demo_activa=True)`): modo demo sintético (`prueba-local`).
2. `crear_app(lote_oficial=ruta)`: lectura de solo lectura desde el archivo JSON indicado.
3. `DATABASE_URL`: lectura desde PostgreSQL (almacén principal versionado; prevalece sobre `CT_LOTE_OFICIAL` para mantener compatibilidad con las pruebas de conformidad contra PostgreSQL).
4. `CT_LOTE_OFICIAL` (sin `DATABASE_URL` ni `CT_MODO=demo`): lectura de solo lectura desde el lote oficial local.

## Carga de un corte oficial en PostgreSQL

Inicializa PostgreSQL en modo `aprobada` con la [infraestructura local](../../infra/README.md). Desde la raíz, configura `DATABASE_URL` con una cuenta que pueda asumir `ct_pib_ingest` y ejecuta:

```sh
python -m apps.api.cargar_publicacion lote.json \
  --artefacto id-real=original-real.html \
  --artefacto id-nominal=original-nominal.html
```

Usa los identificadores que aparecen en `artefactos` en el lote. El comando verifica el contrato y las huellas SHA-256 de los originales antes de invocar la carga transaccional. La opción `--validar` ejecuta estas comprobaciones sin conectarse a PostgreSQL. El mismo identificador y contenido se puede cargar nuevamente de forma idempotente. Para iniciar FastAPI utiliza una conexión distinta con permisos de lectura.

Para verificar el corte cargado en PostgreSQL contra todos los valores, las exportaciones y las procedencias, configura `DATABASE_URL` con la conexión de lectura y ejecuta `CT_LOTE_OFICIAL=lote.json python -m unittest apps.api.test_publicacion_postgres`. Las pruebas HTTP requieren `httpx`.
