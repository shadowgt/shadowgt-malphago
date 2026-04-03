#!/bin/bash
set -e

echo "=== MalPhaGo API Starting ==="

# Wait for DB to be ready (beyond Docker healthcheck, extra safety)
echo "Waiting for database..."
for i in $(seq 1 30); do
    if python -c "
import asyncio, asyncpg, os
async def check():
    url = os.environ.get('DATABASE_URL', '')
    conn = await asyncpg.connect(url.replace('postgresql+asyncpg://', 'postgresql://'))
    await conn.close()
asyncio.run(check())
" 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    echo "  DB not ready yet... ($i/30)"
    sleep 2
done

# Run Alembic migrations if alembic directory exists
if [ -d "alembic" ]; then
    echo "Running Alembic migrations..."
    alembic upgrade head || echo "WARNING: Alembic migration failed, falling back to auto-create"
fi

echo "Starting server..."
exec "$@"
