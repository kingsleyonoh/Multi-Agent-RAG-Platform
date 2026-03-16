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
- [ ] [SETUP] Test fixture data (PRD Section 11, implied)
  - Create `tests/fixtures/sample.pdf` and `tests/fixtures/sample.txt`
  - Provide realistic test documents for dev and integration testing

### Python Project Scaffolding
- [ ] [SETUP] Python project structure (PRD Section 9)
  - Create `pyproject.toml` with project metadata + dependencies
  - Create `src/` directory structure matching PRD Section 9
  - Create `src/__init__.py` and all sub-package `__init__.py` files
  - Create `src/config.py` with Pydantic settings model (validate all PRD §14 env vars)
    - Include: `EMBEDDING_MODEL`, `RETRIEVAL_TOP_K`, `RERANK_TOP_N`, `SIMILARITY_THRESHOLD`
    - Include: `CACHE_SIMILARITY_THRESHOLD`, `CACHE_TTL_HOURS`, `EVAL_JUDGE_MODEL`
  - Create `src/main.py` with FastAPI app factory + lifespan handler for graceful shutdown
- [ ] [SETUP] Environment-specific config profiles (PRD Section 10, 14, cross-cutting)
  - Production vs development config differentiation
  - Document prod env vars in `.env.example`

---

## Phase 1: Core RAG Pipeline

### Database Layer
- [ ] [FEATURE] Database connection module — `src/db/postgres.py` (PRD Section 4, 9)
  - Async SQLAlchemy engine + session factory
  - pgvector extension initialization
  - Connection pool configuration
- [ ] [FEATURE] Neo4j driver wrapper — `src/db/neo4j.py` (PRD Section 4.7, 9)
  - Bolt connection via `neo4j` Python driver
  - Constraint creation on app startup
  - Graceful degradation on connection failure
- [ ] [FEATURE] Redis client — `src/db/redis.py` (PRD Section 3, 9)
  - Redis connection for semantic cache + session store
  - Health check method
- [ ] [FEATURE] Alembic migration setup (PRD Section 10)
  - `alembic.ini` configuration
  - Initial migration: `documents` table (PRD Section 4.1)
  - Migration: `chunks` table with pgvector column (PRD Section 4.2)
  - Migration: `conversations` table (PRD Section 4.3)
  - Migration: `messages` table (PRD Section 4.3)
  - Migration: `prompts` table (PRD Section 4.4)
  - Migration: `evaluations` table (PRD Section 4.5)
  - Migration: `semantic_cache` table (PRD Section 4.6)

### Shared Utilities
- [ ] [FEATURE] Structured logging — `src/lib/logger.py` (PRD Section 10b)
  - structlog with JSON output to stdout
  - Request ID correlation
  - Module name context
  - [ ] [TEST] Unit tests for logger output format and context propagation
- [ ] [FEATURE] Utility functions — `src/lib/utils.py` (PRD Section 9)
  - SHA-256 content hashing for dedup
  - Common helpers
  - [ ] [TEST] Unit tests for hashing and utility functions

### API Foundation
- [ ] [FEATURE] Request ID middleware (PRD Section 10b, implied)
  - Generate UUID per request, attach to structlog context
  - Pass through to all log entries for correlation
- [ ] [FEATURE] Auth middleware — `src/api/middleware/auth.py` (PRD Section 8b)
  - API key validation via `X-API-Key` header
  - User identification via `X-User-Id` header
- [ ] [FEATURE] Rate limiting middleware — `src/api/middleware/rate_limit.py` (PRD Section 8b)
  - Per-endpoint rate limits (see rate limit column in API table)
  - Redis-backed counter
- [ ] [FEATURE] Error handling middleware — `src/api/middleware/errors.py` (PRD Section 8b)
  - Consistent error format: `{ error: { code, message, details } }`
  - Never leak stack traces in production
- [ ] [FEATURE] Health endpoint — `GET /api/health` (PRD Section 8b, 10b)
  - PostgreSQL connectivity check + pgvector extension loaded
  - Neo4j connectivity check
  - Redis connectivity check
  - LLM provider reachability (lightweight ping)

