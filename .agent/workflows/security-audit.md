---
description: Scans for security vulnerabilities, hardcoded secrets, and unsafe patterns.
---

# Security Audit

## Steps

1. **Scan for Secrets:**
    - `grep_search` for API keys, passwords, tokens in source files.
    - Check `.env` files aren't committed.
    - Verify `.gitignore` covers secrets.

2. **Check Dependencies:**
    - Look for known vulnerable packages.
    - Check for outdated dependencies.

3. **Check Input Validation:**
    - Verify all user inputs are validated/sanitized.
    - Check for SQL injection, XSS, CSRF vulnerabilities.

4. **Check Auth & Access Control:**
    - Verify authentication on all endpoints.
    - Check authorization (who can access what).

5. **Check Deployment Security (if `docker-compose.prod.yml` exists):**
    - Read `CODING_STANDARDS_DOMAIN.md` (or `CODING_STANDARDS.md` if unsplit) `§ Public Demo Security` for the expected protections.
    - Verify each layer:
      - [ ] Rate limiting middleware exists on API routes
      - [ ] Usage cap mechanism exists (in-memory counter, Redis, or DB-backed)
      - [ ] No API keys in frontend code or client bundles (`grep_search` for key patterns in `src/`, `public/`, `app/`)
      - [ ] Input length limits on user-facing endpoints
      - [ ] Error responses don't leak stack traces or internal paths (check error handlers)
      - [ ] Production build has no source maps (`find_by_name` for `*.map` files in build output)
      - [ ] CORS configuration is not wildcard `*` (`grep_search` for `cors` and `*`)
      - [ ] Docker resource limits are set in `docker-compose.prod.yml` (`deploy.resources.limits`)
      - [ ] `.env.example` exists and matches env vars used in code
      - [ ] `.env` is in `.gitignore`
    - For each check: report ✅ pass, ❌ fail, or ⚠️ not applicable.
    - **Failures in this step are severity: HIGH** — public exposure + cost risk to VPS.

6. **Report:** Present findings with severity ratings (critical/high/medium/low).

7. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
