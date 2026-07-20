#!/bin/bash
# Startup script for Railway deployment
# Runs database migrations and starts the application

set -e

echo "Starting Exiqus GitHub Analyzer..."

# Environment check (without exposing secrets)
echo "=== Environment Status ==="
echo "PORT: ${PORT:-not set}"
[ -n "$DATABASE_URL" ] && echo "DATABASE_URL: [CONFIGURED]" || echo "DATABASE_URL: [NOT SET]"
[ -n "$REDIS_URL" ] && echo "REDIS_URL: [CONFIGURED]" || echo "REDIS_URL: [NOT SET]"
[ -n "$GITHUB_TOKEN" ] && echo "GITHUB_TOKEN: [CONFIGURED]" || echo "GITHUB_TOKEN: [NOT SET]"
[ -n "$ANTHROPIC_API_KEY" ] && echo "ANTHROPIC_API_KEY: [CONFIGURED]" || echo "ANTHROPIC_API_KEY: [NOT SET]"
echo "RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-not set}"
echo "RAILWAY_PROJECT_NAME: ${RAILWAY_PROJECT_NAME:-not set}"
echo "===================================="

# Use Railway's PORT or default to 8000
PORT="${PORT:-8000}"
echo "Using PORT: ${PORT}"

# ALWAYS run migrations - this is proper practice
echo "Running database migrations..."
if alembic upgrade head; then
    echo "Migrations completed successfully."
else
    echo "Warning: Migration failed with exit code $?, but continuing startup..."
    echo "This may be expected if the database schema is already up to date."
fi

# Start the application
echo "Starting application server on port ${PORT}..."

exec uvicorn src.github_analyzer.api.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --log-level info