# Multi-Agent RAG Platform — Codebase Context

> Primary source of truth for all workflows. Updated by `/sync-context`.
>
> Last updated: 2026-03-16
> Template synced: 2026-03-16

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Framework | FastAPI 0.115+ |
| LLM Orchestration | LangGraph 0.2+ |
| LLM Gateway | OpenRouter (200+ models via single API) |
| Vector DB | PostgreSQL 16 + pgvector |
| Knowledge Graph | Neo4j 5.x Community |
| Cache | Redis 7 (semantic cache + session store) |
| Embeddings | OpenRouter (`openai/text-embedding-3-small`, 1536-dim) |
| Evaluation | Ragas + custom metrics |
| Testing | pytest + httpx + pytest-asyncio |
| Validation | Pydantic v2 |
| Containerization | Docker + Docker Compose |
| Hosting | Docker on Hetzner VPS (Traefik reverse proxy) |
| Package Manager | uv / pip |
| Build Tool | N/A (Python — no build step) |

## Project Structure

```
multi-agent-rag-platform/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── ingestion/          # pipeline.py, chunker.py, embedder.py, extractors/
│   ├── retrieval/          # engine.py, vector_search.py, graph_search.py, reranker.py
│   ├── llm/                # router.py, openrouter.py, streaming.py, cost_tracker.py
│   ├── agents/             # executor.py, registry.py, tools/
│   ├── guardrails/         # pipeline.py, injection.py, pii.py, content_safety.py, hallucination.py
│   ├── memory/             # manager.py, short_term.py, long_term.py, entity.py
│   ├── cache/              # semantic.py
│   ├── evaluation/         # harness.py, relevance.py, faithfulness.py, correctness.py
│   ├── prompts/            # registry.py, templates/
│   ├── mcp/                # server.py
│   ├── api/                # chat.py, documents.py, conversations.py, graph.py, prompts.py, metrics.py, health.py
│   │   └── middleware/     # auth.py, rate_limit.py, errors.py
│   ├── db/                 # postgres.py, neo4j.py, redis.py, migrations/alembic/
│   └── lib/                # logger.py, utils.py
├── tests/                  # unit/, integration/, fixtures/llm/openrouter_responses/
├── docker-compose.yml
├── Dockerfile
├── docker-compose.prod.yml
├── pyproject.toml
├── alembic.ini
└── .env.example
```

## Key Modules

| Module | Purpose | Key Files |
|--------|---------|-----------|
| Ingestion | Document upload → chunk → embed → store | `src/ingestion/pipeline.py` |
| Retrieval | Hybrid search: vector + keyword + graph | `src/retrieval/engine.py` |
| LLM | Multi-model routing via OpenRouter | `src/llm/router.py`, `src/llm/openrouter.py` |
| Agents | LangGraph executor with tool calling | `src/agents/executor.py` |
| Guardrails | Input/output safety (injection, PII, hallucination) | `src/guardrails/pipeline.py` |
| Memory | Conversation memory (short/long/entity) | `src/memory/manager.py` |
| Cache | Semantic similarity cache for LLM responses | `src/cache/semantic.py` |
| Evaluation | RAG quality scoring (relevance, faithfulness) | `src/evaluation/harness.py` |
| Prompts | Versioned prompt template registry | `src/prompts/registry.py` |
| MCP | MCP server for external AI agent tooling | `src/mcp/server.py` |
| API | FastAPI route handlers + middleware | `src/api/` |
| DB | Database clients (PG, Neo4j, Redis) | `src/db/` |

## Database Schema

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| documents | Ingested document records | id (UUID), title, source, content_hash (dedup), status |
| chunks | Document chunks with vector embeddings | id, document_id (FK), content, embedding (vector 1536), token_count |
| conversations | Chat session tracking | id, user_id, total_tokens, total_cost_usd |
| messages | Individual messages with LLM metadata | id, conversation_id (FK), role, model_used, cost_usd, tool_calls |
| prompts | Versioned Jinja2 prompt templates | id, name (unique), version, template, model_hint |
| evaluations | RAG quality scores per response | id, message_id (FK), metric, score (0-1) |
| semantic_cache | Cached query→response pairs | id, query_embedding (vector), response, expires_at |
| Neo4j: Entity | Knowledge graph nodes | id, name, type, source_document_id |
| Neo4j: RELATED_TO | Entity relationship edges | relationship, confidence, source_chunk_id |

## External Integrations

