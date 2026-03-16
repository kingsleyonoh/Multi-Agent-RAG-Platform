---
description: Scans the codebase for changes and updates documentation to stay in sync.
---

# Sync Context

## Steps

// turbo-all

1. **Detect Staleness First:**
    - Read the `Last updated` date from `.agent/rules/CODEBASE_CONTEXT.md`.
    - Run: `git log --since="[last updated date]" --name-only --pretty=format:"" -- src/ app/ lib/` (adjust paths to actual source directories)
    - Filter to source files only (exclude docs/, .agent/, tests/).
    - If changed files found → note: *"⚠️ [N] source files changed since last sync — paying special attention to: [list of changed modules]"*
    - If zero changes → note: *"✅ No source changes since last sync — updating docs only."*

2. **Scan for Changes:**
    - Check all source directories for new/modified files since last sync.
    - Check dependency files for new/removed packages.
    - Check database schemas/migrations for new tables/columns.
    - Check for new environment variables or config changes.
    - Check for new external integrations or API endpoints.
    - Check for **new modules** (new top-level directories in `src/` or equivalent).

3. **Update `CODEBASE_CONTEXT.md`:**
    - Open `.agent/rules/CODEBASE_CONTEXT.md`.
    - Update each section to reflect current reality:
      - **Tech Stack** — any new dependencies or version changes
      - **Project Structure** — any new directories or files
      - **Key Modules** — any new modules or removed ones
      - **Database Schema** — any new tables or field changes
      - **External Integrations** — any new services
      - **Environment Variables** — any new or removed vars
      - **Commands** — any changed build/test/dev commands
      - **Key Patterns** — any new conventions discovered
      - **Shared Foundation** — if any new file is now imported by 3+ modules (or a previously shared file was removed), update the Shared Foundation table: `| Category | File path | What it establishes |`
    - Update `Last updated` date to today.

3.5. **Update Split Rules Files (if rules are split):**
    - Check if `.agent/rules/` contains split rules files (e.g., `CODING_STANDARDS_TESTING.md`, `CODING_STANDARDS_DOMAIN.md`). If only `CODING_STANDARDS.md` exists, skip this step.
    - If split files exist, **route new conventions to the correct file** based on domain:

      | If the new convention is about... | Write it to |
      |-----------------------------------|-------------|
      | Git, commits, AI discipline, workflow pipeline, skill selection, file limits, PowerShell, branching strategy | `CODING_STANDARDS.md` |
      | Testing, TDD, test quality, mocking, edge cases, test modularity, live integration testing | `CODING_STANDARDS_TESTING.md` |
      | Deployment, security, env vars, production-readiness, code organization, logging, error responses, naming conventions | `CODING_STANDARDS_DOMAIN.md` |

    - **NEVER dump all new conventions into `CODING_STANDARDS.md` by default.** Read the cross-reference headers at the top of each file to confirm the split structure.
    - **Size audit** — count characters in every file under `.agent/rules/` and `.agent/workflows/`:
      - If any `.agent/rules/` file exceeds **10,000 characters** → WARN and apply the correct split:

        | Oversized file | Split into |
        |----------------|------------|
        | `CODING_STANDARDS.md` | core → `CODING_STANDARDS.md`, testing → `CODING_STANDARDS_TESTING.md`, domain → `CODING_STANDARDS_DOMAIN.md` |
        | `CODEBASE_CONTEXT.md` | core (tech stack, structure, commands, env vars) → `CODEBASE_CONTEXT.md`, database → `CODEBASE_CONTEXT_SCHEMA.md`, modules/deep refs → `CODEBASE_CONTEXT_MODULES.md` |
        | Other rules file | Split by `##` headers into logical groups under 10K each, add cross-reference headers |

        **⛔ Before splitting:** Read the full split procedure in `.agent/guides/retrofit-guide.md` (Phase 0, Step 0b). It covers preserving project-specific content, adding cross-reference headers, and verification. Do NOT split from memory.

      - If any `.agent/workflows/` file exceeds **10,000 characters** → WARN: *"⚠️ [filename] is [N] chars — exceeds 10K limit. Consider converting to a stub + guide."*
    - **Guide reference check** — for each `.agent/workflows/` stub that contains a `view_file` reference to `.agent/guides/`:
      - Verify the referenced guide file actually exists.
      - If missing → ERROR: *"❌ [stub] references [guide] but the file does not exist."*
      - If the guide exists → **read it fully** before executing any step from the stub. Stubs are quick references only — the guide contains mandatory gates and detailed instructions.

4. **Maintain Deep References and TRIM bloat:**
    - For each module in the project, ensure a row exists in `## Deep References`.
    - **New module added** → add pointer row, e.g., `| Auth module | \`src/auth/\` |`
    - **Module removed** → remove its pointer row
    - **TRIM CHECK (mandatory, every sync):** For EVERY pointer row in Deep References, check the corresponding section above (Key Modules, Database Schema, etc.). If ANY section contains more than a one-line summary for a topic that has a pointer → **trim it now**:
      ```
      Before: "Auth module: handles JWT tokens, refresh, expiry, blacklisting, OAuth integration... [40 words]"
      After:  "Auth | JWT authentication and session management | → see Deep References"
      ```
    - **Do NOT skip this step because the pointers "already exist."** Pointers alongside verbose sections defeat the entire purpose. The file should shrink every time this runs until each pointed topic is a one-liner.
    - Target: CODEBASE_CONTEXT.md should be under 300 lines once Deep References are fully populated.

5. **Update Other Docs (if needed):**
    - Update `docs/progress.md` if new features were completed outside the workflow.
    - Update PRD if structural changes invalidate parts of the spec.

6. **Verify:** Confirm `CODEBASE_CONTEXT.md` matches the actual codebase — no stale references.

7. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
