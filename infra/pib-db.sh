#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mode=${PIB_DB_MODE:-prueba}
case "$mode" in
  prueba) default_port=54327 ;;
  aprobada) default_port=54328 ;;
  *) printf '%s\n' 'PIB_DB_MODE debe ser prueba o aprobada.' >&2; exit 2 ;;
esac
export PIB_DB_PORT=${PIB_DB_PORT:-$default_port}
compose=(docker compose --project-directory "$root" -f "$root/infra/compose.pib.yml" -p "${PIB_DB_PROJECT_PREFIX:-ct-pib}-$mode")

psql_db() {
  "${compose[@]}" exec -T postgres psql -X --no-password --set=ON_ERROR_STOP=1 -U postgres -d chile_territorial "$@"
}

migrate() {
  {
    cat <<'SQL'
BEGIN;
SELECT pg_advisory_xact_lock(34581, 1);
CREATE SCHEMA IF NOT EXISTS ct_control;
REVOKE ALL ON SCHEMA ct_control FROM PUBLIC;
CREATE TABLE IF NOT EXISTS ct_control.migracion (id text PRIMARY KEY, aplicada_en timestamptz NOT NULL DEFAULT now());
SQL
    for migration in "$root"/db/migrations/[0-9]*.sql; do
      name=${migration##*/}
      [[ "$name" =~ ^[0-9]+_[a-z0-9_]+\.sql$ ]] || exit 2
      printf "SELECT NOT EXISTS (SELECT FROM ct_control.migracion WHERE id = '%s') AS aplicar\n" "$name"
      printf '\\gset\n\\if :aplicar\n'
      cat "$migration"
      printf "\nINSERT INTO ct_control.migracion (id) VALUES ('%s');\n" "$name"
      printf '\\endif\n'
    done
    cat <<'SQL'
INSERT INTO pib.configuracion (modo) VALUES (:'modo') ON CONFLICT DO NOTHING;
SELECT modo = :'modo' AS coincide FROM pib.configuracion
\gset
\if :coincide
COMMIT;
\else
DO $$ BEGIN RAISE EXCEPTION 'El modo solicitado no coincide con la base existente'; END $$;
\endif
SQL
  } | psql_db --set="modo=$mode"
}

load() {
  local input=$1 encoded
  encoded=$(python3 -c 'import base64, pathlib, sys; print(base64.b64encode(pathlib.Path(sys.argv[1]).read_bytes()).decode())' "$input")
  {
    printf '%s\n' 'SET ROLE ct_pib_ingest;'
    printf "SELECT pib.cargar_lote(convert_from(decode('%s', 'base64'), 'UTF8')::jsonb);\n" "$encoded"
  } | psql_db -qAt
}

case "${1:-}" in
  iniciar)
    "${compose[@]}" up -d --wait
    migrate
    ;;
  migrar)
    migrate
    ;;
  ejemplo)
    if [[ "$mode" != prueba ]]; then
      printf '%s\n' 'El ejemplo sintético solo se carga en la base de prueba.' >&2
      exit 2
    fi
    load "$root/contracts/pib-prueba.json"
    ;;
  cargar)
    if [[ $# -ne 2 || ! -f $2 ]]; then
      printf '%s\n' 'Indica la ruta a un lote ya validado con el contrato.' >&2
      exit 2
    fi
    load "$2"
    ;;
  consulta)
    shift
    if [[ $# -ne 1 ]]; then
      printf '%s\n' 'Indica una consulta SQL.' >&2
      exit 2
    fi
    psql_db -c 'SET ROLE ct_pib_reader' -c "$1"
    ;;
  detener) "${compose[@]}" stop ;;
  *)
    printf '%s\n' 'Uso: infra/pib-db.sh {iniciar|migrar|ejemplo|cargar LOTE|consulta SQL|detener}' >&2
    exit 2
    ;;
esac
