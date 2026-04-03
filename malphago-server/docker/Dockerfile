# ──────────────────────────────────────────────────────────
# MalPhaGo API — Production Dockerfile
# Target: Oracle Cloud Free Tier ARM (Ampere A1)
# ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

WORKDIR /app

# System deps (Playwright Chromium needs these on ARM)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Python deps (install first for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium (works on both amd64 and arm64)
RUN playwright install chromium

# Copy application
COPY . .

# Entrypoint: runs Alembic migrations then starts server
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Non-root user for security
RUN groupadd -r malphago && useradd -r -g malphago malphago \
    && chown -R malphago:malphago /app
USER malphago

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
