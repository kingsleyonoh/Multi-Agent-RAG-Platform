---
description: Reads your PRD and validates the finished product against Section 15 success criteria, Section 5 user journeys, and progress.md cross-checks. Run after all progress items are complete, before /security-audit.
---

# Validate PRD — Acceptance Testing

**Description:** After all `progress.md` items are `[x]`, verify the finished product against the PRD. Uses the browser subagent for live UI checks, direct calls for API/data checks, and doc comparison for coverage analysis. Soft gate — reports results, flags failures, lets you decide.

> **Use this when:** All items in `progress.md` are marked complete and you're preparing to ship. This is the quality gate between implementation and `/security-audit`.

> **PRD-only workflow.** If the project has no PRD with Section 15 (Success Criteria), exit immediately with: *"No PRD found. This workflow requires a PRD with Section 15 (Success Criteria)."*

// turbo-all

---

## Steps

1. **Validate PRD Exists:**
    - Search for PRD files in `docs/` — look for any file matching `*PRD*` or `*prd*`.
    - If no PRD exists → stop with: *"No PRD found. This workflow requires a PRD with Section 15 (Success Criteria)."*
    - If found, open it and confirm **Section 15 (Success Criteria)** exists.
    - If Section 15 is missing → stop with: *"PRD found but Section 15 (Success Criteria) is missing. Add acceptance criteria to your PRD first."*

2. **Read PRD Sections:**
    - Read **Section 15** (Success Criteria) — extract every checkbox/criterion.
    - Read **Section 5** (Module Specs) — extract module definitions, inputs, and outputs.
    - Read **Section 9** (Dependency Hierarchy) — extract module-to-module dependencies.

3. **Read Progress Tracker:**
    - Open `docs/progress.md`. Confirm all items are `[x]`.
    - If unchecked items remain → warn: *"⚠️ [N] items are still incomplete in progress.md. Results may be partial. Continue anyway?"*
    - Wait for user confirmation before proceeding.

4. **Get Dev Server URL:**
    - Check `.agent/rules/CODEBASE_CONTEXT.md` Commands section for a dev server command.
    - If found → use it. If not → ask user: *"What URL is your dev server running on? (e.g., http://localhost:3000)"*
    - Store the URL for browser subagent steps.

5. **Start Dev Server:**
    - If the dev server is not already running, start it using the command from Step 4.
    - Wait for it to be ready before proceeding.

6. **Layer 1 — Success Criteria (Section 15):**

    For each criterion in Section 15, classify and verify:

    - **Browser-testable** (user can do X and see Y):
      - Use the browser subagent to navigate to the live dev server URL.
      - Follow literal instructions derived from the criterion.
      - Example: "User can create an account and see the dashboard" → navigate to `/register`, fill signup form, submit, expect redirect to `/dashboard`.
      - Record: ✅ pass or ❌ fail with error details.

    - **Measurable without browser** (API returns X, data appears in DB, script runs):
      - Execute the check directly (HTTP request, DB query, script execution).
      - Record: ✅ pass or ❌ fail with error details.

    - **Not automatable** (design approval, client sign-off, subjective quality):
      - Flag as: ⚠️ manual check needed.

7. **Layer 2 — User Journeys (Sections 5 + 9):**

    Build 2-3 realistic end-to-end user journeys by chaining connected modules:

    - From Section 5, identify which modules produce outputs that feed into other modules' inputs.
    - From Section 9, follow the dependency hierarchy to build logical chains.
    - Run each journey through the browser subagent (if UI-based) or direct API calls (if backend-only).
    - Record each step: ✅ pass or ❌ fail with the step number and error details.

    > Not random E2E coverage — specifically the paths the PRD describes as the core system.

8. **Layer 3 — Progress Cross-Check:**

    No browser needed — pure doc comparison:

    - Every `[x]` in `progress.md` → maps to a PRD section?
    - Every Section 13 (Build Phases) checkbox → has a corresponding `[x]` in `progress.md`?
    - Any `progress.md` items marked done but NOT validated in Layer 1 or Layer 2?
    - Record mismatches and gaps.

9. **Present Full Report:**

    ```
    PRD VALIDATION REPORT
    =====================
    Project: {name}        Date: {today}
    PRD: docs/{file}.md    Dev Server: {url}

    SUCCESS CRITERIA (Section 15)
      ✅ {criterion description} — verified via browser
      ✅ {criterion description} — verified via request
      ❌ FAILED: {criterion description} — {error details}
      ⚠️  {criterion description} — manual check needed

    USER JOURNEYS
      ✅ {journey name} ({N} steps, {time})
      ❌ {journey name} (failed at step {N}: {error})

    PROGRESS CROSS-CHECK
      ✅ {N}/{N} PRD Build Phase items matched in progress.md
      ✅ {N}/{N} progress.md items marked complete
      ⚠️  {N} item(s) marked done but not validated (manual criterion)

    VERDICT: {N} failures, {N} manual checks needed
    Recommended: fix failures before /security-audit
    ```

10. **Soft Gate:**
    - If failures exist → *"{N} failures found. Fix them and re-run `/validate-prd`, or proceed to `/security-audit` if failures are known and accepted."*
    - If all pass → *"All criteria validated ✅. Run `/security-audit` to continue."*

11. **Suggest Next:** Read `PIPELINE.md` and suggest the next workflow.
