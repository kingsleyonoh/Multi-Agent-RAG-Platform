# Bootstrap Project from PRD — Full Guide

**Description:** You drop a PRD into `docs/`, run `/bootstrap`, and the AI reads it and customizes EVERYTHING — not just the tracker, but the workflows, rules, and tooling to match your specific project. No generic files left behind.

## Prerequisites
- You've copied the project-template into your new project folder
- Your PRD has been refined (`/refine-prd`) and formatted (`/prepare-prd`)

> **Have an existing codebase instead?** Use `/retrofit` — it reads your code first and generates the docs from reality.

## ⛔ File Operations Discipline (MANDATORY)

- **NEVER use terminal commands** (`Set-Content`, `Add-Content`, `Out-File`, `echo >>`, heredoc `@'...'@`) to create or edit files.
- Use ONLY `view_file`, `write_to_file`, `replace_file_content`, or `multi_replace_file_content`.
- If a file read fails, **retry the read**. Do not fall back to terminal.
- If a file edit fails, **retry with corrected content**. Do not fall back to terminal.
- The ONLY acceptable terminal usage is: `git` commands, `mkdir`, `npm/pip/go install`, and similar system operations.

## Steps


1. **Find the PRD:**
    - Scan `docs/` for `.md` files that look like a spec/PRD.
    - Read the ENTIRE PRD — every section, every table, every schema.

2. **Extract Project Name:**
    - Find the project name from the PRD title or first heading.
    - Replace all `{{PROJECT_NAME}}` references in `.agent/rules/CODING_STANDARDS.md`, `.agent/rules/CODING_STANDARDS_TESTING.md`, `.agent/rules/CODING_STANDARDS_DOMAIN.md`, and `.agent/rules/CODEBASE_CONTEXT.md`.

2b. **Set Up Git Branching (DO THIS NOW — NOT LATER):**
    - Ensure git is initialized: `git init` (skip if `.git/` already exists)
    - Ensure on `main` branch: `git branch -M main`
    - Make initial commit if none exists: `git add . && git commit -m "chore(init): bootstrap project from PRD"`
    - Create and switch to `dev`: `git checkout -b dev`
    - **Verify:** `git branch --show-current` must output `dev`
    - **⛔ Do NOT proceed until you are on the `dev` branch.**

