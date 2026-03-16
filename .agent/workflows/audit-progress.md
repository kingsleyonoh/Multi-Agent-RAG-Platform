---
description: Audits progress.md against the PRD for missing items, vague checkboxes, and dependency-order violations. Re-runnable anytime.
---

# Audit Progress

**Description:** Re-reads the full PRD section-by-section and cross-checks `progress.md` for completeness, granularity, and correct build order. Use this after `/bootstrap`, after adding many tasks, or whenever `progress.md` feels incomplete or poorly ordered.

> **Use this when:** Bootstrap produced a lazy `progress.md`, features were added informally, or you suspect items are missing or misordered.

## ⛔ Full Read Rule (MANDATORY)

> **You MUST read this ENTIRE file from first line to last line BEFORE executing Step 1.** This workflow is 300+ lines. If you start executing after reading only the first screen, you WILL miss critical audit phases, cross-check rules, and the report format. Make multiple sequential read calls if needed until you have read every line.



---

## Step 1: Read the PRD (MANDATORY FULL READ)

Read the ENTIRE PRD — every section, every sub-section, every bullet point. Do NOT skim.

Search paths:
```
docs/PRD.md
docs/prd.md
PRD.md
```

**Self-check:** After reading, you must be able to answer:
- What is the tech stack?
- How many features are described?
- What integrations exist?
- What are the success criteria?

If you cannot answer all four, re-read the PRD.

---

## Step 2: Read progress.md (MANDATORY FULL READ)

```
docs/progress.md
```

Read every line. Note the current phase structure, checkbox count, and item ordering.

---

## Step 3: Completeness Audit

Walk each PRD section and extract every **concrete deliverable** — a feature, screen, endpoint, table, integration, config item, or setup task that should have its own checkbox.

**Sections to mine (at minimum):**
- Section 4 (Features/Scope) — every feature, sub-feature, edge case
- Section 5 (User Journeys/Flows) — pages, forms, navigation
- Section 5b (User Journeys & Screens) — screens, routes, accessibility setup
- Section 6 (Integrations) — every external service
- Section 7 (Data Model) — every table, relationship, migration
- Section 7b (Notifications) — every notification event, channel setup
- Section 8 (API/Endpoints) — every route
- Section 8b (API Endpoints) — every endpoint with method and auth
- Section 9 (Project Structure) — scaffolding tasks
- Section 10b (Performance & Observability) — monitoring setup, analytics integration
- Section 12b (Migration Plan) — data migration, cutover tasks
- Section 14 (Configuration) — env vars, config files

For each deliverable found in the PRD, check if `progress.md` has a matching checkbox. Mark it as:
- ✅ **Covered** — a matching checkbox exists
- ❌ **Missing** — no checkbox for this deliverable
- ⚠️ **Partial** — the deliverable is mentioned but bundled with other items

---

## Step 4: Granularity Audit

Review every checkbox in `progress.md` and flag items that are **too vague or bundled**:

**Flag if:**
- A single checkbox covers 2+ distinct features (e.g., "Build user dashboard" when the PRD describes 5 dashboard widgets)
- The checkbox text is so vague it could mean anything (e.g., "Set up backend")
- The checkbox cannot be tested independently — if you can't write a test for it, it's too broad

**Suggest splits:** For each flagged item, propose specific replacement checkboxes based on the PRD.

---

## Step 5: Dependency Order Audit

For each checkbox in `progress.md`, verify its dependencies appear **before it** in the list. The AI picks items top-to-bottom, so order IS the build sequence.

**Enforce the build sequence:**
1. Phase 0: Testing infrastructure
2. Database schema / data models / migrations
3. Core utilities, shared modules, config (Shared Foundation)
4. Auth / middleware / security
5. Backend API / server actions / business logic
6. Frontend pages / components / forms
7. Integrations / third-party services
8. Polish / optimization / deployment

**Check within each phase:**
- Database tables before the API routes that query them
- Auth setup before protected routes
- Layout/navigation before individual pages
- Form components before the page that uses them
- API client before the frontend that calls it
- Shared utilities before the modules that import them

**Flag violations:** Any item that appears before something it depends on.

---

## Step 5b: Test Coverage Audit

For every code file task in `progress.md` (e.g., "Implement config/config.go", "Create adapter/stripe.go"), check if there is a corresponding test task — either as a sub-item or a separate checkbox.

**Flag if:**
- A code file has no test task anywhere in `progress.md`
- Config/utility files (config loaders, error handlers, validators) lack test tasks — these are easy wins that often get skipped
- Test tasks exist but are placed in a later phase than the code they test (tests should be co-located with implementation, not deferred)

**Suggest:** Add test task as a sub-item under the implementation checkbox, or as the next checkbox after it.

---

## Step 5c: Implied Tasks Audit

Some tasks are never explicitly stated in the PRD but are required for a working system. Check for:

| Implied Task | Check For |
|---|---|
| **Main wiring** | If there's a `main.go`, `index.ts`, or entry point — is there a task for dependency injection, server startup, graceful shutdown? |
| **Config validation** | If there's a config loader — is there a task for testing invalid env vars, missing required fields, bad formats? |
| **Error response format** | If the PRD defines error codes — is there a task for the shared error response struct/handler? |
| **Health check dependencies** | If a health endpoint checks DB/Redis — are those connection setups in earlier phases? |
| **Migration runner** | If there are migration files — is there a task for the migration execution mechanism? |

