#!/bin/sh
# Production entrypoint: migrate DB, start ingestion worker, then serve API.
# Used on Railway (single service + volume) so API and worker share document storage.
set -e

echo "Running database migrations..."
alembic upgrade head

mkdir -p "${DOCUMENT_STORAGE_PATH:-/app/storage/documents}"
mkdir -p "${HF_HOME:-/app/storage/huggingface}"

echo "Starting ingestion worker..."
arq app.workers.ingestion_worker.WorkerSettings &
WORKER_PID=$!

cleanup() {
  echo "Shutting down worker (pid ${WORKER_PID})..."
  kill "$WORKER_PID" 2>/dev/null || true
  wait "$WORKER_PID" 2>/dev/null || true
}
trap cleanup INT TERM

echo "Starting API on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
