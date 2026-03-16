# Retrofit Existing Codebase — Full Guide

**Description:** When you have an existing project that wasn't started with the workflow system and you want to bring it in. This is the reverse of `/bootstrap` — instead of generating code from a PRD, it generates docs from existing code.

**Also handles syncing:** If the project already has `.agent/`, this workflow updates its rules, workflows, and coding standards to match the latest project template. The template is a living document — it evolves as new issues are discovered.

> **Use this when:** You have a codebase with no `.agent/`, no `progress.md`, no `CODING_STANDARDS.md`, and you want the full workflow system running on it. OR you want to sync an existing project with the latest template.

## Prerequisites

- The project must be a git repository.
- You should have the project open as your workspace.

// turbo-all

---

## Phase 0: Sync Mode (When `.agent/` Already Exists)

**If `.agent/rules/CODING_STANDARDS.md` already exists, execute ONLY this phase, then skip to Phase 4 Verify.**

This phase brings the project up to date with the latest template. The project template is a living document — new rules, new workflow improvements, and new sections get added over time. This ensures every project stays current.

**0a.** Read the project's current rules files:
```
.agent/rules/CODING_STANDARDS.md
.agent/rules/CODING_STANDARDS_TESTING.md (if exists)
.agent/rules/CODING_STANDARDS_DOMAIN.md (if exists)
```

**0b. Rules File Migration (if needed):**
Check if ANY rules file in `.agent/rules/` exceeds 10,000 characters:
```powershell
Get-ChildItem ".agent\rules\*.md" | ForEach-Object { $chars = (Get-Content $_.FullName -Raw).Length; if($chars -gt 10000) { Write-Host "⛔ SPLIT NEEDED: $($_.Name) = $chars chars" } }
```

If ANY file exceeds 10,000 characters, perform an **in-place split**:
1. Read the oversized file completely
2. Identify `##` section headers as split points
3. Group sections into logical chunks, each under 10,000 characters:
   - For `CODING_STANDARDS.md`: core rules → `CODING_STANDARDS.md`, testing → `CODING_STANDARDS_TESTING.md`, domain/production → `CODING_STANDARDS_DOMAIN.md`
   - For `CODEBASE_CONTEXT.md`: core → `CODEBASE_CONTEXT.md`, database → `CODEBASE_CONTEXT_SCHEMA.md`, modules → `CODEBASE_CONTEXT_MODULES.md`
4. **Preserve ALL project-specific content** — this is a split, not a rewrite
5. Add cross-reference headers to each new file (e.g., `> Part 1 of 3. Also loaded: ...`)
6. Verify each resulting file is under 10,000 characters
7. Log the split in the project's CHANGELOG: `chore(rules): split oversized rules files for 12K limit compliance`

**0c. Workflow Guides Migration (if needed):**
Check if the template now uses the stub+guide pattern for any workflows. If the template has `.agent/guides/` with guide files:
1. Create `.agent/guides/` in the project if it doesn't exist
2. Copy guide files from the template
3. Replace workflow files with stubs (customized for the project)
4. Add `.agent/guides/` to `.gitignore` if not already present

**0d.** Read the template's latest rules files:
```
C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\.agent\rules\CODING_STANDARDS.md
C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\.agent\rules\CODING_STANDARDS_TESTING.md
C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\.agent\rules\CODING_STANDARDS_DOMAIN.md
```

