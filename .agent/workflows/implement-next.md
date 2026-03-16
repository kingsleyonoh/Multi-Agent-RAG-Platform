---
description: Picks the next unimplemented item from docs/progress.md, implements it with TDD, runs full regression tests, updates the tracker, and syncs deviations.
---

# Implement Next Item

## Full Read Rule

> **Every "read" instruction in this workflow means: read the ENTIRE file from first line to last line.** If the file is longer than your read limit, make multiple sequential calls (e.g., lines 1–200, 201–400, 401–end) until every line has been read. Never read a partial subset and assume you understand the file.

## Steps

1. **Read Progress Tracker (FULL READ):**
    - Open `docs/progress.md`. Read the ENTIRE file — every phase, every item, every sub-item.
    - Find the first unchecked `- [ ]` item.
    - Read its full context — sub-items, affected files, decisions, edge cases.
    - Tell the user: *"Next item: [description]. Ready to implement?"*

2. **Read the Spec (FULL READ — adapt to project type):**

    **If a PRD exists:**
    - Read the ENTIRE PRD — every section, top to bottom. If 500+ lines, read in multiple passes.
    - Find the section that defines this item and extract exact requirements.
    - Also note: Architecture Principles, Project Structure, and What NOT to Build — these constrain your approach.

    **If NO PRD exists (mature/retrofitted project):**
    - The spec IS the enriched task in `progress.md` — the context sub-items, affected files, and decisions written by `/add-task` and `/clarify`.
    - Read `CODEBASE_CONTEXT.md` in full to understand the architecture around this task.
    - Skip searching for a PRD section — the detail is already in the task.

3. **Read Relevant Code (FULL READ — BEFORE planning):**
    - Check KI summaries for relevant architectural decisions or known gotchas that apply to this task area.
    - **Check Skills:** Scan your available skills list for domain matches (e.g., database → `postgresql`, API → `fastapi-templates`). If a match exists, read its `SKILL.md` now. **The skill's exact patterns STRICTLY OVERRIDE your pre-trained knowledge.** Tell the user: *"Using skill: [name] for this task."*
    - Read `.agent/rules/CODING_STANDARDS.md` in full — every line, every rule. Also read `CODING_STANDARDS_TESTING.md` and `CODING_STANDARDS_DOMAIN.md` if they exist.
    - **Read Shared Foundation files:** Open the **Shared Foundation** table in `CODEBASE_CONTEXT.md` and read every file listed there **in full**. These define the project's shared patterns. Before writing any new utility, helper, middleware, handler, or shared module — check these files first. **Never recreate what already exists.**
    - Read the source files listed in the task's context sub-items — each file in full.
    - If no files are listed, identify and read the relevant modules based on the task description.
    - For `[BUG]`: read the file where the bug occurs, trace the stack.
    - For `[FIX]`: read the files that will be modified.
    - For `[FEATURE]`: read related modules, DB schema, and existing patterns for similar features.
    - **You CANNOT create a plan without reading the code first.** The plan is an OUTPUT of understanding.

4. **Create Implementation Plan (MANDATORY — scaled to actual complexity):**

    **Scale the plan to the task, not the label.** A simple feature may need 3 lines. A complex bug spanning multiple systems may need a full investigation. Use your judgment:

    - **Simple tasks** (one file, clear fix): State what you'll change and why. Present inline → approve → go.
    - **Medium tasks** (multiple files, some design decisions): Write the plan as a formal **Implementation Plan artifact** — use `file:///` links for referenced files, group changes by component, include a Verification Plan section. Present via `notify_user` with `BlockedOnUser: true` → approve → go.
    - **Complex tasks** (new systems, cross-cutting concerns, architectural): Full Implementation Plan artifact — files to create/modify, approach, test plan, edge cases, `> [!WARNING]` alerts for breaking changes. Present → approve → consider `/finalize-plan` first.

    **For `[BUG]` items:** If filed via `/report-bug`, the diagnostic context is already in `progress.md`. Read it, identify root cause, state the fix. If context is thin, investigate first.

    > **RULE: Never write a single line of code before the user approves the plan.**

    **After approval:** Did the user make significant changes to the plan? (Changed approach, added/removed files, changed test strategy — not just wording.) If yes, log it immediately:
    ```
    | [today] | plan | [task name] | [original approach] | [changed to] | [user's reason] |
    ```
    Minor clarifications don't count. Significant redirects do.

