#!/bin/bash
set -e

echo "Running Alembic migrations..."
alembic upgrade head || echo "Alembic migration skipped (no migrations yet)"

echo "Starting server..."
exec "$@"
