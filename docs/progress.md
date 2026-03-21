# Multi-Agent RAG Platform — Progress Tracker

> Auto-generated from PRD by `/bootstrap`. Items are picked top-to-bottom by `/implement-next`.

---

## Phase 0: Project Foundation

### Dev Environment Setup
- [x] [SETUP] Git branching strategy (completed during bootstrap Step 2b)
  - `main` = production deployments only, `dev` = active development
- [x] [SETUP] Local service infrastructure (PRD Section 3, 11)
  - PostgreSQL 16 + pgvector via Docker Compose (port 5433, pgvector 0.8.2)
  - Neo4j 5.x Community via Docker Compose (port 7474/7687)
  - Redis 7 via Docker Compose (port 6380)
  - Verified each service starts and accepts connections
  - Remapped ports to avoid conflicts with existing containers
- [x] [SETUP] Environment configuration (PRD Section 14)
  - Created `.env` from `.env.example` with local service URLs
  - Configured `TEST_DATABASE_URL` pointing to local PostgreSQL (port 5433)
  - Verified `.env` is in `.gitignore` (not tracked by git)
  - Documented `TEST_DATABASE_URL` and `DEMO_MODE` in `CODEBASE_CONTEXT.md`

### Testing Infrastructure
- [x] [SETUP] Testing infrastructure (PRD Section 3)
  - Created `pyproject.toml` with pytest + httpx + pytest-asyncio + respx
  - Configured pytest: `asyncio_mode = "auto"`, `integration` marker
  - Created test directory structure: `tests/unit/`, `tests/integration/`, `tests/fixtures/`
  - Created `tests/conftest.py` with async DB session fixtures (transaction rollback cleanup)
  - Wrote DB connectivity smoke test (`tests/integration/test_db_connectivity.py`)
  - Confirmed: `pytest` runs green (1 passed in 0.14s)
- [x] [SETUP] LLM mock infrastructure (PRD Section 6.2) ← moved from Phase 1
  - `respx` for async HTTP mocking of OpenRouter (fixture in `conftest.py`)
  - Response fixtures: `tests/fixtures/llm/openrouter_responses/` (chat_completion.json, embedding.json)
  - `MOCK_LLM=true` env var toggle via `mock_llm` session fixture
  - `@pytest.mark.integration` marker configured in `pyproject.toml`
  - Verified: 5 tests pass (fixture loading, respx interception, MOCK_LLM toggle)
- [x] [SETUP] Config validation tests (PRD Section 14, implied)
  - Created `src/config.py` with Pydantic `BaseSettings` model (all PRD §14 env vars)
  - 32 tests: required fields, defaults, type validation, threshold ranges, enum validation
  - `_NoEnvSettings` subclass for test isolation from `.env` file
  - Verified: 37 total tests pass (32 config + 4 LLM mock + 1 DB)
- [x] [SETUP] Test fixture data (PRD Section 11, implied)
  - `tests/fixtures/sample.txt` (3.5 KB) — RAG architecture content, 5 sections
  - `tests/fixtures/sample.pdf` (3.7 KB, 2 pages) — system design overview, 5 sections
  - Realistic domain content for ingestion pipeline testing

### Python Project Scaffolding
- [x] [SETUP] Python project structure (PRD Section 9)
  - `pyproject.toml` already existed (earlier bootstrap)
  - 16 sub-package `__init__.py` files + 2 empty dirs (`prompts/templates/`, `db/migrations/`)
  - `src/config.py` already existed (config validation task)
  - `src/main.py` — FastAPI app factory with async lifespan, `/api/health` endpoint
  - 5 TDD tests: create_app returns FastAPI, health returns 200/status/environment
  - Verified: 42 total tests pass (5 main + 32 config + 4 LLM mock + 1 DB)
- [x] [SETUP] Environment-specific config profiles (PRD Section 10, 14, cross-cutting)
  - Computed properties: `is_production`, `is_testing`, `debug` on Settings
  - `.env.example` annotated with `# PROD:` notes for production values
  - 6 TDD tests for computed properties
  - Verified: 48 total tests pass (6 env + 32 config + 5 main + 4 LLM mock + 1 DB)
