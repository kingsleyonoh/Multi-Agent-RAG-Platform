---
description: Reads file changes, generates a conventional commit message, and pushes. For manual changes or doc updates outside /implement-next.
---

# Quick Commit & Push

**Description:** A fast workflow for committing changes that were made manually or through other workflows (like doc updates, workflow improvements, config changes). Reads the diff, generates a proper conventional commit message, and pushes after user approval.

> **Use this when:** You made changes outside of `/implement-next` and want to commit them cleanly.

// turbo-all

## Steps

1. **Read Changes:**
    - Run `git status` to see all changed/added/deleted files.
    - Run `git diff --stat` to see the scope of changes.
    - If there are untracked files, note them.

2. **Categorize Changes:**
    - Group files by type:
      - **Workflows** (`.agent/workflows/`) → commit type: `chore` or `docs`
      - **Documentation** (`docs/`, `README`, `CODEBASE_CONTEXT.md`) → commit type: `docs`
      - **Config** (`config/`, `.env.example`, `.gitignore`) → commit type: `chore`
      - **Source code** (`src/`, `pages/`, `app/`) → commit type: `feat`, `fix`, or `refactor`
      - **Tests** (`tests/`) → commit type: `test`

3. **Generate Commit Message:**
    - Follow the convention: `type(scope): descriptive message`
    - If changes span multiple categories, use the **dominant** category.
    - If changes are all docs/workflows: `docs(workflows): add safe refactor pipeline`
    - If changes are mixed code + docs: use the code type, mention docs in body.
    - Present to user:
      ```
      FILES CHANGED:
      [list from git status]
      
      Proposed commit:
      type(scope): message
      
      Approve and push? [yes/no/edit]
      ```

4. **Commit & Push:**
    - On approval: `git add . ; git commit -m "type(scope): message" ; git push`
    - On "edit": let user modify the message, then commit.
    - **Never push without user approval.**

5. **Post-Commit Check:**
    Did this commit do any of the following?
    - Add a new module or top-level directory
    - Change the database schema (new table, new field)
    - Add or remove environment variables
    - Add a new external integration or service
    - Significantly change the project structure

    **If YES →** *"Run `/sync-context` to update CODEBASE_CONTEXT.md with these structural changes."*
    **If NO →** No action needed.

6. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
