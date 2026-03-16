---
description: Deep study of the entire codebase before any planning or implementation begins.
---

# Deep Study

Run BEFORE writing any implementation plan or making code changes. The output of this workflow is a fully populated `CODEBASE_CONTEXT.md` — the AI's persistent memory of the project.

> **Rule: Never assume. Always verify. Everything you learn gets saved to CODEBASE_CONTEXT.md.**

## Steps

// turbo-all

1. **Map Project Structure:**
    - `list_dir` on root, every source directory.
    - Document: entry point, config, apps/modules, shared utilities.

2. **Read Configuration:**
    - Settings files, env vars, dependency files.
    - Note all external services and API integrations.

3. **Read Database/Schema:**
    - All models/schemas/migrations.
    - Document relationships and constraints.

4. **Read Core Business Logic:**
    - Service layer, engines, core algorithms.
    - Document public functions and their signatures.

5. **Read Tests:**
    - What's tested, what's not.
    - Note the test framework, patterns used (fixtures, factories, mocks).
    - Note naming conventions for test files and test functions.
    - Run the full suite: note pass/fail count.

6. **Identify Patterns & Conventions:**
    - How are errors handled? (custom exceptions? HTTP codes? logging?)
    - How is authentication done?
    - How are new features typically structured? (router → service → model?)
    - What naming conventions are used?

7. **Populate `CODEBASE_CONTEXT.md`:**
    - Open `.agent/rules/CODEBASE_CONTEXT.md`.
    - Fill in EVERY section with what you found:
      - **Tech Stack** — language, framework, DB, hosting, test runner, build tool
      - **Project Structure** — directory tree with purpose annotations
      - **Key Modules** — name, purpose, one-line summary, key files for each
      - **Database Schema** — tables, purpose, key fields
      - **External Integrations** — services, purpose, auth method
      - **Environment Variables** — variable, purpose, source
      - **Commands** — dev server, run tests, lint, build, migrate
      - **Key Patterns & Conventions** — naming, structure, error handling, imports
      - **Shared Foundation** — identify files imported by 3+ modules (DB clients, auth middleware, error handlers, shared types, utility modules, base components, shared styles). Add each to the table with `| Category | File path | What it establishes |`
    - Update `Last updated` date to today.

8. **Populate `Deep References` and Trim Embedded Sections:**
    - For each module discovered, add a row to the `## Deep References` table pointing to its directory.
    - For each row added: **trim the corresponding embedded section above to a one-line summary.** Detail lives in the source — the pointer tells the AI where to find it.
      ```
      Before: Auth module row with 40-word description and 5 files listed
      After:  Auth | JWT authentication | src/auth/ → see Deep References
      ```
    - **This is the fix for bloated CODEBASE_CONTEXT files.** Pointers alongside bloat defeat the purpose.
    - **This file is the permanent output of the deep study.** It survives across conversations.

8.5. **Save Key Discoveries as Knowledge Items:**
    - For each non-obvious architectural decision or "gotcha" discovered:
      - Save as a Knowledge Item with project-scoped title (e.g., "[ProjectName] — Auth uses JWT with Redis blacklist")
      - Only save decisions that would be costly to re-discover
    - Do NOT save general context — that's what CODEBASE_CONTEXT.md is for.
    - Target: 2-5 KIs max per deep study — quality over quantity.

9. **Report to User:**
    ```
    DEEP STUDY COMPLETE
    ===================
    Project: [name]
    Stack: [summary]
    Modules: [count] modules mapped
    DB Tables: [count] tables documented
    Integrations: [count] external services
    Tests: [X] passed, [Y] failed
    
    CODEBASE_CONTEXT.md has been populated with full project context.
    This will be used by /resume, /add-task, /implement-next, and all other workflows.
    ```

10. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