- [x] [FEATURE] Graceful shutdown — `src/main.py` lifespan (PRD Section 10, implied)
  - Shutdown event (`get_shutdown_event()`) set at start of shutdown
  - Timeout-protected `_dispose_resource()` helper (default 5 s, catches errors + timeouts)
  - Ordered resource disposal: Redis → Neo4j → PostgreSQL
  - Structured logging for startup + shutdown (structlog)
  - [x] [TEST] Unit test for shutdown sequence and resource cleanup
    - 7 TDD tests: event set, disposal order (3), error isolation (2), timeout protection
    - Verified: 164 passed, 1 skipped (7 shutdown + 157 pre-existing)

---

## Phase 1: Core RAG Pipeline

### Database Layer
- [x] [FEATURE] Database connection module — `src/db/postgres.py` (PRD Section 4, 9)
  - Async SQLAlchemy engine + session factory (`get_engine`, `get_session_factory`)
  - pgvector extension initialization (`init_pgvector`)
  - Connection pool configuration (pool_size=5, max_overflow=10, pool_recycle=3600)
  - Graceful engine disposal + cache cleanup (`dispose_engine`)
  - Wired into `main.py` lifespan (startup/shutdown)
  - 5 unit tests + 3 integration tests (TDD)
  - Verified: 56 total tests pass (8 postgres + 48 pre-existing)
- [x] [FEATURE] Neo4j driver wrapper — `src/db/neo4j.py` (PRD Section 4.7, 9)
  - Bolt connection via `neo4j` Python driver (AsyncDriver, cached by URI)
  - Constraint creation on app startup (`Entity.id` uniqueness)
  - Graceful degradation on connection failure (`verify_connectivity` returns False)
  - Wired into `main.py` lifespan (startup/shutdown)
  - 4 unit tests + 3 integration tests (TDD)
  - Verified: 63 total tests pass (7 neo4j + 8 postgres + 48 pre-existing)
- [x] [FEATURE] Redis client — `src/db/redis.py` (PRD Section 3, 9)
  - Async client via `redis.asyncio.Redis` (cached by URL, `decode_responses=True`)
  - Health check with graceful degradation (`ping` returns `True`/`False`, never raises)
  - Client disposal + cache eviction (`close_client`)
  - Added `redis[hiredis]>=5.0.0` to `pyproject.toml`
  - Added `TEST_REDIS_URL` to `config.py`
  - 6 unit tests + 1 integration smoke test (TDD)
  - Verified: 62 total tests pass (6 redis + 56 pre-existing)
- [x] [FEATURE] Alembic migration setup (PRD Section 10)
  - Added `alembic>=1.14.0` and `pgvector>=0.3.0` to `pyproject.toml`
  - Created `src/db/models.py` with 7 SQLAlchemy ORM models (Document, Chunk, Conversation, Message, Prompt, Evaluation, SemanticCache)
  - `alembic.ini` + async `env.py` configured (reads DATABASE_URL from Settings)
  - Initial migration `001_initial_schema.py`: all 7 tables + pgvector extension + B-tree and ivfflat indexes
  - 26 unit tests for model schema validation (TDD)
  - Verified: 88 total tests pass (26 models + 62 pre-existing)

### Shared Utilities
- [x] [FEATURE] Structured logging — `src/lib/logger.py` (PRD Section 10b)
  - structlog with JSON output to stdout
  - Request ID correlation (via `bind_context` / `clear_context` using contextvars)
  - Module name context (via `get_logger(__name__)`)
  - `setup_logging()` configures JSON or console renderer, bridges stdlib logging
  - Added `structlog>=24.1.0` to `pyproject.toml`
  - [x] [TEST] Unit tests for logger output format and context propagation
    - 9 TDD tests: bound logger, module context, JSON format, console format, bind/clear context, log levels, setup
    - Verified: 98 total tests pass (9 logger + 89 pre-existing)
