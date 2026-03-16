---
description: Reads all context files to restore full project knowledge at the start of a new conversation.
---

# Resume Context

**Goal:** Restore complete project understanding so the user never has to re-explain anything. The AI should emerge from this workflow knowing the project as well as if it had been in the conversation the whole time.

## Steps

// turbo-all

1. **Read Project Context (FULL READ — every line, no skipping):**
    - `.agent/rules/CODEBASE_CONTEXT.md` — architecture, tech stack, modules, commands, integrations. Read the ENTIRE file. If it's longer than your read limit, make multiple calls until you've read every line.
    - **Check for CODEBASE_CONTEXT split files:** If `.agent/rules/CODEBASE_CONTEXT_SCHEMA.md` or `CODEBASE_CONTEXT_MODULES.md` exist, read those too — they contain overflow context that was split to stay under the platform's 12K character limit.
    - `.agent/rules/CODING_STANDARDS.md` — core rules (AI discipline, git, PowerShell, modularity). Read the ENTIRE file top to bottom.
    - `.agent/rules/CODING_STANDARDS_TESTING.md` (if exists) — testing and TDD rules. Read fully.
    - `.agent/rules/CODING_STANDARDS_DOMAIN.md` (if exists) — deployment, security, and naming conventions. Read fully.

1b. **Check Knowledge Items (KI):**
    - Review KI summaries provided at conversation start. If any KI title matches this project's name, domain, or tech stack — read its artifacts now.
    - KIs contain architectural decisions, debugging history, and patterns from previous conversations that won't be in the project files.

2. **Read What Was Happening (FULL READ — every line):**
    - `docs/progress.md` — read the ENTIRE file from first line to last line. If longer than your read limit, make multiple sequential calls:
      - What's completed `[x]`
      - What's in-progress `[/]` — this is the most important section
      - What's next `[ ]`
      - Any deviations and why they happened
    - For any `[/]` in-progress items: read their full context sub-items carefully — these are what the user was mid-stream on.

3. **Read the PRD (MANDATORY — DO NOT SKIP):**
    - **Search for the PRD:** Check `docs/PRD.md`, `docs/prd.md`, `PRD.md`, and any file in `docs/` containing "Product Requirements" or "PRD" in its name. If you find it, read it. If you genuinely cannot find any PRD file after checking all these locations, state: "No PRD file found at [paths checked]" and proceed — but this should be rare.
    - **Read the ENTIRE PRD — every section, every line, no exceptions.** If it's 500+ lines, read in multiple passes (lines 1–200, 201–400, etc.) until you have read every single line. Do NOT read 200 lines and assume you know the rest.
    - **Pay special attention to these sections** — they constrain ALL work:
      - **Architecture Principles** (Section 2) — tech choices, design philosophy
      - **Features & Scope** (Section 4) — what to build and what NOT to build
      - **Project Structure** (Section 9) — folder layout, naming conventions
      - **What NOT to Build** (Section 12) — explicit exclusions
    - Note any constraints, rejected alternatives, or explicit "do NOT" instructions. These override your instincts.
    - **After reading, you MUST be able to answer:** What is the tech stack? What are the build phases? What is explicitly out of scope? If you cannot answer these, you did not read the PRD — go back and read it.

3.5. **Read Shared Foundation (MANDATORY):**
    - Open the **Shared Foundation** table in `CODEBASE_CONTEXT.md`.
    - Read every file listed in that table **in full** — if a file is 300 lines, read all 300 lines.
    - These define the project's established patterns, shared utilities, and cross-cutting concerns.
    - Do NOT proceed to the report without reading these files. They are the foundation everything else builds on.

4. **Read the Active Code:**
    - For each in-progress `[/]` task, read the source files listed in its context.
    - If no files are listed, read the module most relevant to the task description.
    - Goal: understand the current state of the code, not just what the plan said.

4b. **Confirm Environment:**
    - Detect the user's shell. If on Windows → **this is PowerShell**.
    - Use `;` to chain commands, **NEVER** `&&`.
    - Use PowerShell-native syntax for all git, npm, and system commands.
    - If `CODING_STANDARDS.md` has a `## PowerShell Environment` section, its rules are mandatory for the rest of this session.

5. **Calculate Sprint Velocity:**
    - Count `[x]` completed, `[ ]` remaining, `[/]` in-progress from `docs/progress.md`.
    - Completion: `completed / (completed + remaining + in-progress) * 100`

6. **Report — Synthesize, Don't Just List:**

    ```
    CONTEXT RESTORED
    ================
    Project: [name] — [one sentence: what it does]
    Stack: [tech stack summary]
    Context last updated: [date from CODEBASE_CONTEXT.md] ([N days ago])
    ⚠️ STALE: [N] source files changed since last sync — run /sync-context before implementing
    (or ✅ Context is current — no source changes since last sync)
    
    Progress: [████████░░░░░░░░░░░░] 40%  (10/25 items)
    
    CURRENTLY IN PROGRESS:
    → [task name]
       [2-3 sentences explaining what this task is, why it exists, and where it got to]
       Files involved: [list]
       Key decisions made: [any important context from the task notes]
       Still to do: [remaining sub-items]
    
    NEXT UP (if nothing in progress):
    → [first unchecked item with its context summary]
    
    BLOCKERS / BUGS:
    → [any [BUG] items or flags from progress.md, or "None"]
    
    DEVIATIONS FROM SPEC:
    → [count and brief summary, or "None"]
    
    Ready. You don't need to explain anything — I know the project. 
    Tell me what you want to do next.
    ```

    **The stale check:** Run `git log --since="[CODEBASE_CONTEXT Last updated date]" --name-only --pretty=format:"" -- src/ app/ lib/` and filter to source files. If any changed, show the ⚠️ alert. If none, show ✅.

    **The report must read like a human summary, not a file dump.** If someone handed this to a new developer, they should understand the project immediately.