**0e.** **Compare and merge — section by section.** For each universal section in the template:
- If the section **does NOT exist** in the project → **add it** (customized for the project's tech stack)
- If the section **exists but has FEWER rules** than the template → **merge the missing rules in**
- If the section **exists and matches** → leave it alone
- **NEVER remove project-specific sections** (commands, file conventions, component patterns, etc.)

Universal sections to check (ALL are mandatory):
1. Workflow Pipeline Awareness
2. Skill Selection & Orchestration (principle-based — no hardcoded table)
3. Git Commit Convention
4. AI Discipline Rules (all sub-rules, including Workflow Discipline, Use Skills When Available (Skills > Pre-trained Knowledge), Full Read Rule, Read Shared Foundation Before Coding)
5. Production-Readiness Rules
6. File Size Limits
7. Testing Rules — Anti-Cheat
8. Test Quality Checklist (10-category table)
9. Edge Case Coverage Guide
10. Test Modularity Rules
11. Business-Context Testing
12. PowerShell Environment
13. Deployment Platform
14. Public Demo Security
15. Environment Variables

**0f.** **Sync workflow files using the CHANGELOG as your guide.** Do NOT try to diff every file manually — that approach is unreliable. Instead:

  1. **Read the project's `Template synced` date** from `.agent/rules/CODEBASE_CONTEXT.md` header.
     - If the field doesn't exist or says `{{DATE}}` → treat as "never synced" and apply ALL changelog entries.
  
  2. **Read the template's CHANGELOG:**
     ```
     C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\CHANGELOG.md
     ```
  
  3. **Find all entries ON OR AFTER the project's `Template synced` date.** Each entry lists the specific files that changed and what changed in them. Using "on or after" (inclusive) ensures same-day template updates are not missed.
  
  4. **For each changed file listed in the CHANGELOG:**
     - Read the **template version** of that specific file
     - Read the **project version** of that same file
     - Apply the specific change described in the CHANGELOG to the project version
     - Preserve all project-specific customizations (paths, commands, framework references)
  
  5. **For files NOT mentioned in the CHANGELOG** → skip entirely. They haven't changed.
  
  6. **Copy any NEW workflow files** that exist in the template but not in the project (these will appear as "Added" in the CHANGELOG).
  
  7. **Update the `Template synced` date** in the project's CODEBASE_CONTEXT.md to today.

  > **Why this works:** The CHANGELOG tells you EXACTLY what changed and where. You don't have to guess whether "project file is bigger because of customizations" means "nothing changed" or "template added new content." The CHANGELOG is the single source of truth for what's new.

- **NEVER overwrite project-specific customizations** (test commands, directory paths, framework references)

**0g.** **Check for new rules files.** List all files in:
```
C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\.agent\rules\
```
- If any rules file exists in the template but NOT in the project → copy it and customize

**0g-new.** **Merge missing sections into existing rules files.** For each rules file that exists in both template AND project:
- Read both versions
- For each section in the template version that is NOT present in the project version → add it
- Specifically: if `CODEBASE_CONTEXT.md` is missing `## Deep References` → add the section with placeholder rows
- Specifically: if `CODEBASE_CONTEXT.md` is missing `## Shared Foundation` → add the section with the empty table
- **NEVER remove project-specific content already in the file**
- This handles the "file exists but section is missing" case — which affects all projects synced before new template sections were added

**0g-git.** **Check `.gitignore` for workflow protection.** If `.gitignore` exists but does NOT contain `.agent/workflows/` OR does NOT contain `.agent/guides/`, append the full mandatory block (skip lines that already exist):
```
# AI Workflow System (proprietary — do not publish)
.agent/workflows/
.agent/guides/

# Internal project planning
docs/progress.md
docs/*PRD*.md
docs/*prd*.md
```
If `.gitignore` does not exist, create one with the mandatory block. `.agent/rules/` is NOT excluded — helps forkers. This catches projects set up before this feature existed.

**0g-deploy.** **Check for deployment config files.** If any of these are missing from the project root, copy from template:
- `Dockerfile` → `C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\Dockerfile`
- `docker-compose.prod.yml` → `C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\docker-compose.prod.yml`
- `.dockerignore` → `C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\.dockerignore`
- After copying, customize `PROJECT_SLUG` in docker-compose.prod.yml with the actual project slug
- Customize Dockerfile base image to match detected tech stack (Node.js → node:22-alpine, Python → python:3.12-slim, Go → golang:1.22-alpine)

**0h.** Update the `Last updated` date in `CODEBASE_CONTEXT.md` to today.

**0i.** Present a sync report:
```
SYNC COMPLETE
=============
CODING_STANDARDS.md:
  ✅ [N] sections verified present
  📝 [N] sections added/updated
  ⏭️  [N] sections unchanged

CODEBASE_CONTEXT.md:
  ✅ [N] sections verified present
  📝 [N] sections added (e.g., ## Deep References placeholder added)
  ⏭️  [N] sections unchanged

Rules Files:
  ✅ [N] rules files verified
  📝 [N] files split for 12K limit compliance (if any)

Workflows:
  ✅ [N] workflows verified
  📝 [N] workflows added/updated
  ⏭️  [N] workflows unchanged

No project-specific customizations were lost.

Next: Run /sync-context or /deep-study to populate Deep References with real paths.
```

**After 0i, skip directly to Phase 4 (Verify) Step 10.**

---

## Phase 1: Understand What Exists

**Skip this phase if running in Sync Mode (Phase 0).**

1. **Scan the Project:**
    - Run `git log --oneline -20` to understand recent history.
    - List all directories and key files.
    - Read `package.json`, `requirements.txt`, `Cargo.toml`, or equivalent to identify the tech stack.
    - Read the `README.md` if it exists.
    - Identify: language, framework, package manager, test runner, build tool, deployment target.
    - Present to user:
      ```
      PROJECT SCAN
      ============
      Name: [from package.json or dir name]
      Tech stack: [language + framework + build tool]
      Package manager: [npm/pip/cargo/etc]
      Test runner: [jest/pytest/etc or NONE]
      Deployment: [vercel/docker/etc or UNKNOWN]
      Entry point: [main file]
      Source dir: [src/ or equivalent]
      Files: [count] across [count] directories
      ```

2. **Deep-Read the Codebase:**
    - Read outlines of every source file (not node_modules/venv/dist).
    - Identify:
      - Main components/pages/modules
      - Routing structure (if web app)
      - State management approach
      - API integrations
      - Key patterns (component structure, naming conventions, file organization)
    - This is the `/deep-study` phase — be thorough.

3. **Identify What's Already Built:**
    - List every feature/page/component that EXISTS and WORKS.
    - These will become `[x]` (completed) items in progress.md.
    - Group by logical area (e.g., "Landing page", "Auth", "Dashboard").

## Phase 2: Create the Infrastructure

4. **Create `.agent/` directory structure:**
    ```
    .agent/
    ├── workflows/
    │   ├── PIPELINE.md
    │   ├── resume.md
    │   ├── add-task.md
    │   ├── clarify.md
    │   ├── commit.md
    │   ├── implement-next.md
    │   ├── check-modularity.md
    │   ├── refactor-module.md
    │   ├── security-audit.md
    │   ├── report-bug.md
    │   ├── generate-tests.md
    │   ├── deep-study.md
    │   ├── sync-context.md
    │   ├── finalize-plan.md
    │   ├── generate-readme.md
    │   └── validate-prd.md
    ├── guides/
    │   ├── bootstrap-guide.md
    │   └── retrofit-guide.md
    └── rules/
        ├── CODING_STANDARDS.md
        ├── CODING_STANDARDS_TESTING.md
        ├── CODING_STANDARDS_DOMAIN.md
        └── CODEBASE_CONTEXT.md
    ```

5. **Generate `CODEBASE_CONTEXT.md`:**
    - Write this from what you learned in Phase 1 into `.agent/rules/CODEBASE_CONTEXT.md`.
    - **Remove the `<template_manager_warning>` block entirely.** It is only for template editors.
    - Include: tech stack table, file inventory, key patterns, environment variables.
    - This is the source of truth — same format as other projects.
    - **Populate `## Shared Foundation`:** Scan for high-fan-out files — files imported by 3+ other modules.
    - **Populate `## Deep References`:** For each module discovered, add a pointer row.
    - **Keep sections lean:** Each module in Key Modules should be a one-line summary, not a paragraph. Target: under 300 lines total.
    - Set `Last updated` to today.
    - Set `Template synced` to today.
    - **⛔ SIZE GATE:** If `CODEBASE_CONTEXT.md` exceeds 10,000 characters, split per the rules in Phase 0 Step 0b.

6. **Generate `CODING_STANDARDS.md` (3-file split):**

    This is a MERGE task — you combine project-specific patterns with universal rules from the template. Follow ALL sub-steps:

    **6a.** Document the EXISTING code patterns found in Phase 1.

    **6b.** Read the template CODING_STANDARDS files at:
    ```
    C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\.agent\rules\CODING_STANDARDS.md
    C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\.agent\rules\CODING_STANDARDS_TESTING.md
    C:\Users\harri\OneDrive\Documents\SAAS DEV\project-template\.agent\rules\CODING_STANDARDS_DOMAIN.md
    ```

    **6c.** Copy ALL universal sections from the template into the project's coding standards files (one file per concern). Customize for the project's tech stack.

    **6d.** Verify each resulting file is under 10,000 characters.

7. **Generate `docs/progress.md`:**
    - Start with completed features as `[x]`.
    - **TDD Check:** If no test runner found, add Phase 0 as FIRST backlog section.
    - Add Backlog, velocity tracking, and Deviations Log sections.

## Phase 3: Customize Workflows

8. **Generate ALL workflows:**
    - Copy each workflow from the template concept, but customize for THIS project.
    - **Every workflow MUST end with a Suggest Next step.**
    - **PIPELINE.md** must list all workflows with suggestions.

9. **Install Commit Hook:**
    - Create `.git/hooks/commit-msg` with the conventional commit validator.

9b. **Create or update `.gitignore`:**
    - Include mandatory entries for `.agent/workflows/`, `.agent/guides/`, `docs/progress.md`, `docs/*PRD*.md`.

## Phase 4: Verify

10. **Verify the Setup:**

    **10a.** Run `git status` — confirm `.agent/` and `docs/` are ready to commit.

    **10b.** Run the build command to make sure nothing broke.

    **10c.** **Verify CODING_STANDARDS completeness** — open EACH rules file and confirm ALL universal sections exist across the 3 files:
    - [ ] Project-specific commands (dev, build, lint, test)
    - [ ] Project-specific file conventions and component patterns
    - [ ] Workflow Pipeline Awareness
    - [ ] Skill Selection & Orchestration
    - [ ] Git Commit Convention
    - [ ] AI Discipline Rules (no scope creep, no phantom deps, search before creating, etc.)
    - [ ] Production-Readiness Rules
    - [ ] File Size Limits
    - [ ] Testing Rules — Anti-Cheat
    - [ ] Test Quality Checklist (10-category table)
    - [ ] Edge Case Coverage Guide
    - [ ] Test Modularity Rules
    - [ ] Business-Context Testing
    - [ ] PowerShell Environment

    **10d.** **Verify all rules files are under 10,000 characters:**
    ```powershell
    Get-ChildItem ".agent\rules\*.md" | ForEach-Object { $chars = (Get-Content $_.FullName -Raw).Length; if($chars -gt 10000) { Write-Host "⛔ OVER: $($_.Name) = $chars" } else { Write-Host "✅ OK: $($_.Name) = $chars" } }
    ```

    **If ANY section is missing or ANY file exceeds 10,000 chars, go back and fix. Do NOT proceed.**

    **10e.** Present summary:
      ```
      RETROFIT COMPLETE          (or SYNC COMPLETE)
      =================
      ✅ .agent/workflows/ — [N] workflows created/verified
      ✅ .agent/guides/ — [N] guide files
      ✅ .agent/rules/ — [N] rules files (all under 10K chars)
      ✅ docs/progress.md — [N] existing features logged, backlog ready
      ✅ .git/hooks/commit-msg — conventional commits enforced
      ✅ .gitignore — workflows excluded, rules included
      ✅ Build verified
      ✅ CODING_STANDARDS — all [N] universal sections present
      
      READY TO USE:
      - /add-task to add new work
      - /clarify to break down complex items
      - /implement-next to start building with TDD
      - /commit to push these setup changes
      ```

11. **Commit the Setup:**
    - Suggest: `chore(workflows): retrofit project into workflow system` (first time)
    - Or: `chore(workflows): sync project with latest template` (sync mode)
    - Use `/commit` workflow for this.

12. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