- [x] [FEATURE] Utility functions — `src/lib/utils.py` (PRD Section 9)
  - `content_hash(text)` — SHA-256 hex digest with CRLF normalisation for cross-platform dedup
  - `utc_now()` — timezone-aware UTC datetime (replaces naïve `datetime.utcnow()`)
  - `truncate_text(text, max_len=200)` — char-limited truncation with `...` suffix
  - [x] [TEST] Unit tests for hashing and utility functions
    - 15 TDD tests: hex format, determinism, known digest, unicode, whitespace, CRLF, UTC tz, truncation boundaries
    - Verified: 119 passed, 1 skipped (120 total = 15 utils + 105 pre-existing)

### API Foundation
- [x] [FEATURE] Request ID middleware (PRD Section 10b, implied)
  - Generate UUID per request, attach to structlog context
  - Pass through to all log entries for correlation
  - Honours client-provided `X-Request-ID` for distributed tracing
  - Returns `X-Request-ID` response header
  - Registered in `src/main.py` via `app.add_middleware(RequestIDMiddleware)`
  - [x] [TEST] Unit test for UUID generation and structlog context binding
    - 7 TDD tests: header presence, UUID4 validity, uniqueness, client-provided ID, empty/whitespace edge cases, context cleanup
    - Verified: 126 passed, 1 skipped (7 request ID + 119 pre-existing)
- [x] [FEATURE] Auth middleware — `src/api/middleware/auth.py` (PRD Section 8b)
  - Implemented as FastAPI dependency (`require_api_key`) — per-route control, health stays public
  - API key validation via `X-API-Key` header against comma-split `API_KEYS` config
  - User identification via `X-User-Id` header (defaults to `"anonymous"`)
  - PRD error format: `{ error: { code, message } }` — 401 `MISSING_API_KEY`, 403 `INVALID_API_KEY`
  - [x] [TEST] Unit test for API key validation, missing header rejection, user ID extraction
    - 8 TDD tests: valid key, missing header 401, error code, invalid key 403, error format, user ID extraction, default anonymous, multi-key support
    - Verified: 134 passed, 1 skipped (8 auth + 126 pre-existing)
- [x] [FEATURE] Rate limiting middleware — `src/api/middleware/rate_limit.py` (PRD Section 8b)
  - Fixed-window Redis counter (`INCR` + `EXPIRE`) per api_key:path:minute
  - Per-endpoint limits from PRD §8b API table (10–200/min)
  - Fail-open on Redis errors (graceful degradation)
  - Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
  - 429 `RATE_LIMIT_EXCEEDED` with PRD error format + `Retry-After` header
  - `/api/health` exempt
  - Registered in `src/main.py` via `app.add_middleware(RateLimitMiddleware)`
  - [x] [TEST] Unit test for counter logic, window expiry, Redis interaction
    - 7 TDD tests: under limit, over limit 429, headers present, health exempt, Redis fail-open, per-endpoint limits, key isolation
    - Verified: 141 passed, 1 skipped (7 rate limit + 134 pre-existing)
- [x] [FEATURE] Error handling middleware — `src/api/middleware/errors.py` (PRD Section 8b)
  - Consistent error format: `{ error: { code, message, details } }`
  - Never leak stack traces in production
  - FastAPI exception handlers for HTTPException, RequestValidationError + catch-all middleware
  - Auth/rate-limit pre-shaped errors unwrapped; status codes mapped to UPPER_SNAKE codes
  - [x] [TEST] Unit test for error format, stack trace suppression, HTTP status codes
    - 8 TDD tests: PRD format, status preservation, auth unwrap, validation 422, dev traceback, prod suppression, consistency, success passthrough
    - Verified: 149 passed, 1 skipped (8 error handling + 141 pre-existing)
- [x] [FEATURE] Health endpoint — `GET /api/health` (PRD Section 8b, 10b)
  - PostgreSQL connectivity check + pgvector extension loaded
  - Neo4j connectivity check
  - Redis connectivity check
  - LLM provider reachability (OpenRouter `/models` ping)
  - [x] [TEST] 8 TDD tests: all-healthy, pg/neo4j/redis/llm down, pgvector missing, env+version, multi-failure
  - Verified: 151 passed, 1 skipped (11 health + 140 pre-existing)