| Service | Purpose | Auth Method |
|---------|---------|------------|
| OpenRouter | LLM completions + embeddings (200+ models) | API key (`OPENROUTER_API_KEY`) |
| Neo4j | Knowledge graph storage | Username/password (`NEO4J_USER`, `NEO4J_PASSWORD`) |
| BetterStack | Uptime monitoring | External polling of `/api/health` |

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `OPENROUTER_API_KEY` | LLM gateway authentication | OpenRouter dashboard |
| `DATABASE_URL` | PostgreSQL + pgvector connection | Docker Compose / Hetzner |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j connection | Docker Compose |
| `REDIS_URL` | Redis cache + session connection | Docker Compose |
| `API_KEYS` | API key(s) for auth middleware | Manual config |
| `DAILY_COST_LIMIT_USD` | Per-day LLM spend cap | Manual config |
| `TEST_DATABASE_URL` | PostgreSQL connection for pytest test runs | `.env` (same as `DATABASE_URL` locally) |
| `TEST_REDIS_URL` | Redis connection for pytest integration tests | `.env` (same as `REDIS_URL` locally) |
| `MOCK_LLM` | Use fixture responses instead of live APIs | Test env |
| `DEMO_MODE` | Enable public demo security protections | Manual config |

## Commands

> **IMPORTANT:** Before running any command, check if the venv is activated (prompt shows `(venv)`).
> If not, activate it first: `.\venv\Scripts\activate` (PowerShell/Windows).

| Action | Command |
|--------|---------|
| Dev server | `uvicorn src.main:app --reload` |
| Run tests | `python -m pytest` |
| Run unit tests | `python -m pytest tests/unit/` |
| Run integration tests | `python -m pytest -m integration` |
| Lint/check | `ruff check .` |
| Format | `ruff format .` |
| Type check | `mypy src/` |
| Migrate DB | `alembic upgrade head` |
| New migration | `alembic revision --autogenerate -m "description"` |
| Docker dev | `docker compose up -d` |

## Key Patterns & Conventions

> Detailed naming and import conventions are in `CODING_STANDARDS_DOMAIN.md`.

- All LLM calls go through `src/llm/openrouter.py` — never call providers directly
- Config via `src/config.py` Pydantic Settings — never read env vars directly
- Dependency hierarchy: see `CODING_STANDARDS_DOMAIN.md` → Architecture Rules

## Shared Foundation (MUST READ before any implementation)

> These files define the project's shared patterns, configuration, and utilities.
> The AI MUST read these **in full** before writing ANY new code. Never recreate what exists here.
> Populated by `/bootstrap` (from PRD). Updated by `/sync-context`.

| Category | File(s) | What it establishes |
|----------|---------|-------------------|
| Config | `src/config.py` | Pydantic Settings model, all env vars, defaults |
| DB clients | `src/db/postgres.py` | Async SQLAlchemy engine, session factory, pgvector init |
| DB clients | `src/db/neo4j.py` | Neo4j driver, constraint creation, graceful degradation |
| DB clients | `src/db/redis.py` | Async Redis client (cached), health check, graceful degradation |
| DB models | `src/db/models.py` | SQLAlchemy ORM models (7 tables), DeclarativeBase for migrations |
| DB migrations | `src/db/migrations/` | Alembic async config, initial schema (all 7 PRD tables + pgvector) |
| Logging | `src/lib/logger.py` | structlog configuration, JSON output, request correlation |
| Utilities | `src/lib/utils.py` | Content hashing, common helpers |
| Error handling | `src/api/middleware/errors.py` | Centralized error types, consistent error format |
| Auth | `src/api/middleware/auth.py` | API key validation, user ID extraction |
| OpenRouter | `src/llm/openrouter.py` | Single client for all LLM + embedding calls |

## Deep References

> For detailed implementation patterns, read the source directly — don't embed here.

| Topic | Where to look |
|-------|--------------|
| Ingestion pipeline | `src/ingestion/` |
| Retrieval (hybrid search) | `src/retrieval/` |
| LLM routing + streaming | `src/llm/` |
| Agent tools + executor | `src/agents/` |
| Guardrail pipeline | `src/guardrails/` |
| Conversation memory | `src/memory/` |
| Semantic caching | `src/cache/` |
| RAG evaluation | `src/evaluation/` |
| Prompt management | `src/prompts/` |
| MCP server | `src/mcp/` |
| API routes | `src/api/` |
| Database migrations | `src/db/migrations/alembic/` |
| Test patterns | `tests/` |
| LLM response fixtures | `tests/fixtures/llm/openrouter_responses/` |
