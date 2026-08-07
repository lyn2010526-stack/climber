#!/usr/bin/env bash
#
# start.sh - Production start script (Gunicorn + Uvicorn workers)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-4}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "Starting Climber Agent Engine..."
echo "Host: ${HOST}"
echo "Port: ${PORT}"
echo "Workers: ${WORKERS}"
echo ""

# Check if gunicorn is available
if command -v gunicorn &>/dev/null; then
    gunicorn app.main:app \
        --bind "${HOST}:${PORT}" \
        --workers "${WORKERS}" \
        --worker-class uvicorn.workers.UvicornWorker \
        --access-logfile - \
        --error-logfile - \
        --log-level "${LOG_LEVEL}" \
        --timeout 120 \
        --graceful-timeout 30
else
    echo "Gunicorn not found, using Uvicorn..."
    uvicorn app.main:app \
        --host "${HOST}" \
        --port "${PORT}" \
        --log-level "${LOG_LEVEL}" \
        --timeout-keep-alive 60
fi