### Document Ingestion
- [x] [FEATURE] Text extractor — `src/ingestion/extractors/text.py` (PRD Section 5.1)
  - Plain text passthrough
  - [x] [TEST] Unit test for text extractor
- [x] [FEATURE] PDF extractor — `src/ingestion/extractors/pdf.py` (PRD Section 5.1)
  - PDF text extraction via `pdfplumber`
  - Scanned image warning (no OCR)
  - [x] [TEST] Unit test for PDF extractor
- [x] [FEATURE] Markdown extractor — `src/ingestion/extractors/markdown.py` (PRD Section 5.1)
  - Markdown (.md) file passthrough with frontmatter stripping
  - [x] [TEST] Unit test for Markdown extractor
- [x] [FEATURE] URL extractor — `src/ingestion/extractors/url.py` (PRD Section 5.1)
  - URL scraping via `httpx` + `BeautifulSoup`
  - [x] [TEST] Unit test for URL extractor
- [x] [FEATURE] Text chunker — `src/ingestion/chunker.py` (PRD Section 5.1)
  - Recursive character splitting: 512 tokens/chunk, 50-token overlap
  - Configurable via `CHUNK_SIZE`, `CHUNK_OVERLAP`
- [x] [FEATURE] Embedding generator — `src/ingestion/embedder.py` (PRD Section 5.1)
  - OpenRouter embedding API wrapper (`openai/text-embedding-3-small`)
  - Batch embedding support
  - Error handling: mark document `'failed'` on API failure
- [x] [FEATURE] Ingestion pipeline — `src/ingestion/pipeline.py` (PRD Section 5.1)
  - Accept document → extract → deduplicate by content_hash → chunk → embed → store
  - Update document status: `pending` → `chunked` → `embedded` / `failed`
  - Reject empty documents with `EMPTY_DOCUMENT` error
  - Return existing document ID on duplicate content hash
- [x] [FEATURE] Cursor-based pagination utility (PRD Section 8b)
  - Reusable cursor + limit pagination for all list endpoints
  - Default page size 25, max 100
  - [x] [TEST] Unit test for cursor encoding/decoding, limit capping, edge cases
- [x] [FEATURE] Document API endpoints (PRD Section 8b)
  - `POST /api/documents` — file upload → ingest
  - `POST /api/documents/url` — URL → ingest
  - `GET /api/documents` — list documents (cursor pagination, filters: status, source, created_after)
  - `GET /api/documents/:id` — get document + chunk count
  - `DELETE /api/documents/:id` — delete document + cascading chunks
- [ ] [VERIFY] Phase 1 test coverage ≥ 80% — `pytest --cov`

### Vector Search
- [x] [FEATURE] Vector search — `src/retrieval/vector_search.py` (PRD Section 5.2)
  - pgvector cosine similarity query
  - Top-K retrieval (configurable, default 10)
  - Similarity threshold filtering (default 0.7)
- [x] [FEATURE] Search API endpoint — `POST /api/search` (PRD Section 8b)
  - Query embedding + pgvector search
  - Return results with relevance scores + source metadata
  - Filters: `document_ids`, `metadata`

### Basic Chat
- [x] [FEATURE] OpenRouter API client — `src/llm/openrouter.py` (PRD Section 5.3, 6.1)
  - OpenAI-compatible REST client for `/api/v1/chat/completions`
  - Authentication via `Authorization: Bearer` + `X-Title` + `HTTP-Referer`
  - Error handling: 429 → backoff, 5xx → fallback, 402 → COST_LIMIT_EXCEEDED, timeout → downgrade
- [x] [FEATURE] Chat API route file — `src/api/routes/chat.py` (PRD Section 8b, 9)
  - Register router with FastAPI app
  - `POST /api/chat/sync` — Query → retrieve context → LLM call → response
  - Return: `{ response, sources, model_used, cost }`