**Flag:** Any implied task that has no checkbox. Suggest adding it in the correct phase.

---

## Step 5d: Phase Placement Audit

Check that tasks are in the right phase — not just the right order within a phase.

**Rules:**
- **Dev tooling** (Docker Compose, Makefile, local dev setup) → belongs in **Phase 0**, not later phases
- **Scaffolding** (directory structure, go mod init, package.json) → belongs in **Phase 0 or Phase 1**
- **Test tasks** → same phase as the code they test, not deferred to a "testing phase"
- **Deployment/CI** → last phase only
- **Redundant test tasks** → if a code task already has test sub-items AND there's a separate "write tests for X" task later, flag the duplication

**Flag:** Any task that would work better in a different phase, with the suggested move.

---

## Step 5e: Reverse Completeness (Scope Creep Detection)

Walk every checkbox in `progress.md` and verify it maps back to a concrete PRD requirement.

**Flag if:**
- A task has no traceable origin in the PRD — the AI invented it during bootstrap
- A task goes beyond the PRD scope (e.g., PRD says "basic auth" but progress.md has "OAuth2 + SSO")
- A task duplicates another task with different wording

**Action:** Mark flagged items with `[SCOPE?]` for user review. Do NOT auto-remove — the user decides if they belong.

---

## Step 5f: Success Criteria Audit

Read PRD Section 15 (Success Criteria / Acceptance Criteria). For EACH criterion, check if `progress.md` has a task that would **verify or implement** it.

**Examples:**
- PRD says "reconciliation completes in <30s for 10k transactions" → need a task for performance benchmarking
- PRD says "99.9% uptime" → need a task for health checks + monitoring setup
- PRD says "zero data loss on crash" → need a task for graceful shutdown + transaction safety

**Flag:** Any success criterion with no implementing or verifying task in `progress.md`.

---

## Step 5g: Cross-Cutting Concerns Audit

Some concerns are mentioned across multiple PRD sections but need a single, dedicated task. Check for:

| Concern | What to look for |
|---|---|
| **Structured logging** | Is there one task to set up the logging framework, or is it assumed everywhere? |
| **Input validation** | Does every API endpoint task include validation, or is there a shared validation layer task? |
| **Graceful shutdown** | Signal handling + connection draining — often implied but never tasked |
| **Data seeding** | If PRD mentions test/demo data — is there a task to create seed scripts? |
| **Environment config** | If PRD mentions staging/production — are there env-specific config tasks? |

**Flag:** Any cross-cutting concern that appears 2+ times in the PRD but has no dedicated setup task.

---

## Step 6: Produce the Audit Report

Output a structured report:

```
PROGRESS.MD AUDIT REPORT
=========================
Date: [today]
PRD sections audited: [count]/20

COMPLETENESS
─────────────
PRD deliverables found:  [X]
progress.md checkboxes:  [Y]
Missing items:           [count]
Partial items:           [count]

[List each missing/partial item with its PRD section source]

GRANULARITY
─────────────
Vague/bundled items:     [count]

[List each flagged item with suggested splits]

DEPENDENCY ORDER
─────────────
Order violations:        [count]

[List each violation: "Item X depends on Item Y, but X appears at line N before Y at line M"]

TEST COVERAGE
─────────────
Code files without tests: [count]
Deferred test tasks:      [count]

[List each code file missing tests and any test tasks in wrong phase]

IMPLIED TASKS
─────────────
Missing implied tasks:    [count]

[List each implied task not found in progress.md]

PHASE PLACEMENT
─────────────
Misplaced items:          [count]
Redundant test tasks:     [count]

[List each misplaced item with current vs suggested phase]

REVERSE COMPLETENESS (SCOPE CREEP)
─────────────
Tasks without PRD origin:  [count]
Scope overreach items:     [count]
Duplicate tasks:           [count]

[List each flagged task with reason]

SUCCESS CRITERIA
─────────────
PRD criteria total:        [count]
Criteria with tasks:       [count]
Criteria without tasks:    [count]

[List each uncovered criterion from Section 15]

CROSS-CUTTING CONCERNS
─────────────
Missing setup tasks:       [count]

[List each cross-cutting concern found in 2+ PRD sections without a dedicated task]

VERDICT: [PASS / NEEDS FIXES]
```

---

## Step 7: Apply Fixes (WITH USER APPROVAL)

**Do NOT auto-fix.** Present the report to the user first.

If the user approves fixes:
1. **Add missing items** — insert them in the correct dependency position, not just at the end
2. **Split bundled items** — replace the vague checkbox with specific sub-items
3. **Reorder violations** — move items so dependencies come before dependents
4. Preserve all existing `[x]` (completed) and `[/]` (in-progress) statuses

---

## Step 8: Verification Re-check

After applying fixes, re-run Steps 3-5 one more time to confirm:
- Zero missing items
- Zero vague/bundled items
- Zero dependency order violations

Output the final count:
```
POST-FIX VERIFICATION
======================
Missing items:      0
Bundled items:      0
Order violations:   0
Status: CLEAN ✓
```

---

**When done, suggest:** *"Progress audit complete. Run `/implement-next` to continue building."*
