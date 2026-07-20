# Docker Build CI/CD Notes

## Issue: Docker Container Health Check Failures

### Problem
The Docker container fails health checks in CI/CD pipeline with error:
```
exiqus-github-analyzer-1 is unhealthy
```

### Root Cause
The application requires `GITHUB_TOKEN` and `ANTHROPIC_API_KEY` environment variables to start successfully. Without these, the Config class raises a ValueError during initialization, preventing the health endpoint from responding.

### Solution
1. Updated `docker-compose.yml` to pass environment variables:
   ```yaml
   environment:
     - GITHUB_TOKEN=${GITHUB_TOKEN}
     - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
   ```

2. Created `.env.docker` template file with required variables

3. Updated README with Docker deployment instructions

### CI/CD Requirements
For CI/CD pipelines, ensure:
1. Set `GITHUB_TOKEN` and `ANTHROPIC_API_KEY` as GitHub secrets
2. Pass secrets to Docker build/test steps:
   ```yaml
   env:
     GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
     ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
   ```

### Testing Docker Build
```bash
# Test locally
export GITHUB_TOKEN=your_token
export ANTHROPIC_API_KEY=your_key
docker-compose up --build
```

### Health Check Endpoint
The `/health` endpoint checks:
- Database connectivity
- Redis connectivity
- Returns 503 if any dependency fails