---

## Phase 2: Multi-Model + Agents

### Multi-Model Router
- [x] [FEATURE] Model routing logic — `src/llm/router.py` (PRD Section 5.3) ✅ 5 tests
  - ROUTING_TABLE with task-type → model mapping
  - `preferred_model` passthrough bypass
  - `max_cost` budget enforcement → downgrade to `deepseek/deepseek-chat`
  - `routed_chat_completion()` wrapper

### Streaming
- [x] [FEATURE] SSE streaming — `src/llm/streaming.py` (PRD Section 5.3) ✅ 3 tests
  - Async generator yielding SSE events from OpenRouter
  - `format_sse()` helper for event formatting
- [x] [FEATURE] Streaming chat endpoint — `POST /api/chat` (PRD Section 8b) ✅ 1 test
  - `StreamingResponse` with `text/event-stream` content type

### Cost Tracking
- [x] [FEATURE] Cost tracker — `src/llm/cost_tracker.py` (PRD Section 5.3) ✅ 7 tests
  - `CostRecord` dataclass (tokens_in/out, cost_usd, model, user_id)
  - Per-user daily aggregation
  - `check_budget()` with `DAILY_COST_LIMIT_USD` enforcement

### Agent Executor
- [x] [FEATURE] Tool registry — `src/agents/registry.py` (PRD Section 5.4) ✅ 5 tests
  - `ToolSpec` dataclass + `ToolRegistry` with whitelist enforcement
  - `to_openai_tools()` export for function-calling API
- [x] [FEATURE] Search KB tool — `src/agents/tools/search_kb.py` ✅ 2 tests
- [x] [FEATURE] Query graph tool — `src/agents/tools/query_graph.py` ✅ 2 tests (write-blocking regex)
- [x] [FEATURE] Calculate tool — `src/agents/tools/calculate.py` ✅ 3 tests (AST-safe eval)
- [x] [FEATURE] Get current time tool — `src/agents/tools/get_time.py` ✅ 2 tests
- [x] [FEATURE] Summarize tool — `src/agents/tools/summarize.py` ✅ 2 tests
- [x] [FEATURE] Agent executor — `src/agents/executor.py` (PRD Section 5.4) ✅ 4 tests
  - Pure Python ReAct loop (no LangGraph dependency)
  - Multi-step tool chains (LLM → tool → result → tool → synthesize)
  - Max 5 tool calls per turn
  - Whitelist enforcement rejects unregistered tools

### Conversations
- [x] [FEATURE] Conversation CRUD API — `src/api/routes/conversations.py` (PRD Section 4.3, 8b) ✅ 5 tests
  - `POST /api/conversations` — create conversation
  - `GET /api/conversations?user_id=X` — list user conversations
  - `GET /api/conversations/:id` — get with messages
  - `DELETE /api/conversations/:id` — delete + cascade
  - `POST /api/conversations/:id/messages` — add message with token tracking
  - In-memory store (swap to DB session in wiring phase)
- [x] [VERIFY] Phase 2 tests — 44 new tests, 255 total passing

---

## Phase 3: Guardrails + Memory

### Input Guardrails
- [x] [FEATURE] Prompt injection detection — `src/guardrails/injection.py` (PRD Section 5.5)
  - Pattern matching for common injection patterns
  - Score 0.0–1.0, block if > 0.8 (`GUARDRAIL_INJECTION_THRESHOLD`)
- [x] [FEATURE] PII detection — `src/guardrails/pii.py` (PRD Section 5.5)
  - Regex scan for SSN, credit card, phone, email
  - Configurable mode: flag / block / redact (`GUARDRAIL_PII_MODE`)
- [x] [FEATURE] Topic policy — `src/guardrails/pipeline.py` (PRD Section 5.5)
  - Configurable denied topics blocklist
  - Token budget check: reject if estimated cost exceeds session budget

### Output Guardrails
- [x] [FEATURE] Hallucination detection — `src/guardrails/hallucination.py` (PRD Section 5.5)
  - Compare LLM response against source chunks
  - Flag ungrounded claims