### Document Ingestion
- [ ] [FEATURE] Text extractor — `src/ingestion/extractors/text.py` (PRD Section 5.1)
  - Plain text passthrough
  - [ ] [TEST] Unit test for text extractor
- [ ] [FEATURE] PDF extractor — `src/ingestion/extractors/pdf.py` (PRD Section 5.1)
  - PDF text extraction via `pdfplumber`
  - Scanned image warning (no OCR)
  - [ ] [TEST] Unit test for PDF extractor
- [ ] [FEATURE] Markdown extractor — `src/ingestion/extractors/markdown.py` (PRD Section 5.1)
  - Markdown (.md) file passthrough
  - [ ] [TEST] Unit test for Markdown extractor
- [ ] [FEATURE] URL extractor — `src/ingestion/extractors/url.py` (PRD Section 5.1)
  - URL scraping via `httpx` + `BeautifulSoup`
  - [ ] [TEST] Unit test for URL extractor
- [ ] [FEATURE] Text chunker — `src/ingestion/chunker.py` (PRD Section 5.1)
  - Recursive character splitting: 512 tokens/chunk, 50-token overlap
  - Configurable via `CHUNK_SIZE`, `CHUNK_OVERLAP`
- [ ] [FEATURE] Embedding generator — `src/ingestion/embedder.py` (PRD Section 5.1)
  - OpenRouter embedding API wrapper (`openai/text-embedding-3-small`)
  - Batch embedding support
  - Error handling: mark document `'failed'` on API failure
- [ ] [FEATURE] Ingestion pipeline — `src/ingestion/pipeline.py` (PRD Section 5.1)
  - Accept document → extract → deduplicate by content_hash → chunk → embed → store
  - Update document status: `pending` → `chunked` → `embedded` / `failed`
  - Reject empty documents with `EMPTY_DOCUMENT` error
  - Return existing document ID on duplicate content hash
- [ ] [FEATURE] Cursor-based pagination utility (PRD Section 8b)
  - Reusable cursor + limit pagination for all list endpoints
  - Default page size 25, max 100
- [ ] [FEATURE] Document API endpoints (PRD Section 8b)
  - `POST /api/documents` — file upload → ingest
  - `POST /api/documents/url` — URL → ingest
  - `GET /api/documents` — list documents (cursor pagination, filters: status, source, created_after)
  - `GET /api/documents/:id` — get document + chunk count
  - `DELETE /api/documents/:id` — delete document + cascading chunks
- [ ] [VERIFY] Phase 1 test coverage ≥ 80% — `pytest --cov`

### Vector Search
- [ ] [FEATURE] Vector search — `src/retrieval/vector_search.py` (PRD Section 5.2)
  - pgvector cosine similarity query
  - Top-K retrieval (configurable, default 10)
  - Similarity threshold filtering (default 0.7)
- [ ] [FEATURE] Search API endpoint — `POST /api/search` (PRD Section 8b)
  - Query embedding + pgvector search
  - Return results with relevance scores + source metadata
  - Filters: `document_ids`, `metadata`

### Basic Chat
- [ ] [FEATURE] OpenRouter API client — `src/llm/openrouter.py` (PRD Section 5.3, 6.1)
  - OpenAI-compatible REST client for `/api/v1/chat/completions`
  - Authentication via `Authorization: Bearer` + `X-Title` + `HTTP-Referer`
  - Error handling: 429 → backoff, 5xx → fallback, 402 → COST_LIMIT_EXCEEDED, timeout → downgrade
- [ ] [FEATURE] Basic chat endpoint — `POST /api/chat/sync` (PRD Section 8b)
  - Query → retrieve context → LLM call → response
  - Return: `{ response, sources, model_used, cost }`

---

## Phase 2: Multi-Model + Agents

### Multi-Model Router
- [ ] [FEATURE] Model routing logic — `src/llm/router.py` (PRD Section 5.3)
  - Task-type routing rules:
    - Simple Q&A / summarization → `google/gemini-2.0-flash-exp`
    - Complex reasoning / analysis → `anthropic/claude-3.5-sonnet` or `openai/gpt-4o`
    - Code generation → `anthropic/claude-3.5-sonnet`
    - Structured extraction → `openai/gpt-4o` (JSON mode)
    - Cost-optimized → `deepseek/deepseek-chat`
  - `preferred_model` passthrough
  - `max_cost` budget enforcement → downgrade to cheaper model
  - Fallback chain on provider unavailability (5xx/timeout)

