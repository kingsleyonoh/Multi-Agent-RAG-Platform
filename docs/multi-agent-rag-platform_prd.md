# Multi-Agent RAG Platform — PRD

---

## 1. What Is This?

A production-grade AI backend platform that demonstrates the full spectrum of modern AI engineering: document ingestion with vector embeddings (RAG), multi-model LLM orchestration via OpenRouter (GPT-4o, Claude 3.5, Gemini 2.0, DeepSeek, and more), autonomous AI agents with tool calling, guardrails for safety and quality, conversation memory, knowledge graph integration, semantic caching, and an MCP server for agent tooling. The platform exposes a chat API that handles user queries by retrieving relevant context from a knowledge base, routing to the best model for the task, executing tools when needed, and streaming responses back — all while tracking costs, enforcing safety policies, and evaluating response quality.

This is not a chatbot wrapper. It's the **infrastructure layer** that powers intelligent applications — the kind of system a $400K/year AI engineering role expects you to know how to build. One project that gives you credible portfolio evidence for every AI job on Upwork.

---

## 2. Architecture Principles

1. **RAG-first, not prompt-stuffing** — Context comes from retrieval, not from cramming everything into the prompt. The knowledge base is the source of truth. The LLM interprets, it doesn't memorize.
2. **Model-agnostic routing via OpenRouter** — No vendor lock-in. One API, 200+ models. The system routes to GPT-4o, Claude 3.5 Sonnet, Gemini 2.0 Flash, or DeepSeek based on task complexity, cost constraints, and latency requirements. Switching models is a config change.
3. **Guardrails are not optional** — Every input is validated for prompt injection, PII, and policy violations. Every output is checked for hallucination markers and safety. This runs in the pipeline, not as an afterthought.
4. **Agents are controlled, not autonomous** — Tool calling follows a whitelist. Agents can't call tools not registered for their task. Every tool call is logged with inputs, outputs, and latency.
5. **Cost is a first-class metric** — Every LLM call tracks token usage and dollar cost. The system can enforce per-user, per-session, or per-hour cost budgets. Semantic caching reduces redundant calls.
6. **Local-first development** — PostgreSQL (+ pgvector), Neo4j, and Redis run via Docker Compose. LLM calls use real APIs with spend caps for development.

---

## 3. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.12 | AI/ML ecosystem, LangChain/LangGraph native |
| Framework | FastAPI 0.115+ | Async-native, streaming support, OpenAPI auto-docs |
| LLM Orchestration | LangGraph 0.2+ | Stateful agent graphs, human-in-the-loop, persistence |
| LLM Gateway | OpenRouter | Single API for 200+ models (OpenAI, Anthropic, Gemini, DeepSeek, etc.) |
| Vector Database | PostgreSQL 16 + pgvector | Vector search without a separate service |
| Knowledge Graph | Neo4j 5.x (Community) | Entity relationships, graph traversal for context enrichment |
| Cache | Redis 7 (semantic cache + session store) | Fast similarity lookup for cached responses |
| Embeddings | OpenRouter (text-embedding-3-small) | Best cost/quality ratio for embedding, billed through OpenRouter |
| Evaluation | Ragas + custom metrics | RAG quality scoring |
| Testing | pytest + httpx (async) + pytest-asyncio | Async test support |
| Validation | Pydantic v2 | Request/response schemas |
| Containerization | Docker + Docker Compose | Local dev: PG, Neo4j, Redis |
| Hosting | Docker on Hetzner VPS | Self-hosted, cost-effective |

---

## 4. Database Schema

### 4.1 PostgreSQL — Documents & Vectors

```
documents
├── id              UUID PK
├── title           TEXT NOT NULL
├── source          TEXT NOT NULL (e.g., 'upload', 'url', 'api')
├── content         TEXT NOT NULL
├── content_hash    TEXT NOT NULL UNIQUE (SHA-256, for dedup)
├── metadata        JSONB DEFAULT '{}'
├── chunk_count     INTEGER DEFAULT 0
├── status          TEXT DEFAULT 'pending' (enum: 'pending', 'chunked', 'embedded', 'failed')
├── created_at      TIMESTAMP DEFAULT NOW()
└── updated_at      TIMESTAMP DEFAULT NOW()

INDEX ON content_hash
INDEX ON status
```

### 4.2 PostgreSQL — Chunks with Vectors

```
chunks
├── id              UUID PK
├── document_id     UUID FK → documents.id ON DELETE CASCADE
├── chunk_index     INTEGER NOT NULL
├── content         TEXT NOT NULL
├── token_count     INTEGER NOT NULL
├── embedding       vector(1536) NOT NULL (pgvector)
├── metadata        JSONB DEFAULT '{}' (page_number, section, headers)
├── created_at      TIMESTAMP DEFAULT NOW()

INDEX ON document_id
INDEX USING ivfflat ON embedding vector_cosine_ops WITH (lists = 100)
```

