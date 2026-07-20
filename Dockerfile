# Multi-stage production Docker build for GitHub Analyzer
# Stage 1: Build environment with development dependencies
FROM python:3.12-slim AS builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Create application directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --only=main --no-root --no-ansi \
    && rm -rf $POETRY_CACHE_DIR

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Install the application into the virtual environment
RUN poetry install --only=main --no-ansi

# Stage 2: Production runtime environment
FROM python:3.12-slim AS production

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directory and set ownership
WORKDIR /app
RUN chown -R appuser:appuser /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --from=builder /app/src ./src
COPY --from=builder /app/README.md ./

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/uploads /home/appuser/.exiqus/costs \
    && chown -R appuser:appuser /app /home/appuser

# Switch to non-root user
USER appuser

# Health check
# Note: Health check will fail if GITHUB_TOKEN and ANTHROPIC_API_KEY are not set
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health', timeout=5)" || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "src.github_analyzer.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]