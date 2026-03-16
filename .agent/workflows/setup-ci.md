---
description: Generates GitHub Actions CI/CD config from actual codebase. Run after /validate-prd when all features are built. Deploys to DigitalOcean VPS (default) or Railway.
---

# Setup CI/CD — Generate from Codebase

> Run this AFTER all features are implemented and `/validate-prd` passes. The CI config is generated from the actual codebase, not the PRD.

## Prerequisites
- All progress items are `[x]` or this is a deliberate early setup
- `/validate-prd` has passed
- GitHub repo exists and `gh` CLI is authenticated (`gh auth status`)

---

## Steps

1. **Detect Tech Stack:**
    - Read `package.json` → Node.js/npm scripts (test, lint, build)
    - Read `tsconfig.json` → TypeScript project (add type-check step)
    - Read `requirements.txt` / `pyproject.toml` → Python project
    - Read `go.mod` → Go project
    - If none found → ask user what stack they're using

2. **Detect Services:**
    - Read `docker-compose.yml` → running services (postgres, redis, etc.)
    - Read `.env.local` → service URLs that need secrets
    - Read config files → Supabase, Firebase, external APIs
    - Build a **services list** with what CI needs to replicate

3. **Detect Test Runner:**
    - `jest.config.*` / `vitest.config.*` → Jest/Vitest
    - `pytest.ini` / `pyproject.toml [tool.pytest]` → pytest
    - `go test` → Go tests
    - Note the exact test command (e.g., `npm run test`, `pytest`, `go test ./...`)

4. **Detect Deployment Target:**
    - Check `CODING_STANDARDS_DOMAIN.md` (or `CODING_STANDARDS.md` if unsplit) for deployment platform section
    - Check if `docker-compose.prod.yml` exists → **DigitalOcean VPS** deployment (SSH + docker compose)
    - **Default: DigitalOcean VPS** (portfolio projects) — `ssh` → `git pull` → `docker compose up -d`
    - **Client projects: Railway** — use `railway up` or Railway's GitHub integration
    - If PRD specifies different platform → use that instead
    - If frontend is on Vercel → note Vercel auto-deploys from GitHub (no CI step needed)

5. **Generate `.github/workflows/ci.yml`:**

    ```yaml
    name: CI/CD
    
    on:
      pull_request:
        branches: [main]
      push:
        branches: [main]
    
    jobs:
      test:
        runs-on: ubuntu-latest
        # Add services: block for detected databases
        steps:
          - uses: actions/checkout@v4
          - # Setup step (setup-node, setup-python, setup-go)
          - # Install dependencies
          - # Lint
          - # Type check (if TypeScript)
          - # Run full test suite
    
      deploy:
        needs: test
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - # Deploy to DigitalOcean VPS via SSH (or Railway/detected platform)
          # For VPS: ssh user@vps 'cd /apps/project && git pull && docker compose -f docker-compose.prod.yml up -d --build'
          # For Railway: railway up
    ```

    **Adapt the template above based on detected stack.** Do NOT leave placeholder comments — fill in the actual commands.

6. **Set VPS GitHub Secrets (if VPS deployment detected):**
    - Detect the GitHub remote: `git remote get-url origin` → extract `owner/repo`
    - Check if `gh` CLI is authenticated: `gh auth status`
    - Auto-set the 3 VPS secrets:
      ```powershell
      $repo = "OWNER/REPO"  # extracted from git remote
      gh secret set VPS_HOST --repo $repo --body "104.248.137.96"
      gh secret set VPS_USER --repo $repo --body "deploy"
      Get-Content "$env:USERPROFILE\.ssh\id_ed25519" -Raw | gh secret set VPS_SSH_KEY --repo $repo
      ```
    - If `gh` is not installed or not authenticated → fall back to listing the secrets for manual setup
    - Report: `✅ VPS secrets set for $repo` or `⚠️ Set these secrets manually: VPS_HOST, VPS_USER, VPS_SSH_KEY`

7. **List Additional GitHub Secrets:**
    - Parse `.env.local` for any values that CI/deploy needs beyond VPS
    - Output a clear list for any remaining secrets:
      ```
      ⚠️ Add these additional secrets in GitHub → Settings → Secrets:
      - DATABASE_URL: Your production database URL
      - (etc.)
      ```
    - If Vercel is used → note `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

8. **Create the workflow file and commit:**
    - Write `.github/workflows/ci.yml`
    - Commit: `ci: add CI/CD pipeline for [stack]`
    - Do NOT push yet — let the user verify secrets are set

9. **Demo Security Warning (if paid APIs detected):**
    - If `.env.example` contains `DEMO_MODE`, `OPENROUTER`, `OPENAI`, `ANTHROPIC`, `STRIPE`, or any paid API key variable:
      ```
      ⚠️ DEMO SECURITY REMINDER
      This project uses paid external APIs. Before deploying to the public VPS:
      1. Verify rate limiting is implemented on all API routes
      2. Verify usage caps are enforced (5/day for expensive operations)
      3. Verify no API keys are exposed in frontend bundles
      4. Verify CORS is locked to the demo domain
      See CODING_STANDARDS_DOMAIN.md (or CODING_STANDARDS.md if unsplit) § Public Demo Security for the full checklist.
      Run /security-audit to verify all protections are in place.
      ```

10. **Report and suggest next:**
    - Show what was generated
    - Show VPS secret status (✅ auto-set or ⚠️ manual)
    - Show any additional secrets needed
    - Suggest: *"CI configured. Push to trigger your first run. If it fails, run `/fix-ci`."*
    - **Next workflow: `/security-audit`**