### 4.3 PostgreSQL — Conversations & Messages

```
conversations
├── id              UUID PK
├── user_id         TEXT NOT NULL
├── title           TEXT NULL
├── model_preference TEXT NULL (user's preferred model)
├── total_tokens    INTEGER DEFAULT 0
├── total_cost_usd  DECIMAL(10,6) DEFAULT 0
├── created_at      TIMESTAMP DEFAULT NOW()
└── updated_at      TIMESTAMP DEFAULT NOW()

INDEX ON user_id

messages
├── id              UUID PK
├── conversation_id UUID FK → conversations.id ON DELETE CASCADE
├── role            TEXT NOT NULL (enum: 'user', 'assistant', 'system', 'tool')
├── content         TEXT NOT NULL
├── model_used      TEXT NULL (e.g., 'gpt-4o', 'claude-3-5-sonnet', 'gemini-2.0-flash')
├── tokens_in       INTEGER NULL
├── tokens_out      INTEGER NULL
├── cost_usd        DECIMAL(10,6) NULL
├── latency_ms      INTEGER NULL
├── tool_calls      JSONB NULL (array of {name, args, result})
├── sources         JSONB NULL (array of {chunk_id, document_title, relevance_score})
├── guardrail_flags JSONB DEFAULT '[]'
├── created_at      TIMESTAMP DEFAULT NOW()

INDEX ON conversation_id, created_at
```

### 4.4 PostgreSQL — Prompt Registry

```
prompts
├── id              UUID PK
├── name            TEXT NOT NULL UNIQUE
├── version         INTEGER DEFAULT 1
├── template        TEXT NOT NULL (Jinja2 template)
├── model_hint      TEXT NULL (suggested model for this prompt)
├── is_active       BOOLEAN DEFAULT TRUE
├── metadata        JSONB DEFAULT '{}'
├── created_at      TIMESTAMP DEFAULT NOW()
└── updated_at      TIMESTAMP DEFAULT NOW()

INDEX ON name, is_active
```

### 4.5 PostgreSQL — Evaluation Results

```
evaluations
├── id              UUID PK
├── message_id      UUID FK → messages.id
├── metric          TEXT NOT NULL (e.g., 'relevance', 'faithfulness', 'hallucination')
├── score           DECIMAL(5,4) NOT NULL (0.0 – 1.0)
├── details         JSONB DEFAULT '{}'
├── created_at      TIMESTAMP DEFAULT NOW()

INDEX ON message_id
INDEX ON metric, score
```

### 4.6 PostgreSQL — Semantic Cache

```
semantic_cache
├── id              UUID PK
├── query_embedding vector(1536) NOT NULL
├── query_text      TEXT NOT NULL
├── response        TEXT NOT NULL
├── model_used      TEXT NOT NULL
├── hit_count       INTEGER DEFAULT 0
├── created_at      TIMESTAMP DEFAULT NOW()
├── expires_at      TIMESTAMP NOT NULL

INDEX USING ivfflat ON query_embedding vector_cosine_ops WITH (lists = 50)
INDEX ON expires_at
```

### 4.7 Neo4j — Knowledge Graph

```cypher
// Entity nodes
(:Entity {id, name, type, properties, source_document_id})

// Relationship edges
(:Entity)-[:RELATED_TO {relationship, confidence, source_chunk_id}]->(:Entity)

// Document lineage
(:Document {id, title})-[:CONTAINS]->(:Chunk {id, index})
(:Chunk)-[:MENTIONS]->(:Entity)
```

---

## 5. Module Specifications

### 5.1 Document Ingestion Pipeline

**Purpose:** Accept documents (text, PDF, URL), chunk them, generate embeddings, and store in pgvector.

**Core Logic:**
1. Accept document via API upload (file or text) or URL scraping.
2. Extract text content (plain text passthrough, PDF via `pdfplumber`, URL via `httpx` + `BeautifulSoup`).
3. Deduplicate by `content_hash` — skip if identical document exists.
4. Chunk using recursive character splitting: 512 tokens per chunk, 50-token overlap.
5. Generate embeddings for each chunk via OpenRouter → `openai/text-embedding-3-small`.
6. Batch insert chunks + embeddings into `chunks` table.
7. Extract entities (people, organizations, dates, concepts) and upsert into Neo4j knowledge graph.
8. Update document `status` to `'embedded'`.

