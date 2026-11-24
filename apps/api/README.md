# API de PIB

Desde la raíz, instala `python -m pip install -r apps/api/requirements.txt`.
Para la demostración sintética inicia `CT_MODO=demo python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`.

El modo ordinario consulta las vistas de lectura de PostgreSQL mediante `DATABASE_URL` y expone únicamente cortes aprobados. La demo es optativa, independiente de PostgreSQL y devuelve el corte `prueba-local` con datos artificiales. La documentación interactiva está en `/docs`. El contrato compartido está en `contracts/openapi.json`.

## Carga de un corte oficial

Inicializa PostgreSQL en modo `aprobada` con la [infraestructura local](../../infra/README.md). Desde la raíz, configura `DATABASE_URL` con una cuenta que pueda asumir `ct_pib_ingest` y ejecuta:

```sh
python -m apps.api.cargar_publicacion lote.json \
  --artefacto id-real=original-real.html \
  --artefacto id-nominal=original-nominal.html
```

Usa los identificadores que aparecen en `artefactos` en el lote. El comando verifica el contrato y las huellas SHA-256 de los originales antes de invocar la carga transaccional. La opción `--validar` ejecuta estas comprobaciones sin conectarse a PostgreSQL. El mismo identificador y contenido se puede cargar nuevamente de forma idempotente. Para iniciar FastAPI utiliza una conexión distinta con permisos de lectura.

Para verificar el corte cargado contra todos los valores, las exportaciones y las procedencias, configura `DATABASE_URL` con la conexión de lectura y ejecuta `CT_LOTE_OFICIAL=lote.json python -m unittest apps.api.test_publicacion_postgres`. Las pruebas HTTP requieren `httpx`.
