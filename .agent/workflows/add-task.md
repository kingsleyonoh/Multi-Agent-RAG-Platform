---
description: Describe a bug, feature, or improvement in plain language. The AI adds it to progress.md properly formatted. Then run /implement-next.
---

# Add Task

**Description:** You describe what you want in your own words. The AI understands the project first, then turns your request into a properly formatted, context-rich task in `docs/progress.md`.

## Steps

// turbo-all

1. **Listen to the User:**
    - The user describes what they want. It can be rough, messy, one sentence, or a paragraph.
    - Examples of valid input:
      - "add a retry button to the failed jobs page"
      - "the pricing engine doesn't handle negative margins"
      - "we need a CSV export for tenant reports"

2. **Clarify If Needed:**
    - If the request is ambiguous, ask ONE focused question. Don't ask 5 questions.
    - If it's clear enough to code from, skip this step.

3. **Understand the Project:**
    - Read `.agent/rules/CODEBASE_CONTEXT.md` to understand the tech stack, architecture, and modules.
    - Based on the user's description, identify which parts of the codebase are relevant.
    - Read the relevant source files (module entry points, related models, existing patterns).

4. **Confirm Interpretation (MANDATORY — prevents scope narrowing):**
    - Before writing ANYTHING to progress.md, summarize what you found and what you understood:
      ```
      I found: [what the codebase contains related to this request]
      I understood your request as: [your interpretation]
      Scope: [what this would and wouldn't cover]
      
      Is that right, or did you mean something broader/different?
      ```
    - **Do NOT assume the codebase defines the scope.** The user's intent does. The codebase shows what exists, not what the user wants.
    - Wait for the user to confirm or correct before proceeding.

5. **Read Current Progress:**
    - Read `docs/progress.md` to see what's already there.
    - Check if a similar task already exists. If so, tell the user.

6. **Add to Progress Tracker:**
    - Add the task to `docs/progress.md` under the appropriate section.
    - **Placement matters:** insert the task **AFTER any items it depends on.** `/implement-next` picks items top-to-bottom, so a task must not appear before its dependencies (e.g., don't place a UI page before the API route it calls). If its dependencies don't exist yet, add them first.
    - Write it as a **context-rich entry** — not just a one-liner.
    - Prefix with `[BUG]`, `[FEATURE]`, or `[FIX]`.
    - Include structured sub-items with the context you gathered:
      ```markdown
      - [ ] [FEATURE] Add retry button to failed jobs page
        - **Context:** Jobs module at `src/jobs/`, uses BullMQ queue
        - **Affected files:** `src/jobs/views.py`, `templates/jobs/list.html`
        - **Existing pattern:** See "cancel job" button for the UI approach
      ```
    - For simple tasks, a one-liner with one context line is fine.
    - For complex tasks, include more sub-items. Scale to the task.
    - The goal: when `/implement-next` picks this up, it has enough context to generate a good plan WITHOUT re-reading the entire codebase from scratch.

7. **Confirm and Offer to Clarify:**
    - Show the user what was added.
    - Ask: *"Task added. Want to clarify it now? I can break it into sub-steps and read the codebase to fill in the details — or you can run `/implement-next` directly if it's clear enough."*
    - If yes → immediately run the `/clarify` workflow on this task. **Skip clarify step 1** (no need to ask which task — we just added it).
    - If no → read `PIPELINE.md` and suggest the appropriate next workflow.
