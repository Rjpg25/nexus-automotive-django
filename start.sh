#!/usr/bin/env bash
set -euo pipefail
if [ -n "${RENDER:-}" ] && [ -z "${DATABASE_URL:-}" ]; then
  echo "Falta DATABASE_URL: Nexus necesita PostgreSQL para conservar sus registros." >&2
  exit 1
fi
python manage.py migrate --noinput
python manage.py preparar_nexus
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60 --access-logfile - --error-logfile -
