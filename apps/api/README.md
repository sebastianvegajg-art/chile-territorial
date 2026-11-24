# API de PIB

Desde la raíz, instala `python -m pip install -r apps/api/requirements.txt`.
Para la demostración sintética inicia `CT_MODO=demo python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`.

El modo ordinario consulta las vistas de lectura de PostgreSQL mediante `DATABASE_URL` y expone únicamente cortes aprobados. La demo es optativa, independiente de PostgreSQL y devuelve el corte `prueba-local` con datos artificiales. La documentación interactiva está en `/docs`. El contrato compartido está en `contracts/openapi.json`.