- [x] [FEATURE] Content safety checking — `src/guardrails/content_safety.py` (PRD Section 5.5)
  - Check for hate, violence, sexual content
  - Keyword patterns + LLM-as-judge
- [x] [FEATURE] Source attribution verification — `src/guardrails/pipeline.py` (PRD Section 5.5)
  - Verify cited sources exist in retrieval results
- [x] [FEATURE] Guardrail pipeline integration — input wiring (PRD Section 5.5)
  - Wire input guardrails (injection + PII + topic policy) to run pre-LLM on every request
  - Return: `{ passed, flags: [{ type, severity, detail }] }`
- [x] [FEATURE] Guardrail pipeline integration — output wiring (PRD Section 5.5)
  - Wire output guardrails (hallucination + content safety + source attribution) to run post-LLM
  - Store guardrail_flags in messages table

### Conversation Memory
- [x] [FEATURE] Short-term memory — `src/memory/short_term.py` (PRD Section 5.6)
  - Keep last N messages in context window (`MEMORY_WINDOW_SIZE`, default 20)
- [x] [FEATURE] Long-term memory — `src/memory/long_term.py` (PRD Section 5.6)
  - Summarize older messages using cheap LLM (Gemini Flash) when context limit exceeded
  - Store summaries for conversation continuity
- [x] [FEATURE] Entity memory — `src/memory/entity.py` (PRD Section 5.6)
  - Extract named entities from conversations → store in Neo4j
  - Retrieve entity context on new turns for personalization
- [x] [FEATURE] Memory manager — `src/memory/manager.py` (PRD Section 5.6)
  - Orchestrate short-term + long-term + entity memory
  - Return: `{ context_messages, entity_context, memory_summary? }`

### Knowledge Graph Integration
- [x] [FEATURE] Entity extraction during ingestion (PRD Section 5.1 step 7)
  - Extract people, organizations, dates, concepts from document chunks
  - Upsert entities + relationships into Neo4j
- [x] [FEATURE] Graph search — `src/retrieval/graph_search.py` (PRD Section 5.2)
  - Query Neo4j for entities related to query entities
  - Pull in chunks from related documents for context expansion
- [x] [FEATURE] Reranker — `src/retrieval/reranker.py` (PRD Section 5.2)
  - Score results: `0.7 * vector_similarity + 0.2 * keyword_overlap + 0.1 * graph_relevance`
  - Return top-N reranked results
- [x] [FEATURE] Hybrid retrieval engine — `src/retrieval/engine.py` (PRD Section 5.2)
  - Orchestrate: vector search → keyword boost → graph expansion → reranking
  - Return top-5 results with scores and source metadata
- [x] [FEATURE] Graph API endpoints (PRD Section 8b)
  - `GET /api/graph/entities` — list entities
  - `GET /api/graph/related/:entityId` — get entity + relationships
- [x] [VERIFY] Phase 3 test coverage ≥ 80% — `pytest --cov` (achieved: 89%)

---

## Phase 4: Cache + Evaluation + MCP

### Semantic Cache
- [x] [FEATURE] Semantic cache — `src/cache/semantic.py` (PRD Section 5.7)
  - Embed query → search cache for vectors with cosine similarity > 0.95
  - Cache hit → return cached response, skip LLM call, increment hit_count
  - Cache miss → process normally, store query + response with TTL
  - Expire entries after 24h (`CACHE_TTL_HOURS`)
  - Invalidate when knowledge base updated (new document ingested)
- [x] [FEATURE] In-memory embedding LRU cache (PRD Section 10b)
  - LRU cache for repeat embedding queries within a session
  - Avoid re-embedding identical query strings
- [x] [FEATURE] Cache stats endpoint — `GET /api/cache/stats` (PRD Section 8b)
  - Total entries, hit rate, estimated cost saved

