---
description: This file defines the logical sequence of workflows. Each workflow must suggest the NEXT workflow when it finishes. The AI reads this to know where the user is in the pipeline.
---

# Workflow Pipeline — Execution Order

> This file defines the logical sequence of workflows. Each workflow must suggest the NEXT workflow when it finishes. The AI reads this to know where the user is in the pipeline.

## Project Setup Pipeline (run once)

```
/refine-prd → /prepare-prd → /bootstrap → /implement-next
```

| Step | Workflow | When Done, Suggest |
|------|----------|-------------------|
| 1 | `/refine-prd` | *"PRD refined. Run `/prepare-prd` to format it into the standard structure."* |
| 2 | `/prepare-prd` | *"PRD formatted. Run `/bootstrap` to auto-configure the project."* |
| 3 | `/bootstrap` | *"Project bootstrapped. Run `/implement-next` to start building."* |
| 3b | `/retrofit` | *"Existing project retrofitted. Run `/add-task` to add work, or `/commit` to push setup."* |

## Development Pipeline (run repeatedly)

```
/add-task → /implement-next → /implement-next → ... → /check-modularity → /validate-prd → /security-audit
```

| Step | Workflow | When Done, Suggest |
|------|----------|-------------------|
| 4 | `/add-task` | *"Task added to progress.md. Run `/implement-next` to start building it."* |
| 4b | `/clarify` | *"Task expanded into sub-items. Run `/implement-next` to start on the first sub-item."* |
| 4c | `/report-bug` | *"Bug reported with full context. Run `/implement-next` to fix it."* |
| 5 | `/implement-next` | *"Item done. Run `/implement-next` for the next item, or `/check-modularity` if phase is complete. If ALL items are `[x]`, run `/validate-prd`."* |
| 6 | `/check-modularity` | *"If violations found: Run `/refactor-module` to fix safely. If clean: `/implement-next` or `/validate-prd`."* |
| 6b | `/refactor-module` | *"Violation fixed. Run `/check-modularity` to verify, or continue with `/implement-next`."* |
| 7a | `/validate-prd` | *"Validation complete. Fix failures, then run `/setup-ci` to generate CI/CD config."* |
| 7b | `/setup-ci` | *"CI/CD configured. Set the listed secrets in GitHub, push to trigger first run. If it fails, run `/fix-ci`. When green, run `/security-audit`."* |
| 7c | `/security-audit` | *"Security audit complete. Fix any findings, then continue with `/implement-next`."* |

## Support Workflows (run as needed)

| Workflow | Triggered By | When Done, Return To |
|----------|-------------|---------------------|
| `/resume` | New conversation | *"Context restored. Run `/implement-next` to continue."* |
| `/status` | Quick check on progress | *"Status checked. Run `/implement-next` to continue."* |
| `/generate-tests` | Missing test coverage | *"Tests added. Run `/implement-next` to continue."* |
| `/deep-study` | Need to understand code | *"Study complete. Run `/implement-next` to continue."* |
| `/sync-context` | Docs out of date | *"Docs synced. Run `/implement-next` to continue."* |
| `/finalize-plan` | Complex plan needs verification | *"Plan verified. Proceeding with implementation."* |
| `/commit` | Manual changes need committing | *"Changes committed. Run `/implement-next` to continue."* |
| `/generate-readme` | Project needs a professional README | *"README generated. Run `/commit` to push it."* |
| `/hotfix` | Production emergency | *"Hotfix deployed. Run `/sync-context` to update docs, then `/implement-next` to continue."* |
| `/audit-progress` | progress.md feels incomplete or misordered | *"Progress audit complete. Run `/implement-next` to continue building."* |
| `/fix-ci` | CI pipeline failed | *"CI fixed and green. Continue with `/implement-next` or `/security-audit`."* |

## How the AI Uses This

After completing ANY workflow, the AI MUST:
1. Read this file to determine the next logical step.
2. Suggest the next workflow to the user with the exact phrasing from this table.
3. Never leave the user guessing what to do next.