3. **Extract Build Phases:**
    - Find the "Build Phases", "Implementation Order", "Milestones", or similar section.
    - For EACH phase, extract every line item.
    - **MANDATORY: Insert Phase 0 as the FIRST block in `docs/progress.md`, BEFORE any feature work:**
      ```markdown
      ## Phase 0: Project Foundation

      ### Dev Environment Setup
      - [x] [SETUP] Git branching strategy (completed during bootstrap Step 2b)
        - `main` = production deployments only, `dev` = active development
      - [ ] [SETUP] Local service infrastructure (if PRD requires external services)
        - Scan PRD for external services (database, auth, storage, cache, etc.)
        - For each service that can run locally, set it up:
          - **Supabase** → `supabase init` + `supabase start` (requires Docker)
          - **PostgreSQL** → Docker container or Supabase local (already includes Postgres)
          - **Redis** → Docker container (`docker run -d --name redis-dev -p 6379:6379 redis`)
          - **MongoDB** → Docker container (`docker run -d --name mongo-dev -p 27017:27017 mongo`)
          - **S3/Storage** → MinIO via Docker (S3-compatible) or Supabase Storage local
          - **Stripe** → Stripe CLI for webhook forwarding (payments still mocked)
        - **Service Fallback Hierarchy** (use in order of preference):
          1. LOCAL INSTANCE (best) → Run the service on your machine (Docker, CLI)
          2. CLOUD DEV INSTANCE (good) → Dedicated dev/test instance (Supabase test project, staging DB)
          3. MOCK (last resort) → Only when local AND cloud dev are impossible
        - If PRD has NO external services (CLI tool, library, static site) → skip this item
        - Verify each service starts and is accessible
      - [ ] [SETUP] Environment configuration
        - Create `.env.local` with local service URLs (overrides `.env`)
        - Configure `TEST_DATABASE_URL` pointing to local Supabase/Postgres
        - Add `.env.local` to `.gitignore` if not already present
        - Document env setup in README or `CODEBASE_CONTEXT.md`

      ### Testing Infrastructure
      - [ ] [SETUP] Testing infrastructure
        - Install test runner (vitest/pytest/jest/etc. based on tech stack from PRD)
        - Create config file (vitest.config.ts/pytest.ini/jest.config.js/etc.)
        - Configure test runner to use local service URLs from `.env.local`
        - Create test directory structure matching src/ layout
        - Add test scripts to package.json / pyproject.toml / Makefile
        - Write one smoke test hitting the local database to verify connectivity (if applicable)
        - Confirm: test command runs green against local services
      ```
    - After Phase 0, auto-generate the remaining phases with exact checkboxes matching the PRD.
    - If the PRD has sub-items (e.g., individual models, endpoints), create indented sub-checkboxes.
    - Add PRD section references to each item (e.g., "Section 4.3").

    **⚠️ COMPLETENESS MANDATE — DO NOT SKIP OR SUMMARIZE:**
    - Every feature, endpoint, page, model, integration, and config item in the PRD **MUST** appear as a checkbox in `progress.md`. No exceptions.
    - **DO NOT summarize multiple PRD items into one checkbox.** If the PRD lists 5 endpoints, create 5 checkboxes — not one checkbox saying "API endpoints."
    - **DO NOT drop items because they seem obvious.** Auth, error handling, env config, deployment — if the PRD mentions it, it gets a checkbox.
    - **Walk EVERY PRD section systematically.** Do not rely on scanning for keywords. Read Section 1 → extract items. Read Section 2 → extract items. Continue until Section 15.
    - PRD sections to specifically mine for items (at minimum):
      - Section 4 (Features/Scope) — every feature, sub-feature, and edge case
      - Section 5 (User Journeys/Flows) — pages, forms, navigation
      - Section 5b (User Journeys & Screens) — screens, routes, accessibility
      - Section 6 (Integrations) — every external service
      - Section 7 (Data Model) — every table, relationship
      - Section 7b (Notifications) — every notification event, channel setup
      - Section 8 (API/Endpoints) — every route
      - Section 8b (API Endpoints) — every endpoint with method and auth
      - Section 9 (Project Structure) — scaffolding tasks
      - Section 10b (Performance & Observability) — monitoring setup, analytics integration
      - Section 14 (Configuration) — env vars, config files
    - **If in doubt, include it.** A checkbox that turns out to be trivial costs nothing. A dropped feature creates scope gaps.

    **⚠️ DEPENDENCY ORDER MANDATE — ITEMS MUST FOLLOW THE BUILD SEQUENCE:**
    - `progress.md` is a build plan, not a feature list. Items are picked top-to-bottom by `/implement-next`, so **order matters.**
    - **Across phases:** Earlier phases must contain foundations that later phases depend on. The general order is:
      1. Phase 0: Testing infrastructure
      2. Database schema / data models / migrations
      3. Core utilities, shared modules, config (Shared Foundation)
      4. Auth / middleware / security
      5. Backend API / server actions / business logic
      6. Frontend pages / components / forms
      7. Integrations / third-party services
      8. Polish / optimization / deployment
    - **Within each phase:** Order items so dependencies come first. Examples:
      - Database tables before the API routes that query them
      - Auth setup before protected routes
      - Layout/navigation before individual pages
      - Form components before the page that uses them
      - API client before the frontend that calls it
    - **If the PRD's phase order conflicts with build dependencies, FIX IT.** The PRD describes the product; `progress.md` describes the build. They don't have to match order — they must match scope.
    - **Never put a feature before its foundation.** If a page needs auth + a database table + an API endpoint, all three must appear BEFORE the page item.

3b. **Cross-Check: PRD vs progress.md (MANDATORY GATE):**
    - Re-read the ENTIRE PRD one more time.
    - For each PRD section, verify that every concrete deliverable has a matching checkbox in `progress.md`.
    - **Produce a count comparison:**
      ```
      PRD CROSS-CHECK
      ================
      PRD features:    [X] items found across all sections
      progress.md:     [Y] checkboxes generated
      
      Missing items:   [list any PRD items not in progress.md]
      Ordering issues: [list any items that appear before their dependencies]
      ```
    - If ANY items are missing → add them now before proceeding.
    - If ANY ordering issues exist → reorder now before proceeding.
    - **Do NOT proceed to Step 4 until the cross-check passes with zero missing items and zero ordering issues.**

3c. **Verify Dev Environment (MANDATORY GATE):**
    - Confirm `dev` branch is active (`git branch --show-current` → `dev`)
    - If the PRD requires external services, confirm all local services are running:
      - **Supabase:** `supabase status` shows all services running
      - **PostgreSQL:** Database accepts connections on configured port
      - **Redis:** `redis-cli ping` → `PONG`
      - **Other services:** each responds to its health check
    - Confirm `.env.local` has correct URLs for all local services
    - If ANY service fails to start, document the issue and flag to user before proceeding
    - **If PRD has no external services → confirm git branching is set up and skip service checks**