### Prompt Registry
- [x] [FEATURE] Prompt registry — `src/prompts/registry.py` (PRD Section 4.4, 5)
  - CRUD operations for Jinja2 prompt templates
  - Versioning (auto-increment on update)
  - `is_active` flag for A/B testing
  - `model_hint` field for suggested model per prompt
- [x] [FEATURE] Initial Jinja2 prompt templates — `src/prompts/templates/` (PRD Section 9, implied)
  - System prompt template for RAG chat
  - Summarization prompt template
  - Evaluation judge prompt templates
- [x] [FEATURE] Prompt API endpoints (PRD Section 8b)
  - `POST /api/prompts` — create prompt
  - `GET /api/prompts` — list prompts
  - `PUT /api/prompts/:id` — update prompt (increments version)

### Evaluation Harness
- [x] [FEATURE] Relevance scorer — `src/evaluation/relevance.py` (PRD Section 5.9)
  - LLM-as-judge: are retrieved chunks relevant to the query?
- [x] [FEATURE] Faithfulness scorer — `src/evaluation/faithfulness.py` (PRD Section 5.9)
  - Claim extraction + verification against source chunks
- [x] [FEATURE] Correctness scorer — `src/evaluation/correctness.py` (PRD Section 5.9)
  - LLM-as-judge: does the response answer the question?
- [x] [FEATURE] Evaluation harness — `src/evaluation/harness.py` (PRD Section 5.9)
  - Run all metrics after each RAG response
  - Store scores in `evaluations` table
  - Flag responses below threshold (`EVAL_MIN_THRESHOLD`, default 0.7)
- [x] [FEATURE] Metrics API route file — `src/api/metrics.py` (PRD Section 8b, 9)
  - `GET /api/metrics/cost` — total cost, by model, by day
  - `GET /api/metrics/quality` — avg relevance, avg faithfulness, by model

### MCP Server
- [x] [FEATURE] MCP server implementation — `src/mcp/server.py` (PRD Section 5.8)
  - MCP server using `mcp` Python SDK
  - Tools: `search_documents`, `ingest_document`, `query_graph`, `get_conversation_history`
  - Resources: `document://`, `conversation://` URI schemes
  - Tool discovery, parameter validation, execution
  - Compatible with MCP-aware clients (Claude Desktop, Cursor)
  - Port: `MCP_SERVER_PORT` (default 3001), Transport: `MCP_TRANSPORT` (default `stdio`)
  - [x] [TEST] Integration test for MCP tool discovery and execution
- [x] [VERIFY] Phase 4 test coverage ≥ 80% — achieved **95%** (378 total tests passing)

---

## Phase 5: Deploy + Polish

### Background Jobs
- [x] [FEATURE] Cache cleanup job (PRD Section 7)
  - Delete expired `semantic_cache` entries — every 1h
- [x] [FEATURE] Conversation summary job (PRD Section 7)
  - Summarize long conversations exceeding memory window — every 6h
- [x] [FEATURE] Evaluation aggregation job (PRD Section 7)
  - Pre-compute aggregate quality metrics — every 24h
- [x] [FEATURE] Cost budget reset job (PRD Section 7)
  - Reset daily cost budgets per user — daily at midnight UTC
- [x] [FEATURE] Knowledge graph sync job (PRD Section 7)
  - Async background worker triggered on document ingestion
  - Runs entity extraction → upsert Neo4j (distinct from inline extraction in Phase 3)
  - Wire as FastAPI background task from ingestion pipeline

### Deployment
- [x] [FEATURE] Production Docker Compose (PRD Section 10)
  - FastAPI app + PostgreSQL 16/pgvector + Neo4j 5 Community + Redis 7
  - Traefik labels for `ai.kingsleyonoh.com` with auto TLS
- [x] [FEATURE] Deploy to Hetzner VPS (PRD Section 10)
  - SSH deploy: pull → build → migrate → restart
  - Traefik health-based routing

### Monitoring & Observability
- [x] [FEATURE] BetterStack uptime monitoring (PRD Section 10b)
  - Poll `/api/health` endpoint
