---
description: Automatically pulls CI error logs, fixes issues locally, pushes, and monitors until green. Uses gh CLI. Max 5 retries.
---

# Fix CI — Automated Error-Fix-Push-Monitor

> Run this when CI fails. It pulls the error log, fixes the issue, pushes, and monitors the next run until green.

## Prerequisites
- GitHub CLI authenticated (`gh auth status`)
- Git repo has a remote and CI workflow exists (`.github/workflows/ci.yml`)
- You are on the correct branch (`dev` or a feature branch)

---

## Steps

1. **Check CI Status:**
    ```bash
    gh run list --limit 5
    ```
    - If **all passing** → "CI is green ✅. Nothing to fix. Run `/implement-next` to continue."
    - If **in progress** → "CI is still running ⏳. Wait for it to complete, then re-run `/fix-ci`."
    - If **failed** → proceed to step 2

2. **Pull Error Log:**
    ```bash
    gh run view <failed-run-id> --log-failed
    ```
    - Parse the output to identify:
      - **Which job failed** (test, lint, type-check, deploy)
      - **Which file/line** caused the failure
      - **The error message**
    - If the log is too long, focus on the FIRST error — cascading failures are usually caused by one root issue

3. **Diagnose the Error:**
    - Read the failing file(s) locally
    - Categorize the error:
      - **Test failure** → a test is failing that passes locally (environment difference)
      - **Lint error** → code style issue
      - **Type error** → TypeScript/type issue
      - **Build error** → dependency or compilation issue
      - **Deploy error** → deployment config or secrets issue
      - **Service error** → CI service container not configured correctly

4. **Fix Locally:**
    - Apply the fix following `CODING_STANDARDS.md`
    - **For test failures:** Run the failing test locally to reproduce, then fix
    - **For lint/type errors:** Run the same linter/checker locally
    - **For build errors:** Run the build command locally
    - **For deploy errors:** Check deployment config — may need user input for secrets
    - **For service errors:** Check `.github/workflows/ci.yml` service container config

5. **Verify Locally:**
    - Run the EXACT same command that failed in CI:
      - Test: `npm run test` / `pytest` / `go test ./...`
      - Lint: `npm run lint`
      - Type check: `npx tsc --noEmit`
      - Build: `npm run build`
    - **Do NOT push until the local check passes**
    - If it passes locally but fails in CI → likely an environment/secrets issue. Flag to user.

6. **Commit and Push:**
    ```bash
    git add .
    git commit -m "fix(ci): [one-line description of what was fixed]"
    git push
    ```

7. **Monitor the New Run:**
    - Wait for the new CI run to start:
      ```bash
      gh run list --limit 1
      ```
    - Poll every 30 seconds until it completes (max wait: 15 minutes)
    - Show progress: "Run #42: ⏳ in_progress (2m30s elapsed)"

8. **Evaluate Result:**
    - **If passing ✅:**
      - "CI is green! Run #42 passed in 3m15s."
      - Suggest next workflow from PIPELINE.md
    - **If failed ❌:**
      - Increment retry counter
      - If retries < 5 → "Still failing. Attempt 2/5. Pulling new error log..."
      - Go back to Step 2
      - If retries >= 5 → **STOP**:
        ```
        ⛔ CI has failed 5 times. This may require manual investigation.
        Last error: [error summary]
        Failing step: [step name]
        Suggestion: Check GitHub Secrets, service configs, or environment differences.
        ```

---

## Safeguards

- **Max 5 retries** — prevents infinite loops
- **Local verification before push** — never pushes blind fixes
- **Deploy errors require user input** — if secrets are missing, don't guess. Ask user.
- **Branch awareness** — confirms which branch CI ran on (`dev` vs `main` vs feature)
