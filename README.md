# docs-copilot

Point it at a documentation site or Git repository. It crawls, indexes, and answers questions with citations to the exact source passage, and it measures how good its answers are.

> Learning project, built in phases. See [`docs-copilot.md`](docs-copilot.md) for the full spec.

## Quickstart (Phase 0)

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker.

```bash
cp .env.example .env              # fill in API keys later
docker compose -f deploy/docker-compose.yml up -d   # postgres (pgvector) + redis
uv sync
uv run docs-copilot --help
uv run docs-copilot serve         # http://localhost:8000/healthz
```

## Development

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest                      # unit tests
uv run pytest -m integration       # needs the compose stack
uv run pytest tests/unit/test_health.py::test_healthz   # single test
```
