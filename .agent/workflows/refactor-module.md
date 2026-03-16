---
description: Safely refactors code to fix modularity violations without breaking behavior. One violation at a time, with regression protection.
---

# Refactor Module

**Description:** A safety-first refactoring workflow that takes modularity audit findings and fixes them one at a time, with full regression protection and tracking.

> **Golden Rule:** Refactoring changes structure, NEVER behavior. Every test that passed before must pass after.

## Prerequisites

Run `/check-modularity` first to get the violation report. This workflow fixes what that workflow finds.

## Steps

1. **Read Violation Report:**
    - Read the modularity audit results (from the user or from the last `/check-modularity` run).
    - List all violations by severity: file length > function length > class length > layer violations.
    - Pick the **single highest-priority violation** to fix first.

2. **Run Pre-Refactor Baseline:**
    - Run the FULL test suite. Record exact pass/fail count.
    - **This is your safety net.** If tests are already failing, fix those FIRST before refactoring.
    - Store baseline: `X tests passed, 0 failed`

3. **Plan the Refactor (show to user):**
    - For each violation type, apply the standard fix:

    **File too long (>250 lines):**
    - Identify logical groupings within the file.
    - Plan which functions/classes move to which new file.
    - Plan import updates in all files that reference moved code.

    **Function too long (>40 lines):**
    - Identify extractable blocks (loops, conditionals, data transformations).
    - Name the helper functions after what they DO, not what they contain.

    **Class too long (>180 lines):**
    - Identify if it's doing multiple jobs (SRP violation).
    - Plan extraction into mixin or helper class.

    **Layer violation:**
    - Identify the misplaced logic and its correct home.
    - Plan the move with minimal API surface change.

    Present to user:
    ```
    REFACTOR PLAN
    =============
    Violation: [file/function/class] in [path] ([X lines], limit [Y])
    
    Action: [what will change]
    Files affected: [list]
    Public API changes: NONE (if any, explain why)
    
    Approve? [yes/no]
    ```

    > **RULE: Never refactor without user approval.**

4. **Execute the Refactor:**
    - Apply changes incrementally — one logical step at a time.
    - After EACH step, verify the code at least parses/compiles.
    - **NEVER change function signatures, return types, or public APIs** unless explicitly approved.
    - Update all imports that reference moved code.

5. **Run Post-Refactor Regression:**
    - Run the FULL test suite again.
    - Compare against baseline:
      - ✅ **Same pass count, 0 failures** → refactor is safe
      - ❌ **Any new failure** → STOP. Undo the change. Investigate.
    - Show result:
    ```
    REFACTOR VERIFIED ✅
    Before: X passed, 0 failed
    After:  X passed, 0 failed
    No behavior change detected.
    ```

6. **Log the Refactor:**
    - Add entry to `docs/progress.md` under `## Refactoring Log`:
    ```
    | Date | File | Violation | Action | Tests |
    |------|------|-----------|--------|-------|
    | 2026-02-24 | module.py (312→180+132) | File too long | Split into module.py + module_helpers.py | 45/45 ✅ |
    ```
    - If the section doesn't exist, create it.

7. **Git Commit:**
    - Use commit type `refactor`: `refactor(scope): split oversized module into focused files`
    - Present to user for approval (same flow as `/implement-next`).
    - On approval: `git add . ; git commit -m "refactor(scope): message" ; git push`

8. **Next Violation or Done:**
    - If more violations remain: *"Fixed 1 of N violations. Continue with the next one?"*
    - If all fixed: *"All violations resolved. Run `/check-modularity` to verify clean report."*

9. **Suggest Next:** Read `PIPELINE.md` and suggest the next workflow.