- [x] [FEATURE] Alerting rules implementation (PRD Section 10b)
  - Health non-200 for 3 checks → critical
  - Daily LLM spend > $10 → warning
  - Guardrail block rate > 30% in 1h → warning
  - Avg RAG relevance < 0.6 over 24h → warning

### Testing & QA
- [ ] [FEATURE] Full integration test suite (PRD Section 6.2, Phase 5)
  - End-to-end tests covering all API endpoints
  - Verify mock infrastructure from Phase 1 covers all LLM call paths
- [ ] [FEATURE] Load test with concurrent chat sessions (PRD Phase 5, Section 10b)
  - Concurrent user simulation
  - Validate: chat first token (p95) < 1.5s
  - Validate: retrieval latency (p95) < 200ms
  - Validate: document ingestion < 2s/page
  - Validate: semantic cache lookup (p95) < 50ms
  - Validate: embedding generation < 300ms/chunk
  - Validate: cache hit rate > 20% at steady state
- [ ] [FEATURE] Seed knowledge base with sample documents (PRD Phase 5)
  - Sample PDF, TXT, URL documents for demo
- [ ] [VERIFY] Phase 5 test coverage ≥ 80% — `pytest --cov`

---

## Success Criteria (PRD Section 15)

- [ ] Documents ingest, chunk, and embed successfully with pgvector storage
- [ ] Vector search returns relevant chunks with > 0.7 similarity scores
- [ ] Chat responses are grounded in retrieved context (faithfulness > 0.8)
- [ ] Multi-model routing correctly selects providers based on task type
- [ ] Agent tool calling executes registered tools and returns results to LLM
- [ ] Guardrails block prompt injection attempts with > 90% accuracy
- [ ] Semantic cache serves repeated queries without LLM calls (cache hit rate measurable)
- [ ] Knowledge graph enriches retrieval results with entity relationships
- [ ] MCP server is discoverable and callable by external MCP clients
- [ ] Cost tracking reports accurate per-model, per-request spending
- [ ] All tests pass with > 80% coverage
- [ ] System deploys with `docker compose up`

---

## Future Work — Deployable AI Infrastructure Layer (Deferred)

> **Vision:** Position this platform as the reusable AI backend you deploy and customize for each client engagement — not a SaaS product, but the engine behind client products.

### Why This Direction
- No need for thousands of users — one client deployment = one case study
- Aligns with the Architect positioning: you're selling expertise, not seats
- Every "chat with your docs" client project starts from this foundation instead of zero

### What It Would Take

#### Deployment Kit
- [ ] One-command deployment script (`deploy.sh` — Docker Compose + env setup)
- [ ] Client environment template (`.env.client` with per-client config)
- [ ] Data isolation strategy — single-tenant by default, namespace by `tenant_id` for multi-tenant
- [ ] Backup/restore scripts for client knowledge bases

#### Client Onboarding
- [ ] Bulk document upload CLI tool (point at a folder, ingest everything)
- [ ] Admin dashboard — document status, usage stats, cost tracking
- [ ] Simple chat UI template (React/Next.js) that clients can brand
- [ ] Onboarding runbook: "Deploy in 30 minutes" guide

#### Productionisation
- [ ] Background job queue (Celery or BullMQ) for async document ingestion
- [ ] Real DB session injection in all API routes (replace skeleton wiring)
- [ ] API key authentication per client (not just rate limiting)
- [ ] Usage metering and cost pass-through (track per-client LLM spend)
- [ ] Webhook notifications (ingestion complete, error alerts)

#### Differentiation for Case Studies
- [ ] Before/after metrics template: "Search time reduced from X to Y"
- [ ] Source citation confidence scoring (how grounded is each answer)
- [ ] Conversation history + follow-up context (multi-turn chat)
- [ ] Export audit trail (every answer traceable to source chunks)

### First Client Engagement Playbook
1. Deploy platform on client's infrastructure (or your VPS)
2. Bulk-ingest their document corpus
3. Wire a simple branded chat frontend to the API
4. Measure: search time, answer accuracy, user adoption
5. Write Foundry case study with before/after metrics
6. Use case study to land next engagement