5. **Write Tests FIRST (Red Phase — MANDATORY GATE):**

    **⚠️ REFACTORING EXCEPTION:** If this is a `[FIX]` item that is **pure refactoring** (changing code structure without changing behavior):
    - Skip writing new tests — the existing tests ARE your safety net.
    - Run the FULL existing test suite FIRST → confirm it passes (baseline).
    - Refactor the code.
    - Run the FULL test suite AGAIN → confirm everything still passes.
    - If anything fails → the refactoring broke behavior. Fix it or revert.
    - **This exception ONLY applies to pure refactoring.** If the task adds any new behavior, even during a refactor, you MUST write new tests for that behavior.

    **For all other tasks (features, bugs, fixes with new behavior):**
    - Write failing tests covering the feature's behavior, edge cases, and integration.
    - **Tests MUST run against local dev services** (local Supabase, local DB) — NOT mocks. See Mock Policy in `CODING_STANDARDS.md`.
    - **Coverage checklist (ALL must be checked before proceeding):**
      - [ ] Happy path covered?
      - [ ] At least 2 edge cases covered?
      - [ ] Error/failure path covered?
      - If any ❌ → write those tests now.
    - **Run the tests NOW.** They MUST fail. If they pass, your tests aren't testing anything — rewrite them.
    - **⛔ RED PHASE EVIDENCE (MANDATORY — cannot proceed without this):**
      Present this to the user before writing ANY implementation code:
      ```
      RED PHASE EVIDENCE
      ===================
      Test files created:
        - [path/to/test_file] ([X] tests)
        - [path/to/test_file2] ([Y] tests)

      Test run output:
        [paste actual test runner output showing failures]

      Total: [N] tests, [N] FAILED, 0 passed
      Running against: [local Supabase / local Postgres / etc.]
      ```
    - **⛔ Do NOT proceed to Step 6 until RED PHASE EVIDENCE is shown.**
    - **⛔ If you find yourself writing implementation code without having shown RED PHASE EVIDENCE, STOP. Delete the implementation. Go back to Step 5.**

6. **Implement (Green Phase):**
    - Write minimum code to make all new tests pass.
    - Follow `CODING_STANDARDS.md`.
    - Run the SAME tests from Step 5 — **they MUST now pass.**
    - **⛔ GREEN PHASE EVIDENCE (MANDATORY):**
      ```
      GREEN PHASE EVIDENCE
      =====================
      Tests from Red Phase: [N] total
      Now passing:          [N] ✅
      Delta:                [N] failures → 0 failures
      ```

7. **Run FULL Regression Suite:**
    - Run ALL tests across the entire project.
    - **If anything fails:** fix it. Run again. Repeat until 100% green.
    - **Only proceed when full suite is green.**
    - **⛔ REGRESSION EVIDENCE (MANDATORY):**
      ```
      REGRESSION SUITE
      =================
      New tests added:     [X]
      Pre-existing tests:  [Y]
      Total:               [Z]
      All passing:         ✅
      ```
    - **⛔ If "New tests added" = 0, STOP.** You skipped TDD. Go back to Step 5.
    - **If regression failures reveal a deeper issue:**
      - If the failure is in your new code → fix and re-run (normal flow).
      - If the failure reveals a **design conflict** (your approach conflicts with existing architecture, or the spec contradicts existing behavior):
        1. STOP implementation.
        2. Log the conflict to the user with evidence (failing tests, conflicting code).
        3. Return to Step 4 with a revised plan that addresses the conflict.
        4. Get user approval on the revised plan before resuming.
        5. Log as a deviation: `| [date] | plan | [task] | [original approach] | [revised] | Regression conflict |`
      - Never force a fix that breaks existing functionality to satisfy new tests.

7b. **Verify UI (if applicable):**
    - If this task has a visual component (page, component, form, dashboard):
      - Use the browser subagent to navigate to the affected page.
      - Verify the UI renders correctly and capture a screenshot.
    - If the project has no UI → skip this step.

8. **Handle Deviations:**
    - If user requests a change from the spec, ask to update the spec (or progress.md for non-PRD projects).
    - Log deviation in `docs/progress.md` Deviations Log using the correct type:
      - `spec` — implementation differs from PRD/spec
      - `plan` — user changed the AI's plan before approval (do this immediately after approval, not here)
      - `scope` — the task scope expanded or narrowed from the original request

9. **Update Tracker:** Mark `- [ ]` → `- [x]` in `docs/progress.md`.

9.25. **Update Shared Foundation (if applicable):**
    - Review the files you created or significantly modified in this task.
    - If any file is a **shared, cross-cutting concern** — used (or intended to be used) by multiple modules — add it to the **Shared Foundation** table in `CODEBASE_CONTEXT.md`.
    - Examples: error handler, DB client, API client, auth middleware, config loader, shared types/interfaces, base components, utility modules, shared styles, validation helpers.
    - Format: `| Category | File path | What it establishes |`
    - If the file is task-specific and only used by one module → do NOT add it.
    - This keeps the Shared Foundation table current as the project grows.

9.5. **Create/Update Walkthrough (medium/complex tasks only):**
    - Create or update a Walkthrough artifact documenting:
      - Changes made and approach taken
      - Tests run and results
      - Screenshots/recordings if UI was verified in Step 7b
    - Simple tasks → skip.

10. **Git Commit (after all tests green):**
    - Generate a commit message following the Git Commit Convention in `CODING_STANDARDS.md`.
    - Map task type to commit type: `[FEATURE]` → `feat`, `[BUG]` → `fix`, `[FIX]` → `fix` or `refactor`.
    - Present the commit to the user:
      ```
      ALL TESTS GREEN ✅ (X passed, 0 failed)
      
      Proposed commit:
      feat(scope): descriptive message
      
      Files changed: [list]
      
      Approve commit and push? [yes/no]
      ```
    - On approval: run `git add . ; git commit -m "type(scope): message" ; git push`
    - **Never commit without user approval.**

11. **Suggest Next:** Read `PIPELINE.md` and suggest the next workflow. If ALL items in `progress.md` are now `[x]`, suggest `/validate-prd` to run PRD acceptance testing.