**Inputs:** File upload (PDF, TXT, MD) or `{ url }` or `{ text, title }`.

**Outputs:** `documents` record + `chunks` with embeddings in pgvector + entities in Neo4j.

**Configuration:** `CHUNK_SIZE` (default 512), `CHUNK_OVERLAP` (default 50), `EMBEDDING_MODEL` (default `text-embedding-3-small`).

**Edge Cases:**
- PDF with scanned images → log warning, skip (OCR not in scope — see Document Extraction Pipeline project #10).
- Empty document → reject with `EMPTY_DOCUMENT` error.
- Duplicate content hash → return existing document ID, skip re-processing.
- Embedding API failure → mark document `'failed'`, store error, allow retry.

### 5.2 Retrieval Engine

**Purpose:** Find the most relevant chunks for a user query using hybrid search (vector + keyword + knowledge graph).

**Core Logic:**
1. Embed the user query using the same embedding model.
2. **Vector search:** Query pgvector for top-K similar chunks (cosine similarity, K=10).
3. **Keyword boost:** If query contains entity names found in Neo4j, boost chunks from documents mentioning those entities.
4. **Knowledge graph expansion:** Query Neo4j for entities related to query entities — pull in chunks from related documents.
5. **Re-rank:** Score results by `0.7 * vector_similarity + 0.2 * keyword_overlap + 0.1 * graph_relevance`.
6. Return top-5 chunks with relevance scores and source metadata.

**Inputs:** `{ query, top_k?, filters?: { document_ids?, metadata? } }`.

**Outputs:** `[ { chunk_id, content, relevance_score, document_title, document_id } ]`.

**Configuration:** `RETRIEVAL_TOP_K` (default 10), `RERANK_TOP_N` (default 5), `SIMILARITY_THRESHOLD` (default 0.7).

### 5.3 Multi-Model Router

**Purpose:** Route LLM requests to the optimal model via OpenRouter based on task, cost, and latency.

**Core Logic:**
1. Accept a request with `{ messages, task_type, max_cost?, preferred_model? }`.
2. If `preferred_model` is set → pass it directly to OpenRouter (e.g., `anthropic/claude-3.5-sonnet`).
3. Otherwise, apply routing rules:
   - **Simple Q&A / summarization** → `google/gemini-2.0-flash-exp` (cheapest, fastest)
   - **Complex reasoning / analysis** → `anthropic/claude-3.5-sonnet` or `openai/gpt-4o` (best quality)
   - **Code generation** → `anthropic/claude-3.5-sonnet` (strongest at code)
   - **Structured extraction** → `openai/gpt-4o` with JSON mode
   - **Cost-optimized** → `deepseek/deepseek-chat` (excellent quality/price)
4. If `max_cost` would be exceeded → downgrade to a cheaper model.
5. Call OpenRouter's `/api/v1/chat/completions` with streaming enabled.
6. Track tokens in/out, latency, and cost per call (OpenRouter returns cost in response headers).
7. If model is unavailable (HTTP 5xx or timeout) → fallback to next model in priority list via OpenRouter.

**Inputs:** `{ messages, task_type, context_chunks, max_cost?, preferred_model? }`.

**Outputs:** Streamed response tokens + `{ model_used, tokens_in, tokens_out, cost_usd, latency_ms }`.

**Configuration:** `OPENROUTER_API_KEY`, model routing table in config, fallback chain per task type.

### 5.4 Agent Executor

**Purpose:** Execute AI agents with tool calling for structured actions.

**Core Logic:**
1. Accept a user message that requires tool use (detected by the LLM's tool_call response).
2. Validate the tool call against the registered tool whitelist.
3. Execute the tool function with the provided arguments.
4. Return the tool result to the LLM for interpretation.
5. Support multi-step tool chains (LLM calls tool → gets result → calls another tool → synthesizes).
6. Cap at 5 tool calls per turn to prevent infinite loops.
7. Log every tool invocation: name, args, result, latency.

**Available Tools (v1):**
- `search_knowledge_base` — vector search over ingested documents
- `query_graph` — Cypher query against Neo4j knowledge graph
- `calculate` — safe math expression evaluator
- `get_current_time` — returns UTC timestamp
- `summarize_document` — summarize a specific document by ID

**Inputs:** LLM tool_call response: `{ name, arguments }`.

**Outputs:** Tool execution result as string, fed back into LLM context.

**Configuration:** `MAX_TOOL_CALLS_PER_TURN` (default 5), tool whitelist in config.

### 5.5 Guardrails Pipeline

**Purpose:** Validate inputs and outputs for safety, quality, and policy compliance.

**Core Logic:**

**Input guardrails (pre-LLM):**
1. **Prompt injection detection:** Check for common injection patterns (\"ignore previous instructions\", role-play attacks, delimiter injection). Score 0.0–1.0. Block if > 0.8.
2. **PII detection:** Regex-based scan for SSN, credit card, phone numbers, emails. Flag (don't block) — log which PII types detected.
3. **Topic policy:** Block requests that match denied topics (configurable blocklist).
4. **Token budget check:** Reject if estimated input + output would exceed session budget.

**Output guardrails (post-LLM):**
1. **Hallucination check:** Compare LLM response against source chunks. Flag claims not grounded in retrieved context.
2. **Content safety:** Check for harmful content categories (hate, violence, sexual content). Use keyword patterns + LLM-as-judge.
3. **Source attribution:** Verify that cited sources exist in the retrieval results.

**Inputs:** `{ text, direction: 'input' | 'output', context_chunks? }`.

**Outputs:** `{ passed: boolean, flags: [{ type, severity, detail }] }`.

**Configuration:** `GUARDRAIL_INJECTION_THRESHOLD` (default 0.8), `GUARDRAIL_PII_MODE` (default `'flag'` — options: `'flag'`, `'block'`, `'redact'`).

### 5.6 Conversation Memory

**Purpose:** Manage short-term and long-term memory for multi-turn conversations.

**Core Logic:**
1. **Short-term:** Keep last N messages in the conversation context window (configurable, default 20).
2. **Long-term:** When conversation exceeds context limit, summarize older messages using a cheap LLM (Gemini Flash) and store the summary.
3. **Entity memory:** Extract named entities from conversations and store in Neo4j. On new turns, retrieve entity context for personalization.
4. **Session continuity:** Conversations persist in PostgreSQL. Users can resume any previous conversation.

**Inputs:** `{ conversation_id, new_message }`.

**Outputs:** `{ context_messages, entity_context, memory_summary? }`.

**Configuration:** `MEMORY_WINDOW_SIZE` (default 20), `MEMORY_SUMMARY_MODEL` (default `gemini-2.0-flash`).

### 5.7 Semantic Cache

**Purpose:** Cache responses to semantically similar queries to reduce LLM costs.

**Core Logic:**
1. On new query, embed it and search `semantic_cache` for vectors with cosine similarity > 0.95.
2. If cache hit → return cached response immediately (skip LLM call entirely). Increment `hit_count`.
3. If cache miss → process normally, then store query embedding + response in cache with TTL.
4. Cache expiry: default 24 hours. Invalidate when knowledge base is updated (new documents ingested).

**Inputs:** `{ query_text, query_embedding }`.

**Outputs:** `{ hit: boolean, cached_response?: string }`.

**Configuration:** `CACHE_SIMILARITY_THRESHOLD` (default 0.95), `CACHE_TTL_HOURS` (default 24).

### 5.8 MCP Server

**Purpose:** Expose platform tools via the Model Context Protocol for external AI agent consumption.

**Core Logic:**
1. Implement an MCP server using the `mcp` Python SDK.
2. Expose tools: `search_documents`, `ingest_document`, `query_graph`, `get_conversation_history`.
3. Expose resources: `document://`, `conversation://` URI schemes.
4. Handle tool discovery, parameter validation, and execution.
5. Return structured results compatible with MCP-aware clients (Claude Desktop, Cursor, etc.).

**Inputs:** MCP tool call requests from external agents.

**Outputs:** MCP-formatted tool results.

**Configuration:** `MCP_SERVER_PORT` (default 3001), `MCP_TRANSPORT` (default `stdio`).

### 5.9 Evaluation Harness

**Purpose:** Automated quality scoring for RAG responses.

**Core Logic:**
1. After each RAG response, run evaluation metrics:
   - **Relevance:** Are the retrieved chunks relevant to the query? (LLM-as-judge)
   - **Faithfulness:** Is the response grounded in the retrieved context? (claim extraction + verification)
   - **Answer correctness:** Does the response actually answer the question? (LLM-as-judge)
2. Store scores in `evaluations` table.
3. Expose aggregate metrics via API (avg scores per model, per time period).
4. Flag responses with scores below threshold for review.

**Inputs:** `{ query, response, retrieved_chunks }`.

**Outputs:** `{ relevance: 0.0-1.0, faithfulness: 0.0-1.0, correctness: 0.0-1.0 }`.

**Configuration:** `EVAL_JUDGE_MODEL` (default `gpt-4o-mini`), `EVAL_MIN_THRESHOLD` (default 0.7).

---

## 5b. User Journeys & Screens

N/A — Backend API only. Chat UIs, admin dashboards, and agent clients are consumer concerns. The platform exposes REST + SSE + WebSocket + MCP interfaces.

---

## 6. Connectors / Integrations

### 6.1 OpenRouter API

**Purpose:** Single gateway for all LLM completions and embeddings. Provides access to 200+ models (OpenAI, Anthropic, Google, DeepSeek, etc.) through one API key and one billing dashboard.

**API Used:** REST — OpenAI-compatible `/api/v1/chat/completions` and `/api/v1/embeddings` endpoints.

**Authentication:** API key via `Authorization: Bearer sk-or-v1-...` header. App identification via `X-Title` and `HTTP-Referer` headers.

**Data Flow:**
- **Outbound:** Chat messages + system prompts + tool definitions → OpenRouter → selected model.
- **Inbound:** Streamed completion tokens, usage stats (tokens in/out), cost in response headers.
- **Embeddings:** Text chunks → OpenRouter → `openai/text-embedding-3-small` → 1536-dim vectors.

**Error Handling:**
- HTTP 429 (rate limit) → exponential backoff with jitter, max 3 retries.
- HTTP 5xx (provider error) → fallback to next model in routing chain.
- HTTP 402 (insufficient credits) → log critical error, return `COST_LIMIT_EXCEEDED` to client.
- Timeout (>30s for non-streaming) → cancel, try cheaper/faster model.

### 6.2 Neo4j

**Purpose:** Knowledge graph storage for entity relationships extracted from documents. Enables graph-based context enrichment during retrieval.

**API Used:** Bolt protocol via `neo4j` Python driver. Cypher queries for read/write.

**Authentication:** Username/password (`NEO4J_USER`, `NEO4J_PASSWORD`). Community Edition, no TLS in dev.

**Data Flow:**
- **Write:** Entity extraction during document ingestion → `CREATE`/`MERGE` nodes and relationships.
- **Read:** Retrieval engine queries related entities → `MATCH` traversals for context expansion.

**Error Handling:**
- Connection failure → health check reports `neo4j: unhealthy`, retrieval falls back to vector-only search (graceful degradation).
- Query timeout (>5s) → cancel and return partial results from vector search only.

**Test Data Strategy:** All LLM API calls are mocked in tests using recorded HTTP response fixtures in `tests/fixtures/llm/`. Adapter tests use `respx` for async HTTP mocking. A `MOCK_LLM=true` env var switches between fixtures and live APIs. Integration tests that hit real APIs are marked with `@pytest.mark.integration` and excluded from CI by default.

---

## 7. Scheduler / Background Jobs

| Job | Frequency | What It Does |
|-----|-----------|-------------|
| Cache Cleanup | Every 1h | Deletes expired entries from `semantic_cache` |
| Conversation Summary | Every 6h | Summarizes long conversations that exceed memory window |
| Evaluation Aggregation | Every 24h | Pre-computes aggregate quality metrics |
| Knowledge Graph Sync | On document ingestion | Extracts entities and relationships after embedding |
| Cost Budget Reset | Daily at midnight UTC | Resets daily cost budgets per user (if configured) |

---

## 7b. Notifications Strategy

N/A — No user-facing notifications in v1. Cost limit warnings are returned inline in API responses. Quality alerts are logged server-side.

---

## 8. Admin / UI

N/A — Backend API only. Management via API endpoints.

---

## 8b. API Endpoints

| Method | Path | Auth | Response | Rate Limit |
|--------|------|------|----------|------------|
| POST | /api/chat | API Key | SSE stream of `{ token, sources?, tool_call?, done }` | 60/min |
| POST | /api/chat/sync | API Key | `{ response, sources, model_used, cost }` | 30/min |
| POST | /api/documents | API Key | `{ document_id, status, chunk_count }` | 20/min |
| POST | /api/documents/url | API Key | `{ document_id, status }` | 10/min |
| GET | /api/documents | API Key | `{ documents: [...], total }` | 100/min |
| GET | /api/documents/:id | API Key | `{ document, chunks_count }` | 100/min |
| DELETE | /api/documents/:id | API Key | `{ deleted: true }` | 20/min |
| POST | /api/search | API Key | `{ results: [...], query_embedding_time_ms }` | 200/min |
| GET | /api/conversations | API Key | `{ conversations: [...], total }` | 100/min |
| GET | /api/conversations/:id | API Key | `{ conversation, messages }` | 100/min |
| DELETE | /api/conversations/:id | API Key | `{ deleted: true }` | 20/min |
| GET | /api/graph/entities | API Key | `{ entities: [...] }` | 50/min |
| GET | /api/graph/related/:entityId | API Key | `{ entity, relationships: [...] }` | 50/min |
| POST | /api/prompts | API Key | `{ prompt }` | 20/min |
| GET | /api/prompts | API Key | `{ prompts: [...] }` | 100/min |
| PUT | /api/prompts/:id | API Key | `{ prompt }` | 20/min |
| GET | /api/metrics/cost | API Key | `{ total_cost, by_model, by_day }` | 30/min |
| GET | /api/metrics/quality | API Key | `{ avg_relevance, avg_faithfulness, by_model }` | 30/min |
| GET | /api/cache/stats | API Key | `{ total_entries, hit_rate, cost_saved }` | 30/min |
| GET | /api/health | None | `{ status, pg, neo4j, redis, models }` | — |

### Authentication
- **Strategy:** API Key in `X-API-Key` header.
- **Token Refresh:** N/A — API keys are static, no refresh mechanism.
- **User identification:** `X-User-Id` header for per-user cost tracking and conversation ownership.
- **Public endpoints:** `GET /api/health` only.

### Pagination & Filtering
- **Pattern:** Cursor-based on list endpoints (`cursor` + `limit` query params).
- **Default Page Size:** 25
- **Max Page Size:** 100
- **Filters:** `status`, `source`, `created_after` on documents; `user_id`, `created_after` on conversations.

### Error Response Format

```json
{
  "error": {
    "code": "GUARDRAIL_BLOCKED",
    "message": "Input blocked: prompt injection detected (score: 0.92)",
    "details": [
      { "type": "prompt_injection", "severity": "high", "score": 0.92 }
    ]
  }
}
```

---

## 9. Project Structure

```
multi-agent-rag-platform/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── ingestion/
│   │   ├── pipeline.py              # Document → chunks → embeddings
│   │   ├── chunker.py               # Text splitting strategies
│   │   ├── embedder.py              # OpenAI embedding wrapper
│   │   └── extractors/
│   │       ├── pdf.py               # PDF text extraction
│   │       ├── url.py               # URL scraping
│   │       └── text.py              # Plain text passthrough
│   ├── retrieval/
│   │   ├── engine.py                # Hybrid search orchestrator
│   │   ├── vector_search.py         # pgvector similarity queries
│   │   ├── graph_search.py          # Neo4j entity expansion
│   │   └── reranker.py              # Result scoring and reranking
│   ├── llm/
│   │   ├── router.py                # Multi-model routing logic
│   │   ├── openrouter.py            # OpenRouter API client (all models)
│   │   ├── streaming.py             # SSE response streaming
│   │   └── cost_tracker.py          # Token counting + pricing
│   ├── agents/
│   │   ├── executor.py              # LangGraph agent executor
│   │   ├── tools/
│   │   │   ├── search_kb.py         # Knowledge base search tool
│   │   │   ├── query_graph.py       # Neo4j query tool
│   │   │   ├── calculate.py         # Math expression evaluator
│   │   │   └── summarize.py         # Document summarization tool
│   │   └── registry.py              # Tool whitelist registry
│   ├── guardrails/
│   │   ├── pipeline.py              # Input + output guardrail chain
│   │   ├── injection.py             # Prompt injection detection
│   │   ├── pii.py                   # PII detection + redaction
│   │   ├── content_safety.py        # Output safety checks
│   │   └── hallucination.py         # Hallucination detection
│   ├── memory/
│   │   ├── manager.py               # Conversation memory orchestrator
│   │   ├── short_term.py            # Context window management
│   │   ├── long_term.py             # Summary-based long-term memory
│   │   └── entity.py                # Entity extraction + Neo4j storage
│   ├── cache/
│   │   └── semantic.py              # Semantic similarity cache
│   ├── evaluation/
│   │   ├── harness.py               # Evaluation orchestrator
│   │   ├── relevance.py             # Retrieval relevance scoring
│   │   ├── faithfulness.py          # Groundedness checking
│   │   └── correctness.py           # Answer correctness scoring
│   ├── prompts/
│   │   ├── registry.py              # Prompt CRUD + versioning
│   │   └── templates/               # Jinja2 prompt templates
│   ├── mcp/
│   │   └── server.py                # MCP server implementation
│   ├── api/
│   │   ├── chat.py
│   │   ├── documents.py
│   │   ├── conversations.py
│   │   ├── graph.py
│   │   ├── prompts.py
│   │   ├── metrics.py
│   │   ├── health.py
│   │   └── middleware/
│   │       ├── auth.py
│   │       ├── rate_limit.py
│   │       └── errors.py
│   ├── db/
│   │   ├── postgres.py              # async SQLAlchemy + pgvector
│   │   ├── neo4j.py                 # Neo4j driver wrapper
│   │   ├── redis.py                 # Redis client
│   │   └── migrations/
│   │       └── alembic/
│   └── lib/
│       ├── logger.py
│       └── utils.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── llm/
│           └── openrouter_responses/   # Mocked OpenRouter API responses
├── docker-compose.yml                # PostgreSQL + pgvector, Neo4j, Redis
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── .env.example
└── docs/
    └── multi-agent-rag-platform_prd.md
```

### Dependency Hierarchy
```
lib/ → nothing
db/ → lib/
cache/ → db/ (Redis), lib/
ingestion/ → db/ (PG, Neo4j), lib/
retrieval/ → db/ (PG, Neo4j), lib/
llm/ → lib/ (single OpenRouter client)
guardrails/ → lib/, llm/ (for LLM-as-judge)
memory/ → db/ (PG, Neo4j), llm/ (for summarization), lib/
agents/ → retrieval/, llm/, db/, lib/
evaluation/ → db/, llm/ (for LLM-as-judge), lib/
prompts/ → db/, lib/
mcp/ → retrieval/, ingestion/, db/, lib/
api/ → all modules above
main.py → api/, db/, mcp/, config
```

---

## 10. Deployment

- **Hosting:** Docker on shared Hetzner VPS behind Traefik reverse proxy.
- **Domain:** `ai.kingsleyonoh.com` (Traefik auto-generates TLS via Let's Encrypt).
- **Containers:** FastAPI app, PostgreSQL 16 + pgvector, Neo4j 5 Community, Redis 7.

### Deploy Process

1. SSH into VPS.
2. `git pull origin main` — pull latest code.
3. `docker compose build app` — rebuild app image only.
4. `docker compose run --rm app alembic upgrade head` — run Alembic migrations against production PostgreSQL.
5. `docker compose up -d` — restart with zero-downtime (Traefik handles health-based routing).

### CI/CD

No automated CI/CD pipeline in v1. Deployment is manual via SSH. Future: GitHub Actions → build Docker image → push to registry → SSH deploy.

### Database Migrations

- **Tool:** Alembic (via `alembic upgrade head`).
- **Strategy:** Forward-only migrations. No down-migrations in production.
- **Pre-deploy check:** Review migration SQL with `alembic upgrade --sql head` before applying.
- **Neo4j:** Schema-less — no formal migrations. Constraints created on app startup via `db/neo4j.py` init function.

---

## 10b. Performance & Observability

### Performance Targets

| Metric | Target |
|--------|--------|
| Chat response first token (p95) | < 1.5 seconds |
| Retrieval latency (p95) | < 200ms |
| Document ingestion (per page) | < 2 seconds |
| Semantic cache lookup (p95) | < 50ms |
| Embedding generation (per chunk) | < 300ms |
| Cache hit rate (steady state) | > 20% |

### Caching Strategy
- **Semantic cache:** Redis-backed vector similarity cache for LLM responses. TTL 24h. Invalidated on knowledge base updates.
- **Embedding cache:** In-memory LRU for repeat queries within a session.

### Observability Stack

| Concern | Tool |
|---------|------|
| Logging | structlog (structured JSON to stdout) |
| Error Tracking | Structured error logs with LLM provider errors, guardrail flags |
| Uptime | `/api/health` polled by BetterStack |
| Cost Tracking | Built-in per-request cost logging to `messages` table |

### Health Checks
- `/api/health` — app status, PostgreSQL connectivity, pgvector extension loaded, Neo4j connectivity, Redis connectivity, LLM provider reachability (lightweight ping)

### Alerting Rules

| Condition | Severity | Action |
|-----------|----------|--------|
| Health returns non-200 for 3 checks | Critical | BetterStack notification |
| Daily LLM spend > $10 | Warning | Logged at `warn` level |
| Guardrail block rate > 30% in 1h | Warning | Logged at `warn` level |
| Avg RAG relevance score < 0.6 over 24h | Warning | Logged at `warn` level |

### Analytics & Tracking
Built-in analytics: cost per model, cost per user, cache hit rate, retrieval quality scores, guardrail flag distribution. All available via `/api/metrics/*` endpoints.

---

## 11. Onboarding / Setup Process

1. Clone repository.
2. Copy `.env.example` → `.env`, add OpenRouter API key (`OPENROUTER_API_KEY`).
3. `docker compose up -d` (PostgreSQL + pgvector, Neo4j, Redis).
4. `pip install -e ".[dev]"` or `uv sync`.
5. `alembic upgrade head` (run migrations).
6. `uvicorn src.main:app --reload`.
7. Ingest a test document: `curl -X POST http://localhost:8000/api/documents -H "X-API-Key: dev-key" -F "file=@tests/fixtures/sample.pdf"`.
8. Ask a question: `curl -X POST http://localhost:8000/api/chat -H "X-API-Key: dev-key" -d '{"message": "What is this document about?", "conversation_id": null}'`.

---

## 12. What NOT to Build

| Don't Build | Why |
|------------|-----|
| Chat UI / frontend | Backend API only. Focus on infrastructure. |
| Fine-tuning pipeline | v1 uses pre-trained models via API. Fine-tuning is v2. |
| Image/audio processing | Text-only RAG in v1 |
| User authentication (OAuth, JWT) | API key auth. Full auth is a consumer concern. |
| Multi-tenancy | Single-tenant for portfolio demo. Multi-tenant is enterprise concern. |
| Custom embedding model | Use OpenAI embeddings. Custom training is out of scope. |
| Automated prompt optimization | Manual prompt management via registry. Auto-optimization is v2. |
| Vector database migration (Pinecone, Weaviate) | pgvector is sufficient for portfolio scale |

---

## 12b. Migration Plan

N/A — Greenfield project.

---

## 13. Build Phases

### Phase 1: Core RAG Pipeline (Day 1-2)
- [ ] FastAPI project setup + PostgreSQL (pgvector) + Redis + Neo4j Docker Compose
- [ ] Database schema + Alembic migrations
- [ ] Config, logging, auth middleware, error handling
- [ ] Document ingestion: upload → chunk → embed → store
- [ ] Vector search: query embedding → pgvector similarity → ranked results
- [ ] Basic chat endpoint: query → retrieve → LLM → response
- [ ] Health endpoint

### Phase 2: Multi-Model + Agents (Day 2-3)
- [ ] Multi-model router: OpenAI / Anthropic / Gemini with fallback
- [ ] SSE streaming for chat responses
- [ ] Cost tracking per request (tokens, cost, model)
- [ ] Agent executor with tool calling (search_kb, calculate, get_time)
- [ ] Tool whitelist registry
- [ ] Conversation persistence + message history

### Phase 3: Guardrails + Memory (Day 3-4)
- [ ] Input guardrails: prompt injection detection, PII detection, topic policy
- [ ] Output guardrails: hallucination check, content safety
- [ ] Conversation memory: short-term window + long-term summarization
- [ ] Entity extraction + Neo4j knowledge graph
- [ ] Knowledge graph search integration in retrieval

### Phase 4: Cache + Evaluation + MCP (Day 4-5)
- [ ] Semantic cache: embed query → check cache → serve or compute
- [ ] Prompt registry: CRUD + versioning
- [ ] Evaluation harness: relevance, faithfulness, correctness scoring
- [ ] Metrics API: cost, quality, cache stats
- [ ] MCP server: expose tools + resources for external agents

### Phase 5: Deploy + Polish (Day 5-6)
- [ ] Dockerfile + production Docker Compose
- [ ] Deploy to Hetzner VPS
- [ ] BetterStack monitoring
- [ ] Integration tests with mocked LLM responses
- [ ] Load test with concurrent chat sessions
- [ ] Seed knowledge base with sample documents

---

## 14. Environment Variables

```env
HOST=0.0.0.0
PORT=8000
ENV=development
API_KEYS=dev-key-1
LOG_LEVEL=info

# Database
DATABASE_URL=postgresql+asyncpg://postgres:devpass@localhost:5432/ragplatform
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devpass
REDIS_URL=redis://localhost:6379

# LLM Provider (OpenRouter — single key for all models)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_APP_NAME=multi-agent-rag-platform

# LLM Configuration
DEFAULT_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=openai/text-embedding-3-small
MEMORY_SUMMARY_MODEL=google/gemini-2.0-flash-exp
EVAL_JUDGE_MODEL=openai/gpt-4o-mini

# RAG Configuration
CHUNK_SIZE=512
CHUNK_OVERLAP=50
RETRIEVAL_TOP_K=10
RERANK_TOP_N=5
SIMILARITY_THRESHOLD=0.7

# Guardrails
GUARDRAIL_INJECTION_THRESHOLD=0.8
GUARDRAIL_PII_MODE=flag

# Cache
CACHE_SIMILARITY_THRESHOLD=0.95
CACHE_TTL_HOURS=24

# Agents
MAX_TOOL_CALLS_PER_TURN=5
MOCK_LLM=false

# Cost Management
DAILY_COST_LIMIT_USD=10.00

# MCP
MCP_SERVER_PORT=3001
MCP_TRANSPORT=stdio
```

---

## 15. Success Criteria

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