### Streaming
- [ ] [FEATURE] SSE streaming — `src/llm/streaming.py` (PRD Section 5.3)
  - Server-Sent Events for chat responses
  - Stream format: `{ token, sources?, tool_call?, done }`
- [ ] [FEATURE] Streaming chat endpoint — `POST /api/chat` (PRD Section 8b)
  - SSE stream of tokens with sources and tool calls

### Cost Tracking
- [ ] [FEATURE] Cost tracker — `src/llm/cost_tracker.py` (PRD Section 5.3, Arch Principle 5)
  - Token counting per request (tokens_in, tokens_out)
  - Dollar cost tracking per request (from OpenRouter response headers)
  - Per-user cost aggregation
  - Daily cost budget enforcement (`DAILY_COST_LIMIT_USD`)

### Agent Executor
- [ ] [FEATURE] Tool registry — `src/agents/registry.py` (PRD Section 5.4)
  - Tool whitelist management
  - Tool registration with name, description, parameters
- [ ] [FEATURE] Search KB tool — `src/agents/tools/search_kb.py` (PRD Section 5.4)
  - Knowledge base vector search tool for agent use
  - [ ] [TEST] Unit test for search_kb tool
- [ ] [FEATURE] Query graph tool — `src/agents/tools/query_graph.py` (PRD Section 5.4)
  - Neo4j Cypher query tool for agent use
  - [ ] [TEST] Unit test for query_graph tool
- [ ] [FEATURE] Calculate tool — `src/agents/tools/calculate.py` (PRD Section 5.4)
  - Safe math expression evaluator
  - [ ] [TEST] Unit test for calculate tool
- [ ] [FEATURE] Get current time tool — `src/agents/tools/get_time.py` (PRD Section 5.4)
  - Returns UTC timestamp
  - [ ] [TEST] Unit test for get_time tool
- [ ] [FEATURE] Summarize tool — `src/agents/tools/summarize.py` (PRD Section 5.4)
  - Document summarization by ID
  - [ ] [TEST] Unit test for summarize tool
- [ ] [FEATURE] Agent executor — `src/agents/executor.py` (PRD Section 5.4)
  - LangGraph-based agent executor
  - Multi-step tool chains (LLM → tool → result → tool → synthesize)
  - Max 5 tool calls per turn (`MAX_TOOL_CALLS_PER_TURN`)
  - Log every tool invocation: name, args, result, latency

