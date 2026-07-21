# Contributing to Exiqus

Thanks for your interest in contributing! Exiqus is an evidence-based
GitHub repository analyzer, released under the
[AGPL-3.0 license](LICENSE).

By contributing, you agree that your contributions will be licensed
under the same AGPL-3.0 license that covers the project.

## Development Setup

### Backend (Python 3.10+, Poetry, Docker)

```bash
poetry install --with dev
poetry run pytest tests/          # run the test suite
```

The test suite runs against a real PostgreSQL spun up automatically via
testcontainers. The only requirement is a running Docker daemon. Set
`TEST_DATABASE_URL` to reuse an existing PostgreSQL instead (CI does
this with a service container).

### Frontend (Node 20+, npm)

```bash
cd frontend
npm install
npm run dev                       # local dev server
```

### Local stack (optional)

```bash
cp docker-compose.env.example .env   # fill in values
docker compose up
```

## Quality Gates

All of these must pass before a PR can be merged.

**Backend** (run in order, stop on any failure):

```bash
poetry run pytest tests/
poetry run ruff check src/ tests/ scripts/
poetry run ruff format src/ tests/ scripts/
poetry run mypy src/
```

**Frontend**:

```bash
npm run check-all    # typecheck → biome (lint + format)
npm run build
```

Conventions:

- Ruff handles formatting (88-char lines, double quotes) and linting,
  including import order and security rules - one tool, one config
- Type hints on every function (mypy strict)

## The Evidence-Based Philosophy (important!)

Exiqus deliberately contains **no numerical scores, ratings, or
hire/pass verdicts** anywhere. Reports present factual, observable
evidence patterns with confidence *explanations* in prose.

PRs that add scores, percentages, star ratings, verdict badges, or
behavioral inferences from commit patterns will not be accepted. When
in doubt: observations, not assessments; evidence, not judgment.

## Pull Request Process

1. Fork the repo and create a feature branch from `main`.
2. Make your change, including tests that cover the new behavior.
3. Ensure all quality gates above pass.
4. Open a PR with a clear description of the problem and solution.
5. A maintainer will review it. Expect honest, constructive feedback.

## Reporting Bugs & Requesting Features

Use the issue templates. For security vulnerabilities, **do not open a
public issue**. See [SECURITY.md](SECURITY.md).

## Code of Conduct

This project follows the
[Contributor Covenant](CODE_OF_CONDUCT.md). Be kind.