4. **Extract Success Criteria:**
    - Find "Success Criteria", "Definition of Done", "Acceptance Criteria", or similar section.
    - Add these as a separate tracked section at the bottom of `docs/progress.md`.

5. **Customize CODING_STANDARDS.md (and split files):**
    - Extract architecture rules, dependency hierarchies, and conventions from the PRD.
    - **Replace the generic rules with project-specific ones:**
      - App/module dependency hierarchy (from PRD Section 9)
      - Import conventions
      - Multi-tenant rules (if applicable)
      - Framework-specific conventions
      - Database conventions (UUID vs auto-increment, timestamp fields, etc.)
    - Keep ALL the generic AI discipline rules (including workflow discipline, use skills when available (skills > pre-trained knowledge)), testing anti-cheat rules, production-readiness rules, deployment platform, public demo security, environment variables, and the **Skill Selection & Orchestration** SOP.
    - Only customize the architecture/framework sections.
    - **Replace `{{PROJECT_NAME}}` in all 3 CODING_STANDARDS files.**
    - **Domain rules extraction:** If any domain in the PRD has 5+ concentrated conventions (e.g., complex auth patterns, multi-tenant DB rules, strict API conventions), extract those into `.agent/rules/[domain]_rules.md` and add a pointer row in the **Domain-Specific Rules** table in CODING_STANDARDS.md. This keeps the main file lean.
    - **⛔ SIZE GATE:** After customization, verify each rules file is under 10,000 characters. If any file exceeds 10,000 characters, split it further by extracting sections into new files with cross-reference headers.

    **5b. Populate `CODEBASE_CONTEXT.md` with Deep References and Shared Foundation:**
    - Open `.agent/rules/CODEBASE_CONTEXT.md` (copied from template).
    - Fill in the Tech Stack, Project Structure, and Key Modules sections from the PRD.
    - **Populate `## Shared Foundation`** from the PRD's architecture section:
      - Identify cross-cutting concerns: DB client, auth middleware, error handler, config loader, shared types, base components, API client, etc.
      - Pre-populate the table with expected file paths and what each establishes.
      - Example rows: `| Error handling | src/lib/errors.ts | Centralized error types and handler |`, `| DB client | src/lib/db.ts | Database connection and query helpers |`
    - **Populate `## Deep References`** with aspirational pointers based on the PRD's planned modules (e.g., `| Auth | \`src/auth/\` |`, `| Payments | \`src/payments/\` |`).
    - **Populate observability context from Section 10b:** Add error tracking tool, logging destination, monitoring provider, and analytics tool to the External Integrations section.
    - **Populate notification stack from Section 7b:** Add delivery services (email provider, push provider) to External Integrations.
    - **Keep all sections to one-line summaries per module.** The pointers tell the AI where to find detail later. Target: under 300 lines from the start.
    - Set `Last updated` to today.
    - Set `Template synced` to today. This records the baseline for CHANGELOG-driven sync — future syncs will only apply changes dated after this.
    - **⛔ SIZE GATE:** After population, if `CODEBASE_CONTEXT.md` exceeds 10,000 characters, split it:
      - `CODEBASE_CONTEXT.md` → core (tech stack, structure, commands, env vars, key patterns)
      - `CODEBASE_CONTEXT_SCHEMA.md` → database schema, data access patterns
      - `CODEBASE_CONTEXT_MODULES.md` → key modules detail, deep references
      - Add cross-reference headers to each file.

