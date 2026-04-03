#!/bin/bash
# ──────────────────────────────────────────────────────────
# MalPhaGo Oracle Cloud Deployment Script
# Target: Oracle Cloud Free Tier ARM (Ampere A1)
# Usage: ./deploy.sh [up|down|logs|restart|migrate|backup]
# ──────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check .env exists
if [ ! -f ../.env ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env and configure it."
    echo "  cp .env.example .env"
    exit 1
fi

# Load .env
set -a
source ../.env
set +a

case "${1:-up}" in
    up)
        echo "=== Starting MalPhaGo ==="
        docker compose up -d --build
        echo "=== Started! API at http://localhost:${API_PORT:-8000} ==="
        docker compose logs -f api
        ;;
    down)
        echo "=== Stopping MalPhaGo ==="
        docker compose down
        ;;
    restart)
        echo "=== Restarting API ==="
        docker compose restart api
        docker compose logs -f api
        ;;
    logs)
        docker compose logs -f "${2:-api}"
        ;;
    migrate)
        echo "=== Running Alembic Migration ==="
        docker compose exec api alembic upgrade head
        ;;
    backup)
        BACKUP_FILE="malphago_backup_$(date +%Y%m%d_%H%M%S).sql"
        echo "=== Backing up database to $BACKUP_FILE ==="
        docker compose exec db pg_dump -U "${POSTGRES_USER:-malphago}" "${POSTGRES_DB:-malphago}" > "$BACKUP_FILE"
        echo "=== Backup saved: $BACKUP_FILE ==="
        ;;
    status)
        docker compose ps
        echo ""
        echo "=== Health Check ==="
        curl -s http://localhost:${API_PORT:-8000}/health | python3 -m json.tool 2>/dev/null || echo "API not responding"
        ;;
    *)
        echo "Usage: $0 [up|down|restart|logs|migrate|backup|status]"
        exit 1
        ;;
esac
