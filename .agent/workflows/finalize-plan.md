---
description: Deep-reads all affected files before executing an implementation plan.
---

# Finalize Plan

**Description:** The last gate before coding. Verifies the implementation plan is correct by reading every file that will be touched, checking for conflicts, and confirming the plan matches the task requirements.

## Steps

1. **Read the Task Context:**
    - Read the task entry in `docs/progress.md` — including all context sub-items, decisions, and edge cases from `/add-task` and `/clarify`.
    - Read the implementation plan (from the current conversation or artifact).
    - Verify the plan actually addresses what the task describes. Flag any gaps.

2. **For each file to be modified:**
    - Read the ENTIRE file.
    - Note exact line numbers, function signatures, and imports.
    - Verify the planned changes don't conflict with existing code.
    - Check for recent changes that might not have been in context when the plan was written.

3. **For each new file to be created:**
    - Search the codebase to confirm it doesn't already exist.
    - Verify the target directory exists.
    - Confirm the file follows the project's naming and structure conventions.

4. **Check dependencies:**
    - Are all needed packages installed?
    - Are all needed imports available?

5. **Check test coverage plan:**
    - Does the plan include tests for the behaviors described in the task?
    - Does it cover the edge cases listed in the task context?
    - Does it follow the project's existing test patterns?

6. **Update the plan** with exact locations, line numbers, and any issues found.

7. **Present to user** for final approval before execution.

8. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