6. **Customize Workflow Files for This Project:**

    **This is the most important step.** The template workflows are starting points. After bootstrap, every workflow must be tailored to the project's tech stack, directory structure, and commands.

    **Process for EACH workflow** (one at a time, in order):
    1. **Read** the generic version with `view_file` (MANDATORY — understand the structure first)
    2. **Identify** what needs project-specific replacement (see table below)
    3. **Write** the customized version with `write_to_file` (Overwrite: true)
    4. **Verify** the file was written by reading the first 20 lines

    **What to customize in each workflow:**

    | Replacement Target | Generic → Project-Specific |
    |---|---|
    | Test commands | `npm test` → actual test runner (e.g., `go test ./...`, `pytest`) |
    | Lint/check commands | `npx tsc` → actual linter (e.g., `go vet ./...`, `ruff check .`) |
    | Directory paths | `src/`, `app/`, `lib/` → actual project dirs (e.g., `internal/`, `cmd/`) |
    | Commit scopes | Generic scopes → project module names from PRD |
    | File read paths | Generic scan paths → actual config files, schemas, key modules |
    | Module references | "source files" → actual module/package names from PRD |

    **Workflow priority order:**

    | # | Workflow | Key Focus |
    |---|---|---|
    | 1 | implement-next.md | Test/lint commands, dir refs, commit scopes, TDD cycle commands |
    | 2 | resume.md | Source paths for stale check, config files to read, scan directories |
    | 3 | commit.md | Source code paths for diff, commit scopes |
    | 4 | add-task.md | Module names for context reading |
    | 5 | clarify.md | Module names, architecture refs |
    | 6 | report-bug.md | Source paths for investigation |
    | 7 | deep-study.md | Directories to scan, output to CODEBASE_CONTEXT.md |
    | 8 | finalize-plan.md | Key file paths |
    | 9 | generate-tests.md | Test runner, test file patterns, fixture style |
    | 10 | security-audit.md | Source dirs to scan, deployment config paths, test commands |
    | 11 | check-modularity.md | Source dirs, file size limits, import rules |
    | 12 | refactor-module.md | Source dirs, test commands, regression suite |
    | 13 | sync-context.md | Source dirs to scan, config files to read |
    | 14 | bug-investigator.md | Source dirs, log paths, config files |
    | 15 | status.md | Source dirs, test commands, progress file path |
    | 16 | validate-prd.md | Test commands, browser test URLs, source dirs |
    | 17 | setup-ci.md | Tech stack detection paths, deploy config |
    | 18 | fix-ci.md | Test commands, CI log paths |
    | 19 | generate-readme.md | Source dirs, config files, git remote |
    | 20 | hotfix.md | Source dirs, test commands, commit scopes |
    | 21 | audit-progress.md | PRD path, progress.md path, source dirs |

    **After all generic workflows:** Create tech-stack-specific scaffolding workflows based on the PRD (e.g., `/new-model`, `/new-route`, `/new-component`). Each should create the file, update imports, and include a test stub.

    **Rules for ALL customized workflows:**
    - **Preserve the generic structure and step sequence** — you are CUSTOMIZING, not rewriting from scratch
    - Every workflow must END with: `Read PIPELINE.md and suggest the appropriate next workflow.`
    - `/check-modularity` chains to `/refactor-module` when violations found (via PIPELINE.md)
    - `/refactor-module` includes: pre/post regression, one violation at a time, user approval
    - `/report-bug.md` MUST include: "This workflow CAPTURES bugs. It does NOT fix them. Do NOT modify source code."
    - After this step, zero generic workflow content should remain

7. **Extract Environment Variables:**
    - Find the "Environment Variables" or "Configuration" section.
    - Generate `.env.example` with all variables listed (values set to `xxxxx`).
    - **Paid API detection:** If the PRD references any paid external APIs (OpenRouter, OpenAI, Anthropic, Stripe, Twilio, SendGrid, etc.), add `DEMO_MODE=true` to `.env.example` with comment: `# Enable demo security protections (rate limits, usage caps). See CODING_STANDARDS.md § Public Demo Security.`
    - If `DEMO_MODE` is added, note it in the report (Step 12).

