---
description: Reads your PRD and auto-configures the ENTIRE project — fills progress.md, customizes coding standards, generates project-specific workflows, and prepares for /implement-next. Run this ONCE after /refine-prd and /prepare-prd.
---

# Bootstrap Project from PRD

> **This is a stub.** The full guide is too large for the workflow character limit.
> The steps below are NOT executable — they exist only for orientation AFTER you read the guide.

## ⛔ MANDATORY: Read the Full Guide First

```
view_file .agent/guides/bootstrap-guide.md
```

Read the ENTIRE guide file from first line to last line. The guide is ~367 lines. If it exceeds your read limit, make multiple sequential `view_file` calls with `StartLine`/`EndLine` until every line has been read.

**Do NOT execute any step from memory or assumption.** The guide contains:
- ⛔ SIZE GATES that abort the workflow if files exceed limits
- ⛔ MANDATORY GATES (PRD cross-check, dev environment verification)
- Exact file paths, PowerShell commands, and split-target tables
- Step ordering dependencies — skipping one step breaks later ones

**If you skip reading the guide, you WILL produce an incomplete bootstrap** — missing size gates cause silent truncation, missing cross-checks cause scope gaps, missing workflow customization leaves generic placeholders.

## ⛔ Verification Gate

After reading the guide, confirm you read it by stating the LAST section heading in the guide (it's a question only answerable by reading the file). Then proceed with Step 1.

## Orientation Only (read the guide first — these are NOT instructions)

The guide covers: PRD extraction → git setup → progress.md generation → cross-check gate → env verification gate → coding standards (3-file split with size gates) → CODEBASE_CONTEXT population (with size gate) → all 21 workflow customizations → env variables → deployment files → commit hook → report.
