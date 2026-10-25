# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

This is a learning project, built in phases from the spec `docs-copilot.md` (the source of truth for scope, architecture, data model, API, and evals). **The phase plan and progress tracker are in `docs/PLAN.md`. Read its "Progress" section first to see where to resume, and update it whenever a phase starts or finishes.** Each phase gets one branch, `phase-NN-name`, and one PR merged to `main`. Claude writes the scaffolding and the failing tests that specify behaviour. **The user implements the core algorithms**, so don't write those unless asked. Review and explain instead.

## Commands

```bash
uv sync                                           # install (set UV_LINK_MODE=copy on this machine)
docker compose -f deploy/docker-compose.yml up -d # postgres (pgvector) + redis
uv run docs-copilot serve                         # API on :8000 (/healthz, /readyz)
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest                                     # all tests; CI runs -m "not integration and not live"
uv run pytest tests/unit/test_health.py::test_healthz
```

Pytest markers: `integration` needs the compose stack, and `live` calls real model APIs (costs money). Settings come from env vars prefixed with `DOCS_COPILOT_`, except `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY`, which use their standard names (see `src/docs_copilot/settings.py`). The CLI lives at `src/docs_copilot/cli.py` (Typer), not at the top-level `cli/` directory the spec shows.

## What is being built

`docs-copilot` is a RAG service. It ingests a documentation site, a Git repo of Markdown/MDX/RST, or PDFs into isolated **collections**. It answers questions with inline citations to the exact source URL and section anchor, and it says "not found" when retrieval doesn't support an answer. A published evaluation harness and ablation study back up its quality claims.

## Planned stack and tooling (spec §12, §17)

- Providers: Voyage AI `voyage-3.5-lite` (1024-d) for embeddings (replaces the spec's OpenAI choice; see `docs/PLAN.md`), a local cross-encoder (sentence-transformers) for reranking, and Claude for generation (`claude-haiku-5-5` fast, `claude-sonnet-5-5` strong, `claude-opus-5-5` judge). The first corpus is the FastAPI docs.
- Python 3.12+, `uv`, Pydantic v2, FastAPI + SSE, Postgres + pgvector + Postgres FTS, Redis, SQLAlchemy + Alembic, OpenTelemetry → Langfuse, Prometheus/Grafana.
- Lint: `ruff`. Types: mypy or pyright. Tests: pytest. Integration tests use testcontainers Postgres.
- Local stack: `docker compose up` (from `deploy/docker-compose.yml`) runs the api, worker, postgres, redis, and langfuse. The `local` profile adds Ollama. Model calls go to hosted APIs using keys from `.env` (template in `.env.example`).
- Planned CLI:
  ```
  docs-copilot add-collection --name fastapi --git https://github.com/... --path docs/
  docs-copilot sync fastapi
  docs-copilot ask fastapi "How do I add CORS?"
  docs-copilot eval run --dataset evals/fastapi.jsonl --config configs/hybrid_rerank.yaml
  ```

## Architecture (spec §5, §13)

Two pipelines share one Postgres store. Code lives under `src/docs_copilot/`.

**Ingestion** (`ingest/`): Fetcher (git diff against the last indexed SHA; sitemap crawl first, then bounded BFS with ETag/Last-Modified; PDF) → Parser that normalizes everything to a Markdown AST (removes boilerplate, keeps heading anchors) → pluggable Chunker (`fixed` / `recursive` / `heading` (default) / `semantic`) → Contextual enrichment (a 1–2 sentence prefix, cached by chunk hash, template-only mode available, provider batch API for bulk runs) → Embedding worker.

**Query** (`retrieve/`, `generate/`): Query transform (rewrite / multi-query / HyDE) → Hybrid retrieve (pgvector HNSW cosine + FTS, fused with RRF k=60) → Reranker (top 30 → 5–8) → Context builder (dedupe, merge adjacent chunks, optional parent expansion, token budget) → Generator (Claude, structured answer + citations JSON, streaming) → Citation verifier (sets `grounded`) → API. A Redis semantic cache sits in front of this pipeline.

**Providers** (`providers/`): the interfaces are `ChatModel`, `EmbeddingModel`, and `Reranker`. Defaults are Anthropic/Bedrock for generation and hosted APIs for embeddings and reranking. Ollama and a local cross-encoder are optional. A per-model price table lets every call record `cost_usd`.

**Interfaces**: HTTP `/v1/*` (spec §7), the CLI, a minimal UI, and an MCP server (`mcp/`) with the tools `search_docs`, `ask_docs`, `list_collections` and the resource `docs://{collection}/{document_id}`.

## Invariants to preserve

- **Tenant isolation:** filter every query by `collection_id` at the SQL level. Tests must prove that no data leaks across collections.
- **Never mix embedding models in one index.** Store the model name and dimension. Embedding is idempotent on `(chunk_hash, embedding_model)`. Chunks are unique on `(collection_id, chunk_hash)`.
- **Incremental re-indexing** re-embeds only changed content. A re-index bumps `index_version` and invalidates that collection's semantic cache.
- **Chunker rules:** never split code blocks or tables. Store the heading path as metadata. Keep parent-child chunk links.
- **Prompt caching layout:** put the stable system prompt and instructions first, add a cache breakpoint, then the retrieved context.
- **Retrieved/crawled content is untrusted:** delimit it and treat it as data, not instructions (an injection eval set exists for this). The crawler enforces a domain allowlist, SSRF protection (blocks private IPs and metadata endpoints), size limits, and timeouts.
- `/v1/ask` responses follow the schema in spec §7: `answer`, `citations[]`, `grounded`, `not_found`, `usage`, `trace_id`.
- Use one typed settings object (`settings.py`). Never log provider keys.
- Every component that the ablation varies (chunker, enrichment, retriever mode, reranker, query transform, model tier) must be switchable through config.

## Testing and evaluation

- Use record/replay fixtures for LLM calls so tests are deterministic and free. Put live contract tests behind a flag.
- Evals live in `evals/` (datasets in versioned `*.jsonl`, ablation YAML configs, judge rubrics, `runner.py`, `results/`).
- The CI gate runs a ~30-question smoke subset on PRs that touch retrieval, prompt, or chunking code. It fails if recall@5 or faithfulness regresses past a threshold vs `main`.
- Record design decisions as ADRs in `docs/adr/` (the planned list is in spec §16).
