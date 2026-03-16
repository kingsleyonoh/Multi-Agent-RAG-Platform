# Multi-Agent RAG Platform — Coding Standards: Domain & Production

> Part 3 of 3. Also loaded: `CODING_STANDARDS.md`, `CODING_STANDARDS_TESTING.md`

## Architecture Rules (Project-Specific)

### Dependency Hierarchy (Enforced)
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
- **NEVER import upward** in this hierarchy. If `db/` needs something from `llm/`, the design is wrong.
- **NEVER import across siblings** unless there's an explicit arrow above.

### OpenRouter Rules
- **ALL LLM and embedding calls** go through `src/llm/openrouter.py` — never call model APIs directly.
- **ALL config** reads from `src/config.py` Pydantic Settings — never use `os.getenv()` directly.
- Model names use OpenRouter format: `provider/model-name` (e.g., `openai/gpt-4o`, `anthropic/claude-3.5-sonnet`).

### Python/FastAPI Conventions
- Use `async def` for all route handlers and DB operations.
- Use Pydantic v2 models for all request/response schemas.
- Use `Depends()` for dependency injection (auth, DB sessions, rate limiting).
- Database sessions via async context manager — never open sessions without cleanup.
- UUID primary keys for all tables (use `uuid7()` for time-ordered IDs).
- All timestamps use `datetime.utcnow()` with UTC timezone.

## Public Demo Security

> This project uses OpenRouter (paid API). When deployed publicly (`DEMO_MODE=true`):

- **Rate limiting:** Enforce per-IP and per-API-key rate limits (see PRD Section 8b rate limit column).
- **Cost caps:** Enforce `DAILY_COST_LIMIT_USD` per user. Return `COST_LIMIT_EXCEEDED` error when exceeded.
- **Token limits:** Cap max input tokens per request to prevent prompt-stuffing attacks.
- **API key rotation:** Support multiple API keys via `API_KEYS` env var (comma-separated).
- **No anonymous access:** All endpoints except `/api/health` require `X-API-Key`.

## Deployment Flow (Dev → Production)

### Dev Branch Workflow
1. All implementation work happens on `dev` branch
2. Tests run against local Docker services (PostgreSQL + pgvector, Neo4j, Redis)
3. Each completed item → commit → push to `dev`
4. Run full test suite frequently

### When Ready to Deploy
1. Ensure ALL tests pass on `dev`
2. Merge `dev` → `main`
3. SSH into Hetzner VPS → `git pull origin main`
4. `docker compose run --rm app alembic upgrade head` (run migrations)
5. `docker compose up -d` → verify deployment

### Emergency Hotfix Flow
- Branch from `main` → `hotfix/description`
- Fix + test → merge to BOTH `main` and `dev`
- Use `/hotfix` workflow for guidance

## Security Rules

### Secrets Management
- **NEVER hardcode secrets** — no API keys, passwords, tokens in source code
- Use `.env` files locally (listed in `.gitignore`)
- Use environment variables in production
- If you accidentally commit a secret, **rotate it immediately**

### Input Validation
- Validate ALL user input at the boundary (API route, form handler)
- Use Pydantic v2 models for all request/response validation
- Never trust client-side validation alone

### Authentication & Authorization
- Verify auth on EVERY protected endpoint
- Check permissions, not just authentication
- Log auth failures

### SQL & Data Safety
- Use parameterized queries or ORM methods — NEVER string concatenation for SQL
- Sanitize HTML output to prevent XSS
- Validate file upload types and sizes

## Environment Variables
- `.env` for local development (NEVER committed)
- `.env.example` for documenting required vars (committed, no real values)
- Production variables set via hosting platform UI/CLI
- NEVER log env var values

## Production-Readiness Rules (Before Merge to Main)

Before merging ANY feature to `main`:

1. **All tests pass** — `python -m pytest` shows 0 failures
2. **No print debugging** — remove all `print()` and debug output, use structlog
3. **No TODO/FIXME/HACK** — resolve them or create tickets
4. **Error handling exists** — no unhandled exceptions in user flows
5. **Types are complete** — no `Any` types, all functions type-hinted
6. **Migrations committed** — all DB changes have Alembic migration files
7. **Environment variables documented** — new ones added to `.env.example`
8. **Linting passes** — `ruff check .` clean, `mypy src/` passes

## Code Organization Conventions

### Import Order
1. Standard library imports
2. Third-party package imports
3. Local/project imports
4. Blank line between each group

### Naming Conventions
- **Files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/Methods:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** Prefix with `_`
- **Pydantic models:** `{Entity}Create`, `{Entity}Response`, `{Entity}Update`

### Project Structure
- Follow the structure defined in `CODEBASE_CONTEXT.md`
- New modules go in the documented location for that type
- If unsure where something belongs, check `CODEBASE_CONTEXT.md` or ask

## Logging Standards
- Use `structlog` for all logging — JSON output to stdout
- Log levels: DEBUG (dev only), INFO (normal events), WARNING (recoverable), ERROR (failures), CRITICAL (system down)
- Include context: user_id, request_id, module name
- NEVER log sensitive data (passwords, tokens, PII, API keys)
- All LLM calls must log: model, tokens_in, tokens_out, cost_usd, latency_ms

## Error Response Standards
- Consistent error format across all endpoints
- Include: error code, human-readable message, timestamp
- Never leak stack traces to clients in production
- Log full error details server-side
