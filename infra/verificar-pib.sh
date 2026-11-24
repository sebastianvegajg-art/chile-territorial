#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
db=$root/infra/pib-db.sh
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT

PIB_DB_MODE=prueba "$db" iniciar
PIB_DB_MODE=prueba "$db" migrar
PIB_DB_MODE=prueba "$db" ejemplo
[[ $(PIB_DB_MODE=prueba "$db" ejemplo) == f ]]

PIB_DB_MODE=prueba "$db" consulta "
DO \$\$
BEGIN
    IF (SELECT count(*) FROM pib.api_territorio) <> 17 OR
       (SELECT count(*) FROM pib.api_observacion WHERE publicacion = 'prueba-local') <> 2 OR
       (SELECT valor FROM pib.api_observacion WHERE id = 'prueba-11-2024') IS DISTINCT FROM '0' OR
       NOT EXISTS (SELECT FROM pib.api_observacion
          WHERE id = 'prueba-11-2025' AND valor IS NULL AND clase = 'no_disponible') OR
       NOT EXISTS (SELECT FROM pib.api_procedencia WHERE observacion = 'prueba-11-2025') THEN
        RAISE EXCEPTION 'Falló la lectura del corte sintético o del catálogo territorial';
    END IF;
END
\$\$;
"

if PIB_DB_MODE=prueba "$db" consulta 'SELECT * FROM pib.configuracion' >"$scratch/salida" 2>&1 ||
   ! grep -q 'permission denied' "$scratch/salida"; then
  cat "$scratch/salida" >&2
  exit 1
fi

python3 - "$root/contracts/pib-prueba.json" "$scratch/lote-invalido.json" <<'PY'
import json
from pathlib import Path
import sys

base, invalid = map(Path, sys.argv[1:])
lot = json.loads(base.read_text())
cut_id = "prueba-integridad-rollback"
lot["publicacion"]["id"] = cut_id
for obs in lot["observaciones"]:
    obs["id"] = f"{cut_id}-{obs['anio']}"
    obs["publicacion"] = cut_id
lot["procedencias"] = []
invalid.write_text(json.dumps(lot))
PY

if PIB_DB_MODE=prueba "$db" cargar "$scratch/lote-invalido.json" >"$scratch/salida" 2>&1 ||
   ! grep -q 'Procedencia, estado o clase de evidencia incompatibles' "$scratch/salida"; then
  cat "$scratch/salida" >&2
  exit 1
fi

PIB_DB_MODE=prueba "$db" consulta "
DO \$\$
BEGIN
    IF EXISTS (SELECT FROM pib.api_publicacion WHERE id = 'prueba-integridad-rollback') THEN
        RAISE EXCEPTION 'La publicación inválida quedó disponible';
    END IF;
END
\$\$;
"

PIB_DB_MODE=aprobada "$db" iniciar
if PIB_DB_MODE=aprobada "$db" cargar "$root/contracts/pib-prueba.json" >"$scratch/salida" 2>&1 ||
   ! grep -q 'incompatible con el modo de la base' "$scratch/salida"; then
  cat "$scratch/salida" >&2
  exit 1
fi
printf '%s\n' 'Verificación de persistencia PIB completada.'
