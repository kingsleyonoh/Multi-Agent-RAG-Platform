---
description: Bring an existing codebase into the workflow system, OR sync an existing project with the latest template. The reverse of /bootstrap — reads code first, generates docs from reality.
---

# Retrofit Existing Codebase

> **This is a stub.** The full guide is too large for the workflow character limit.
> The steps below are NOT executable — they exist only for orientation AFTER you read the guide.

## ⛔ MANDATORY: Read the Full Guide First

```
view_file .agent/guides/retrofit-guide.md
```

Read the ENTIRE guide file from first line to last line. The guide is ~356 lines. If it exceeds your read limit, make multiple sequential `view_file` calls with `StartLine`/`EndLine` until every line has been read.

**Do NOT execute any step from memory or assumption.** The guide contains:
- ⛔ CHANGELOG-driven sync logic (the ONLY reliable way to sync — do NOT diff manually)
- ⛔ Rules file migration with split procedures and size gates
- ⛔ Workflow guides migration (stub + guide pattern)
- Exact file paths, PowerShell commands, and verification steps
- Phase routing logic — sync mode vs full retrofit are completely different paths

**If you skip reading the guide, you WILL corrupt the project** — manual diffing loses project-specific customizations, skipping size checks causes silent truncation, wrong phase selection overwrites existing work.

## ⛔ Verification Gate

After reading the guide, confirm you read it by stating the LAST section heading in the guide (it's a question only answerable by reading the file). Then determine: does `.agent/rules/CODING_STANDARDS.md` already exist? If yes → Phase 0 (Sync). If no → Phase 1 (Full Retrofit).

## Orientation Only (read the guide first — these are NOT instructions)

**Sync Mode** (`.agent/` exists): CHANGELOG-driven comparison → rules migration with splits → workflow guides migration → section-by-section merge → verify.

**Full Retrofit** (new project): Scan codebase → deep-read all source → generate CODEBASE_CONTEXT + CODING_STANDARDS (3-file split with size gates) → customize all workflows → verify.
