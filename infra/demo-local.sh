#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:-demo}
case "$mode" in
  demo) label='Comparador de prueba' ;;
  oficial)
    : "${DATABASE_URL:?Configura DATABASE_URL para el lector PostgreSQL}"
    label='Comparador con datos oficiales'
    ;;
  *) printf '%s\n' 'Uso: infra/demo-local.sh [demo|oficial]' >&2; exit 2 ;;
esac
api_pid=
web_pid=
cleanup() {
  if [[ -n "$web_pid" ]]; then kill "$web_pid" 2>/dev/null || true; fi
  if [[ -n "$api_pid" ]]; then kill "$api_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
CT_MODO="$mode" "${CT_PYTHON:-python}" -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!
(
  cd apps/web
  exec node node_modules/vite/bin/vite.js --mode "$mode" --host 127.0.0.1 --port 5173 --strictPort
) &
web_pid=$!
printf '%s en http://127.0.0.1:5173\n' "$label"
set +e
wait -n "$api_pid" "$web_pid"
status=$?
exit "$status"
