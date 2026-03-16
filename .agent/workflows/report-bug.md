---
description: Report a bug with full diagnostic context preserved. Captures error messages, steps to reproduce, and affected files so /implement-next has everything needed to fix it.
---

# Report Bug

**Description:** When something is broken, this captures the FULL diagnostic context — error messages, tracebacks, steps to reproduce, expected vs actual behavior, files involved. Optionally investigates the root cause immediately. Stores everything in `progress.md` so `/implement-next` has everything needed to fix it.

> **RULE: This workflow CAPTURES bugs. It does NOT fix them.**
> **Do NOT write, modify, or refactor any source code during this workflow.**
> **After saving the report to progress.md, STOP and suggest `/implement-next`.**

> **Use `/report-bug` instead of `/add-task` when:**
> - You have an error message or traceback
> - The bug needs steps to reproduce
> - You'd lose important context if compressed to one line
> - The bug involves multiple files or systems

## Steps

1. **Capture the Bug:**
    - Let the user describe the problem in their own words — rough is fine.
    - If they paste a traceback, error message, or screenshot description, capture ALL of it.

2. **Extract Structured Context:**
    - From what the user said, extract these fields (skip any that don't apply):
      ```
      BUG REPORT
      ==========
      Summary: [one-line description]
      Error: [exact error message or traceback, if provided]
      Steps to Reproduce: [numbered steps]
      Expected: [what should happen]
      Actual: [what actually happens]
      Files: [files involved, with line numbers if known]
      Frequency: [always / sometimes / first time]
      ```
    - Show the structured report to the user and ask: *"Does this capture the issue? Anything to add?"*

3. **Read Current Progress:**
    - Read `docs/progress.md` to check if the bug is already reported.
    - If a similar bug exists, ask the user if this is the same issue or a new one.

4. **Investigate Root Cause (Optional):**
    - Ask the user: *"Want me to investigate the root cause now, or just save the report for later?"*
    - **If yes — investigate now:**
      1. Read the files mentioned in the bug report.
      2. Trace the execution path from entry point to the error.
      3. Check `CODEBASE_CONTEXT.md` to understand how the failing component interacts with others.
      4. Hypothesize the root cause and validate by reading the code.
      5. Add findings to the report:
         ```
         INVESTIGATION
         =============
         Root Cause: [what's actually wrong]
         Fix: [what needs to change and where]
         Affected Files: [file:line for each change needed]
         Risk: [low/medium/high — does the fix touch other systems?]
         ```
    - **If no — skip to step 5.** The bug is saved for `/implement-next` to pick up later.
    - **After investigation: proceed to Step 5 (save). Do NOT write any fix code. Reading source to understand the bug is allowed. Changing source is NOT.**

5. **Add to progress.md:**
    - If a `## Bug Reports` section doesn't exist, create it.
    - Add the bug with full context as structured sub-items:
      ```markdown
      ## Bug Reports

      - [ ] [BUG] Portal login returns 500 error (2026-02-25)
        - **Error:** `TypeError: a bytes-like object is required` at `src/auth.py:23`
        - **Steps:** Enter username → enter password → click Login
        - **Expected:** Redirect to dashboard
        - **Actual:** 500 error, page hangs
        - **Files:** `portal.py:45`, `src/auth.py:23`
        - **Root Cause:** `bcrypt.checkpw()` receives str instead of bytes — missing `.encode('utf-8')`
        - **Fix:** Add `.encode('utf-8')` to password argument in `auth.py:23`
      ```
    - Root Cause and Fix lines only appear if investigation was done (step 4).
    - The context travels WITH the checkbox. When `/implement-next` picks this up, everything is there.

6. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