### Conversations
- [ ] [FEATURE] Conversation persistence — `src/api/conversations.py` (PRD Section 4.3, 8b)
  - `GET /api/conversations` — list conversations (cursor pagination, filters: user_id, created_after)
  - `GET /api/conversations/:id` — get conversation with messages
  - `DELETE /api/conversations/:id` — delete conversation + cascading messages
  - Support `model_preference` field per conversation (user's preferred model)
- [ ] [FEATURE] Message history tracking (PRD Section 4.3)
  - Store role, content, model_used, tokens, cost, latency, tool_calls, sources, guardrail_flags per message
  - Track total_tokens and total_cost_usd per conversation
- [ ] [VERIFY] Phase 2 test coverage ≥ 80% — `pytest --cov`

---

## Phase 3: Guardrails + Memory

### Input Guardrails
- [ ] [FEATURE] Prompt injection detection — `src/guardrails/injection.py` (PRD Section 5.5)
  - Pattern matching for common injection patterns
  - Score 0.0–1.0, block if > 0.8 (`GUARDRAIL_INJECTION_THRESHOLD`)
- [ ] [FEATURE] PII detection — `src/guardrails/pii.py` (PRD Section 5.5)
  - Regex scan for SSN, credit card, phone, email
  - Configurable mode: flag / block / redact (`GUARDRAIL_PII_MODE`)
- [ ] [FEATURE] Topic policy — `src/guardrails/pipeline.py` (PRD Section 5.5)
  - Configurable denied topics blocklist
  - Token budget check: reject if estimated cost exceeds session budget

### Output Guardrails
- [ ] [FEATURE] Hallucination detection — `src/guardrails/hallucination.py` (PRD Section 5.5)
  - Compare LLM response against source chunks
  - Flag ungrounded claims
- [ ] [FEATURE] Content safety checking — `src/guardrails/content_safety.py` (PRD Section 5.5)
  - Check for hate, violence, sexual content
  - Keyword patterns + LLM-as-judge
- [ ] [FEATURE] Source attribution verification — `src/guardrails/pipeline.py` (PRD Section 5.5)
  - Verify cited sources exist in retrieval results
- [ ] [FEATURE] Guardrail pipeline integration — input wiring (PRD Section 5.5)
  - Wire input guardrails (injection + PII + topic policy) to run pre-LLM on every request
  - Return: `{ passed, flags: [{ type, severity, detail }] }`
- [ ] [FEATURE] Guardrail pipeline integration — output wiring (PRD Section 5.5)
  - Wire output guardrails (hallucination + content safety + source attribution) to run post-LLM
  - Store guardrail_flags in messages table

### Conversation Memory
- [ ] [FEATURE] Short-term memory — `src/memory/short_term.py` (PRD Section 5.6)
  - Keep last N messages in context window (`MEMORY_WINDOW_SIZE`, default 20)
- [ ] [FEATURE] Long-term memory — `src/memory/long_term.py` (PRD Section 5.6)
  - Summarize older messages using cheap LLM (Gemini Flash) when context limit exceeded
  - Store summaries for conversation continuity
- [ ] [FEATURE] Entity memory — `src/memory/entity.py` (PRD Section 5.6)
  - Extract named entities from conversations → store in Neo4j
  - Retrieve entity context on new turns for personalization
- [ ] [FEATURE] Memory manager — `src/memory/manager.py` (PRD Section 5.6)
  - Orchestrate short-term + long-term + entity memory
  - Return: `{ context_messages, entity_context, memory_summary? }`

### Knowledge Graph Integration
- [ ] [FEATURE] Entity extraction during ingestion (PRD Section 5.1 step 7)
  - Extract people, organizations, dates, concepts from document chunks
  - Upsert entities + relationships into Neo4j
- [ ] [FEATURE] Graph search — `src/retrieval/graph_search.py` (PRD Section 5.2)
  - Query Neo4j for entities related to query entities
  - Pull in chunks from related documents for context expansion
- [ ] [FEATURE] Reranker — `src/retrieval/reranker.py` (PRD Section 5.2)
  - Score results: `0.7 * vector_similarity + 0.2 * keyword_overlap + 0.1 * graph_relevance`
  - Return top-N reranked results
- [ ] [FEATURE] Hybrid retrieval engine — `src/retrieval/engine.py` (PRD Section 5.2)
  - Orchestrate: vector search → keyword boost → graph expansion → reranking
  - Return top-5 results with scores and source metadata
- [ ] [FEATURE] Graph API endpoints (PRD Section 8b)
  - `GET /api/graph/entities` — list entities
  - `GET /api/graph/related/:entityId` — get entity + relationships
- [ ] [VERIFY] Phase 3 test coverage ≥ 80% — `pytest --cov`

---

## Phase 4: Cache + Evaluation + MCP

### Semantic Cache
- [ ] [FEATURE] Semantic cache — `src/cache/semantic.py` (PRD Section 5.7)
  - Embed query → search cache for vectors with cosine similarity > 0.95
  - Cache hit → return cached response, skip LLM call, increment hit_count
  - Cache miss → process normally, store query + response with TTL
  - Expire entries after 24h (`CACHE_TTL_HOURS`)
  - Invalidate when knowledge base updated (new document ingested)
- [ ] [FEATURE] In-memory embedding LRU cache (PRD Section 10b)
  - LRU cache for repeat embedding queries within a session
  - Avoid re-embedding identical query strings
- [ ] [FEATURE] Cache stats endpoint — `GET /api/cache/stats` (PRD Section 8b)
  - Total entries, hit rate, estimated cost saved

### Prompt Registry
- [ ] [FEATURE] Prompt registry — `src/prompts/registry.py` (PRD Section 4.4, 5)
  - CRUD operations for Jinja2 prompt templates
  - Versioning (auto-increment on update)
  - `is_active` flag for A/B testing
  - `model_hint` field for suggested model per prompt
- [ ] [FEATURE] Initial Jinja2 prompt templates — `src/prompts/templates/` (PRD Section 9, implied)
  - System prompt template for RAG chat
  - Summarization prompt template
  - Evaluation judge prompt templates
- [ ] [FEATURE] Prompt API endpoints (PRD Section 8b)
  - `POST /api/prompts` — create prompt
  - `GET /api/prompts` — list prompts
  - `PUT /api/prompts/:id` — update prompt (increments version)

### Evaluation Harness
- [ ] [FEATURE] Relevance scorer — `src/evaluation/relevance.py` (PRD Section 5.9)
  - LLM-as-judge: are retrieved chunks relevant to the query?
- [ ] [FEATURE] Faithfulness scorer — `src/evaluation/faithfulness.py` (PRD Section 5.9)
  - Claim extraction + verification against source chunks
- [ ] [FEATURE] Correctness scorer — `src/evaluation/correctness.py` (PRD Section 5.9)
  - LLM-as-judge: does the response answer the question?
- [ ] [FEATURE] Evaluation harness — `src/evaluation/harness.py` (PRD Section 5.9)
  - Run all metrics after each RAG response
  - Store scores in `evaluations` table
  - Flag responses below threshold (`EVAL_MIN_THRESHOLD`, default 0.7)
- [ ] [FEATURE] Metrics API endpoints (PRD Section 8b)
  - `GET /api/metrics/cost` — total cost, by model, by day
  - `GET /api/metrics/quality` — avg relevance, avg faithfulness, by model

### MCP Server
- [ ] [FEATURE] MCP server implementation — `src/mcp/server.py` (PRD Section 5.8)
  - MCP server using `mcp` Python SDK
  - Tools: `search_documents`, `ingest_document`, `query_graph`, `get_conversation_history`
  - Resources: `document://`, `conversation://` URI schemes
  - Tool discovery, parameter validation, execution
  - Compatible with MCP-aware clients (Claude Desktop, Cursor)
  - Port: `MCP_SERVER_PORT` (default 3001), Transport: `MCP_TRANSPORT` (default `stdio`)
  - [ ] [TEST] Integration test for MCP tool discovery and execution
- [ ] [VERIFY] Phase 4 test coverage ≥ 80% — `pytest --cov`

---

## Phase 5: Deploy + Polish

### Background Jobs
- [ ] [FEATURE] Cache cleanup job (PRD Section 7)
  - Delete expired `semantic_cache` entries — every 1h
- [ ] [FEATURE] Conversation summary job (PRD Section 7)
  - Summarize long conversations exceeding memory window — every 6h
- [ ] [FEATURE] Evaluation aggregation job (PRD Section 7)
  - Pre-compute aggregate quality metrics — every 24h
- [ ] [FEATURE] Cost budget reset job (PRD Section 7)
  - Reset daily cost budgets per user — daily at midnight UTC
- [ ] [FEATURE] Knowledge graph sync job (PRD Section 7)
  - Async background worker triggered on document ingestion
  - Runs entity extraction → upsert Neo4j (distinct from inline extraction in Phase 3)
  - Wire as FastAPI background task from ingestion pipeline

### Deployment
- [ ] [FEATURE] Production Docker Compose (PRD Section 10)
  - FastAPI app + PostgreSQL 16/pgvector + Neo4j 5 Community + Redis 7
  - Traefik labels for `ai.kingsleyonoh.com` with auto TLS
- [ ] [FEATURE] Deploy to Hetzner VPS (PRD Section 10)
  - SSH deploy: pull → build → migrate → restart
  - Traefik health-based routing

### Monitoring & Observability
- [ ] [FEATURE] BetterStack uptime monitoring (PRD Section 10b)
  - Poll `/api/health` endpoint
- [ ] [FEATURE] Alerting rules implementation (PRD Section 10b)
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
