---
description: Emergency hotfix for production issues — bypasses normal /add-task → /implement-next cycle
---

# /hotfix — Emergency Production Fix

> **When to use:** A production bug that can't wait for the normal `/report-bug → /implement-next` cycle.
> **When NOT to use:** Feature work, non-urgent bugs, or improvements. Use `/add-task` for those.

---

## Steps

### 1. Understand the Emergency
Read the user's description of the production issue.
- What is broken?
- What is the impact? (data loss, service down, users blocked)
- When did it start? (deploy-related or time-triggered)

### 2. Read Relevant Code
// turbo
Search for and read the files most likely to contain the bug.
- Read error logs/stack traces if provided
- Read the file(s) where the failure occurs
- Read recent git history for that file (`git log -5 --oneline -- [file]`)

### 3. Identify the Fix
Produce a **one-line diagnosis** and a **minimal fix plan**.
- The fix should be the smallest possible change that resolves the issue
- Do NOT refactor, improve, or clean up unrelated code
- If the root cause is complex, fix the symptom now and log a follow-up task

### 4. Implement the Fix
Apply the fix. Then:
- Write a **targeted test** that reproduces the bug and verifies the fix
- Run the **full regression suite** — hotfixes must not break other things

```
[Run project test command]
```

> [!CAUTION]
> If regression tests fail, STOP. Fix the regression before proceeding. A hotfix that breaks other things is worse than the original bug.

### 5. Commit with Hotfix Convention
```
git add .
git commit -m "hotfix(scope): [description of what was fixed]"
```

The commit message must:
- Use the `hotfix()` prefix — this makes hotfixes searchable in git history
- Describe what was fixed, not what was wrong
- Reference the error/ticket if one exists

### 6. Post-Hotfix Cleanup
Tell the user:

> **Hotfix deployed.** To keep docs in sync:
> 1. Run `/sync-context` — updates CODEBASE_CONTEXT.md with the fix
> 2. Run `/add-task` if there's a deeper root cause that needs a proper fix later
> 3. Continue normal development with `/implement-next`

---

## Guardrails

- **No scope creep.** Fix only the reported issue. Log everything else as follow-up tasks.
- **Regression required.** Never commit a hotfix without running the full test suite.
- **Document what was skipped.** If you skipped the normal planning/TDD cycle, note it in the commit body so `/sync-context` can catch up.
