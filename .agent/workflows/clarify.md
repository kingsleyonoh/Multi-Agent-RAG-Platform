---
description: Expand a high-level task into concrete sub-steps. Works with PRD-based AND non-PRD projects. Reads the codebase to fill in implementation details the original task was missing.
---

# Expand / Clarify a Task

**Description:** When a task in progress.md is too high-level and needs to be broken down into concrete sub-steps. This isn't a new task — it's enriching an existing one with codebase understanding and implementation details.

> **Use this when:**
> - A task is too vague to implement directly (e.g., "Integrate Stripe" → what does that actually mean for THIS codebase?)
> - You have working code from a previous project that shows the pattern
> - You want to discuss a feature's approach BEFORE `/implement-next` picks it up
> - The task needs more detail whether you have a PRD or not

## Steps

// turbo-all

1. **Identify the Parent Task:**
    - Ask the user: *"Which item in progress.md are you expanding?"*
    - Read `docs/progress.md` and find the matching item.
    - If no match, ask for clarification.

2. **Capture the Breakdown:**
    - Ask the user to describe what they've learned — in plain language.
    - Example: *"Connect Idealo actually means: (1) set up API to get product IDs, (2) use IDs to trigger scraping on self-hosted API, (3) fetch and store results"*

3. **Understand the Codebase Context:**
    - Read `.agent/rules/CODEBASE_CONTEXT.md` for architecture overview.
    - Read the source files relevant to this task — modules, models, existing patterns.
    - Identify:
      - **Where this feature fits** in the existing architecture
      - **What patterns to follow** (how do similar features work in this codebase?)
      - **What files will be affected**
      - **What edge cases exist** based on the existing code

4. **Capture Code Reference (if provided):**
    - If the user pastes code from a previous project or points to existing files:
      - **Analyze the code** — identify the pattern, dependencies, data flow, and key functions.
      - **Extract the implementation approach** — what does this code do step-by-step?
      - **Identify what needs adapting** — different DB schema? Different framework? Different naming?
      - Summarize to user:
        ```
        CODE ANALYSIS
        =============
        Source: [pasted code / file path]
        Pattern: [what the code does]
        Key functions: [list]
        Dependencies: [list]
        Adaption needed: [what changes for this project]
        ```
    - If no code provided, skip this step.

5. **Update Spec Context (adapt to project type):**

    **If a PRD exists:**
    - Open the project PRD.
    - Find the section matching the parent task.
    - Add a **Technical Implementation Notes** subsection with the concrete steps, patterns, and decisions discovered.

    **If NO PRD exists (retrofitted/mature project):**
    - The context lives in `progress.md` directly — as structured sub-items under the task.
    - No PRD to update, so ALL the detail goes into the task entry itself.
    - If the feature changes the project architecture, also update `CODEBASE_CONTEXT.md`.

6. **Update progress.md:**
    - Convert the parent item into a group with indented sub-items:
    ```
    Before:
    - [ ] Connect Idealo integration

    After:
    - [ ] Connect Idealo integration
      - **Context:** Idealo API uses category-based product harvesting
      - **Affected files:** `src/integrations/`, `src/models/offers.py`
      - **Existing pattern:** See `src/integrations/amazon.py` for similar connector
      - [ ] Set up Idealo API client to fetch product IDs by category
      - [ ] Build scraping trigger: send product IDs to self-hosted API
      - [ ] Fetch scrape results and store in database
    ```
    - Keep the parent checkbox — it's checked when ALL sub-items are done.
    - Context lines (bold prefix) = information for the AI. Checkboxes = work items.

7.  **Log the Expansion:**
    - Add an entry to the **Deviations Log** in `docs/progress.md` (use the SAME format as the existing table):
    ```markdown
    | Date | Type | Item | Original | Changed To | Reason |
    |------|------|------|----------|------------|--------|
    | 2026-02-24 | scope | Connect Idealo | 1 high-level task | 3 sub-steps + context | Codebase analysis revealed concrete integration pattern |
    ```
    - If the section doesn't exist, create it.

8.  **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
