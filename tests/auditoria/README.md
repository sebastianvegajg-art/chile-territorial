# Auditoría del MVP de PIB

Arranca la API local desde la raíz del repositorio con `CT_MODO=demo python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`. En otra terminal ejecuta:

```bash
python -m unittest discover -s tests/auditoria -v
```

Las pruebas usan la biblioteca estándar. Si el puerto difiere, configura `CT_AUDIT_API_URL` con la URL base local completa, por ejemplo `http://127.0.0.1:8020/api/v1`.

La comprobación cubre los 16 territorios regionales y Chile, el aislamiento del corte sintético, la paginación, la equivalencia del CSV con JSON, la procedencia y los estados de ausencia. También verifica errores de consulta y corte fijo en resultados vacíos.

El cierre de Q01 requiere una carga real repetible, contraste de una muestra con el Banco Central, inspección del linaje y comprobación del recorrido accesible en la web. Adjunta los identificadores y cortes de la muestra, comandos que reproduzcan los resultados, valores y unidades comparadas, y cualquier discrepancia observada. El contraste con Excel se ejecuta cuando esté disponible como fuente de referencia.
