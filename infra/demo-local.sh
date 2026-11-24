#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
api_pid=
web_pid=
cleanup() {
  if [[ -n "$web_pid" ]]; then kill "$web_pid" 2>/dev/null || true; fi
  if [[ -n "$api_pid" ]]; then kill "$api_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
CT_MODO=demo "${CT_PYTHON:-python}" -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!
(
  cd apps/web
  exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
) &
web_pid=$!
printf '%s\n' 'Comparador de prueba en http://127.0.0.1:5173'
set +e
wait -n "$api_pid" "$web_pid"
status=$?
exit "$status"