8. **Generate `CODEBASE_CONTEXT.md`:**
    - Open `.agent/rules/CODEBASE_CONTEXT.md` (copied from template).
    - **Remove the `<template_manager_warning>` block entirely.** It is only for the template editors, not project users.
    - Populate with:
      - **Tech Stack** table (from PRD Section 3)
      - **Project Structure** (from PRD Section 9)
      - **Key Modules** summary (from PRD Section 5) — one-line per module
      - **Database Schema** overview (from PRD Section 4)
      - **Environment Variables** list (from PRD Section 14)
      - **External Integrations** (from PRD Section 6)
      - **Commands** — dev server, test runner, lint, build, migrate (from PRD or detected)
      - **Key Patterns & Conventions** — from PRD architecture section
      - **Deep References** — aspirational directory pointers from PRD Section 9 project structure, e.g., `| Auth module | \`src/auth/\` |`. These are forward-looking (directories don't exist yet). `/deep-study` or `/sync-context` will replace placeholders with real paths and trim embedded sections later.
      - `Last updated: [today's date]`
    - This is the source of truth for `/resume`, `/deep-study`, `/add-task`, `/implement-next`, and all other workflows — it must exist from day one.

9. **Generate .gitignore:**
    - Based on detected tech stack, create an appropriate `.gitignore`.
    - **MANDATORY entries (include in EVERY project regardless of tech stack):**
      ```
      # AI Workflow System (proprietary — do not publish)
      .agent/workflows/
      .agent/guides/

      # Internal project planning
      docs/progress.md
      docs/*PRD*.md
      docs/*prd*.md
      ```
    - `.agent/rules/` is NOT excluded — `CODEBASE_CONTEXT.md` and `CODING_STANDARDS.md` help forkers understand the project.
    - Add tech-stack-specific entries on top (`node_modules/`, `__pycache__/`, `.env`, etc.).

10. **Generate Deployment Files:**
    - Copy `Dockerfile`, `docker-compose.prod.yml`, and `.dockerignore` from template root.
    - **Customize `Dockerfile`** based on detected tech stack:
      - Node.js/TypeScript → `node:22-alpine` base, `npm ci` + `npm run build`
      - Python/FastAPI → `python:3.12-slim` base, `pip install` + `uvicorn`
      - Go → `golang:1.22-alpine` base, `go build` → scratch runtime
      - Other → leave the generic template with `TODO` comments for the user
    - **Customize `docker-compose.prod.yml`:**
      - Replace `PROJECT_SLUG` with the project name slug (lowercase, hyphens)
      - Replace `project-slug.kingsleyonoh.com` with actual subdomain
      - Add database service if PRD requires PostgreSQL/Redis/MongoDB
    - **Customize `.dockerignore`:**
      - Add stack-specific entries (e.g., `__pycache__/` for Python, `target/` for Go)
    - If PRD specifies Railway/Vercel/AWS instead → still generate the files (they serve as containerization reference) but note the override in comments.

// turbo
11. **Install Git Commit Hook:**
    - Create `.git/hooks/commit-msg` with a shell script that validates the `type(scope): message` format.
    - Allowed types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`.
    - Scope should match the project's modules/apps.
    - Allow merge commits through (starts with "Merge").
    - Show clear error message with examples on rejection.

12. **Report to User:**
    ```
    PROJECT BOOTSTRAPPED
    ====================
    Project: [name]
    Tech Stack: [detected]
    Phases: [count] phases, [count] total items
    Success Criteria: [count] items
    
    Files updated:
    ✅ docs/progress.md — [X] checkboxes from PRD
    ✅ .agent/rules/CODING_STANDARDS.md — project-specific rules added
    ✅ .agent/rules/CODING_STANDARDS_TESTING.md — testing rules
    ✅ .agent/rules/CODING_STANDARDS_DOMAIN.md — domain rules
    ✅ .agent/rules/CODEBASE_CONTEXT.md — project context generated
    ✅ .env.example — [X] variables
    ✅ .gitignore — generated for [tech stack]
    ✅ Dockerfile — customized for [tech stack]
    ✅ docker-compose.prod.yml — [project-slug].kingsleyonoh.com
    ✅ .dockerignore — stack-specific exclusions
    
    Workflows customized (21 total):
    ✅ /implement-next — uses [test command], [lint command]
    ✅ /resume — source paths, config files
    ✅ /commit — source paths, commit scopes
    ✅ /add-task — module names, context reading
    ✅ /clarify — module names, architecture refs
    ✅ /report-bug — source paths for investigation
    ✅ /deep-study — scan dirs, CODEBASE_CONTEXT output
    ✅ /finalize-plan — key file paths
    ✅ /generate-tests — test runner, patterns, fixtures
    ✅ /security-audit — source dirs, deployment config
    ✅ /check-modularity — source dirs, size limits
    ✅ /refactor-module — source dirs, regression suite
    ✅ /sync-context — source dirs, config files
    ✅ /bug-investigator — source dirs, log paths
    ✅ /status — source dirs, test commands
    ✅ /validate-prd — test commands, browser URLs
    ✅ /setup-ci — tech stack paths, deploy config
    ✅ /fix-ci — test commands, CI log paths
    ✅ /generate-readme — source dirs, git remote
    ✅ /hotfix — source dirs, commit scopes
    ✅ /audit-progress — PRD path, progress path
    ✅ /new-[scaffold] — [count] project-specific workflows created
    
    Review these files, then type /implement-next to start building.
    ```

## What You (the user) Do

```
1. Create project folder
2. Copy template into it
3. Drop your PRD into docs/
4. Open in Antigravity
5. /refine-prd   — discuss and iterate
6. /prepare-prd  — format into 15 sections
7. /bootstrap    — YOU ARE HERE: everything gets customized
8. /implement-next — start building
```

That's it. The PRD is the ONLY thing you write manually. Everything else adapts to it.
