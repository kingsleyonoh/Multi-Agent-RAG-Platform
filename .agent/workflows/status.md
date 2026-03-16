---
description: Quick project status — sprint velocity, blockers, and recent activity. Lighter than /resume, no full context restore.
---

# Quick Project Status

**Description:** A fast check on where things stand — velocity, blockers, recent commits. Use this when you want a snapshot, not a full context restore. For full context restore, use `/resume` instead.

## When to Use
- Quick standup check
- Before deciding what to work on next
- After being away briefly and wanting a summary

## Steps

1. **Read Progress Tracker:**
    - Open `docs/progress.md`.
    - Count items:
      - `[x]` = completed
      - `[/]` = in progress
      - `[ ]` = remaining
    - Calculate velocity:
      ```
      Sprint Velocity: X completed / Y total (Z%)
      In Progress: X items
      Remaining: X items
      ```

2. **Recent Activity:**
    - Run `git log --oneline -10` to show the last 10 commits.
    - Summarize: what areas were touched recently?

3. **Current Blockers:**
    - Check `docs/progress.md` for any `[BUG]` or `[FIX]` items.
    - Check for any `[/]` (in-progress) items that might be stalled.

4. **Present Status:**
    ```
    PROJECT STATUS
    ==============
    Velocity: X/Y completed (Z%)
    In Progress: [list items]
    Blockers: [list or "None"]

    Recent commits:
    [last 5 commits]

    Next up: [first unchecked item]
    ```

5. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow based on current project status.
