# docs-copilot — Phased Build Plan

## Progress

**Resume here:** finish Phase 0. Start Docker Desktop, verify `docker compose up`, then merge PR #1. After that, start Phase 1 on branch `phase-01-storage`.

| Phase | Name | Status | PR |
|-------|------|--------|----|
| 0 | Repo bootstrap | 🟡 PR open, CI green, compose check pending | [#1](https://github.com/amikumar91/docs-copilot/pull/1) |
| 1 | Storage & data model | ⬜ Not started | |
| 2 | Ingestion: Git → parser → chunker | ⬜ | |
| 3 | Embeddings & dense search | ⬜ | |
| 4 | Golden dataset v1 + retrieval metrics | ⬜ | |
| 5 | Hybrid retrieval + reranking | ⬜ | |
| 6 | Answer generation with citations | ⬜ | |
| 7 | Observability & cost | ⬜ | |
| 8 | Answer evaluation + judge calibration | ⬜ | |
| 9 | Web crawler + incremental sync | ⬜ | |
| 10 | Enrichment, query transforms, caching | ⬜ | |
| 11 | Ablation study + CI eval gate | ⬜ | |
| 12 | MCP server, security, UI | ⬜ | |
| 13 | Polish & deploy | ⬜ | |

Legend: ⬜ not started · 🔵 in progress · 🟡 PR open · ✅ merged. Update this table at the start and end of every phase.

## Context
This is a learning project. The goal is to build the spec'd RAG system **as a learning project**, committed phase by phase. Decisions made with the user:
- **Collaboration:** Claude scaffolds (project setup, config, wiring, fixtures, and failing tests that specify behaviour). **The user implements the core algorithms**, and Claude reviews and explains. Each phase lists a "You build" section.
- **Providers:** OpenAI `text-embedding-3-small` (1536-d) for embeddings. A local cross-encoder (`sentence-transformers`, e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2` or `BAAI/bge-reranker-base`) for reranking. Claude for generation (fast: `claude-haiku-5-5`, strong: `claude-sonnet-5-5`, judge: `claude-opus-5-5`).
- **First corpus:** the FastAPI docs (`github.com/fastapi/fastapi`, path `docs/en/docs/`).
- **Git:** `git init` locally, create a GitHub repo, and use **one branch + PR per phase** (`phase-NN-name`). Merge to `main` when the phase's "Done when" is met.

Every phase has the same shape: Claude writes the scaffolding and tests → the user implements the core → `ruff` + `pyright` + `pytest` pass → Claude reviews → commit, then PR, then merge. Write ADRs (spec §16) in the phase where the decision is made.

Environment notes: Windows 11. Requires Docker Desktop (Postgres+pgvector, Redis, Langfuse), `uv`, Python 3.12+, and the `gh` CLI. API keys go in `.env` (git-ignored).

---

## Phase 0 — Repo bootstrap
- **Claude:** `git init`, `.gitignore`, `uv init` with the `src/docs_copilot/` package layout (spec §13), `pyproject.toml` (ruff, pyright, pytest config), Pydantic v2 `settings.py`, `.env.example`, and `deploy/docker-compose.yml` (postgres+pgvector, redis). Also a FastAPI app with `/healthz` and `/readyz`, a Typer CLI entry point `docs-copilot`, a GitHub Actions CI job (lint, types, unit tests), and `gh repo create`.
- **You build:** nothing yet. Read through the layout and run the stack.
- **Done when:** `docker compose up` works, `uv run docs-copilot --help` runs, `/healthz` returns 200, and CI is green on GitHub.

## Phase 1 — Storage & data model
- **Claude:** SQLAlchemy 2 models for the spec §6 tables, an Alembic setup, and the initial migration (the `vector` extension, HNSW + GIN + unique indexes). Also a testcontainers Postgres fixture.
- **You build:** the repository functions (`create_collection`, `upsert_document`, `upsert_chunks`), all scoped by `collection_id`, plus a test proving there's no cross-collection leakage.
- **Learn:** pgvector, HNSW vs IVF, tsvector/GIN. ADR-1 (vector store).

## Phase 2 — Ingestion: Git fetcher → parser → chunker
- **Claude:** a `Fetcher` protocol, a Git fetcher (shallow clone, records SHA), a Markdown → normalized AST parser (`markdown-it-py`, which keeps heading anchors), a `Chunker` protocol, a `fixed` baseline chunker, golden chunker fixtures, and the CLI `add-collection` / `sync`.
- **You build:** the **`heading` chunker**: split on the heading hierarchy, store `heading_path`, never split code blocks or tables, target 300–800 tokens (tiktoken) with overlap, and link parent and child chunks.
- **Done when:** syncing FastAPI docs puts its chunks in Postgres and the golden chunker tests pass. ADR-3 is drafted.

## Phase 3 — Embeddings & dense search
- **Claude:** the provider interfaces `EmbeddingModel` / `Reranker` / `ChatModel` (`providers/`), an OpenAI embedding implementation, a per-model price table, record/replay fixtures for API calls, `POST /v1/search`, and the CLI `search`.
- **You build:** the embedding worker (batching, retry with backoff, idempotent on `(chunk_hash, embedding_model)`, refuses to mix models) and the pgvector cosine top-k query with metadata filters.
- **Done when:** searching a real FastAPI question returns relevant chunks.

## Phase 4 — Golden dataset v1 + retrieval metrics
- **Claude:** the `evals/` layout, the JSONL schema, a drafting script (Claude drafts Q/A from sampled sections), `evals/runner.py`, and YAML configs.
- **You build:** the **recall@k, MRR, and nDCG@k** functions, plus a **hand review of all 50 questions**. Hand-write the multi-hop and unanswerable questions (≥15% unanswerable).
- **Done when:** the baseline dense-only recall@5 is committed in `evals/results/`.

## Phase 5 — Hybrid retrieval + reranking
- **Claude:** the lexical retriever plumbing (Postgres FTS), the local cross-encoder `Reranker` implementation, and retriever-mode config flags.
- **You build:** the FTS ranking query, **Reciprocal Rank Fusion (k=60)** plus a weighted-fusion option, and the rerank stage (top 30 → top 5–8, can be switched off).
- **Done when:** eval results for dense vs BM25 vs hybrid vs hybrid+rerank are committed. ADR-2 and ADR-4 are written.

## Phase 6 — Answer generation with citations
- **Claude:** the Anthropic `ChatModel` (structured output via a tool schema, streaming), the system prompt, the `/v1/ask` response model (spec §7), SSE streaming, and the CLI `ask`.
- **You build:** the **context builder** (dedupe, merge adjacent chunks, parent expansion, token budget, a stable prefix → cache breakpoint → retrieved context) and the **citation verifier** (cited chunk was in the context, key-term overlap, sets `grounded` and `not_found`).
- **Done when:** `docs-copilot ask fastapi "How do I add CORS?"` returns a grounded answer with working anchor URLs, and an unanswerable question returns `not_found`. ADR-6 and ADR-7 are written.

## Phase 7 — Observability & cost
- **Claude:** OTel setup, Langfuse in compose, the Prometheus `/metrics` endpoint, and structured JSON logs with `trace_id`.
- **You build:** per-stage spans with `gen_ai.*` attributes, `cost_usd` per call from the price table, and `query_log` writes. Also `POST /v1/feedback`, attached to the trace.
- **Done when:** a full request trace with tokens and cost is visible in Langfuse.

## Phase 8 — Answer evaluation + judge calibration
- **Claude:** judge rubric prompts (`evals/judges/`) and the judge runner using the strong/judge tier.
- **You build:** faithfulness (claim decomposition), correctness (1–5 rubric), citation precision/recall, and refusal accuracy. Also **hand-label 50 answers** and compute Cohen's kappa against the judge.
- **Done when:** judge–human agreement is reported. ADR-9 is written.

## Phase 9 — Web crawler + incremental sync
- **Claude:** an HTTP fetcher skeleton, an HTML boilerplate stripper, a Postgres-backed job queue and worker, and the `ingestion_runs` bookkeeping. Add `/sync` and `/runs` endpoints.
- **You build:** the sitemap-first crawler with bounded-BFS fallback, robots.txt handling, and rate limiting. Also **SSRF protection** (block private IP ranges and metadata endpoints, enforce a domain allowlist and size/time limits). Then content-hash and git-diff incremental re-indexing, where only changed chunks are re-embedded and `index_version` is bumped.
- **Done when:** the incremental sync test passes, with only changed chunks embedded.

## Phase 10 — Enrichment, query transforms, caching
- **Claude:** config switches, a Redis client, and Batch API plumbing for enrichment.
- **You build:** contextual enrichment (an LLM mode plus a template-only mode, cached by chunk hash), the rewrite, multi-query, and HyDE query transforms, a semantic cache invalidated by `index_version`, and conversation mode with query condensation. Then **measure the prompt-cache savings**.
- ADR-8 is written.

## Phase 11 — Ablation study + CI eval gate
- **Claude:** an ablation grid runner, a results table generator, and a GitHub Actions eval gate (a ~30-question smoke subset, response caching, a spend cap, secrets).
- **You build:** the regression thresholds vs the `main` baseline, then run the full grid and write the "what mattered" conclusion.
- **Done when:** the PR gate blocks a deliberate regression.

## Phase 12 — MCP server, security, UI
- **Claude:** an MCP server (`search_docs`, `ask_docs`, `list_collections`, and a `docs://` resource) over Streamable HTTP and stdio, an API-key auth and rate-limit scaffold, and a minimal HTMX UI with streaming.
- **You build:** a prompt-injection eval set (poisoned docs) and the defenses for it. Also `SECURITY.md` (threat model).
- **Done when:** the MCP server works from Claude Code and MCP Inspector, and the injection set passes.

## Phase 13 — Polish & deploy
- Helm chart, README with measured quality, latency, and cost numbers plus the ablation table, any remaining ADRs, CONTRIBUTING, license, and a second public docs set. Optional: an Ollama offline profile.
- **Done when:** every item in the spec §18 checklist is satisfied.

---

## Verification (every phase)
- `uv run ruff check . && uv run pyright && uv run pytest` passes locally, and CI is green on the PR.
- The phase's "Done when" check is demonstrated live (CLI/HTTP call shown in the PR description).
- From Phase 4 on: re-run `docs-copilot eval run` and commit the results, so each phase's quality impact is measured.

## Immediate next step after approval
Execute **Phase 0** on branch `phase-00-bootstrap`.
