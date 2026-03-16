---
description: Takes a raw PRD (from ChatGPT, a doc, or your brain) and restructures it into the standard 20-section format that works with /bootstrap and /implement-next.
---

# Prepare PRD

**Description:** You have a raw PRD — maybe from ChatGPT, maybe a rough draft. This workflow reads it, identifies what's there and what's missing, restructures it into the standard format, and asks you to fill gaps.

## When to Use
- You got a PRD from ChatGPT and dropped it in `docs/`
- You wrote a rough spec and want it formatted properly
- You're starting a new project and need to build the PRD from scratch

## Steps

1. **Find the Raw PRD:**
    - Scan `docs/` for `.md` files.
    - Read the entire raw PRD.

2. **Read the Template:**
    - Read `docs/PRD_TEMPLATE.md` to know the required 20-section structure.

3. **Audit the Raw PRD — Section by Section:**
    For each of the 20 required sections, check if the raw PRD covers it:

    | Section | Status |
    |---------|--------|
    | 1. What Is This? | ✅ Found / ❌ Missing / ⚠️ Incomplete |
    | 2. Architecture Principles | ... |
    | 3. Tech Stack | ... |
    | 4. Database Schema | ... |
    | 5. Module Specifications | ... |
    | 5b. User Journeys & Screens | ... |
    | 6. Connectors / Integrations | ... |
    | 7. Scheduler / Background Jobs | ... |
    | 7b. Notifications Strategy | ... |
    | 8. Admin / UI | ... |
    | 8b. API Endpoints | ... |
    | 9. Project Structure | ... |
    | 10. Deployment | ... |
    | 10b. Performance & Observability | ... |
    | 11. Onboarding Process | ... |
    | 12. What NOT to Build | ... |
    | 12b. Migration Plan | ... |
    | 13. Build Phases | ... |
    | 14. Environment Variables | ... |
    | 15. Success Criteria | ... |

4. **Report Gaps to User:**
    Present the audit table and ask:
    - *"Your PRD is missing sections X, Y, Z. I can draft them from context, or you can provide the details. Which sections should I draft?"*

5. **Restructure the PRD:**
    - Take ALL content from the raw PRD.
    - Reorganize it into the 20-section format.
    - Don't delete any information — move it to the right section.
    - For missing sections, either:
      a. Draft them based on what's implied in other sections (ask user to confirm)
      b. Mark as `[TO BE DEFINED]` if there's no way to infer

6. **Critical Checks on the Restructured PRD:**
    - **Section 4 (Database Schema):** Does every table have field names, types, and constraints? Not just descriptions?
    - **Section 5 (Modules):** Is each module specific enough to implement? "Build pricing" is too vague — "5-layer cascade with margin brackets" is implementable.
    - **Section 5b (User Journeys):** Does every screen have a route and key actions? Are accessibility requirements specified?
    - **Section 7b (Notifications):** Does every notification have a trigger event and channel? Is the delivery service specified?
    - **Section 8b (API Endpoints):** Does every endpoint have a method, path, and auth requirement?
    - **Section 9 (Project Structure):** Is there a directory tree with file names? Not just "we'll have an API."
    - **Section 10b (Performance):** Are there measurable targets? "Fast" is useless — "API p95 < 200ms" is measurable.
    - **Section 13 (Build Phases):** Are the checkboxes specific enough to be progress.md items? Each should be a 1-3 day task, not a 2-week epic.
    - **Section 15 (Success Criteria):** Are they testable? "System works well" is useless — "Demo tenant runs unattended for 48 hours" is testable.

7. **Save the Restructured PRD:**
    - Save as `docs/<project_name>_prd.md`
    - Delete or rename the raw PRD to `docs/raw_prd_backup.md`

8. **Present for Review:**
    - Show the restructured PRD to the user.
    - Ask for any corrections or additions.
    - Iterate until approved.

9. **Hand Off:**
    - *"PRD is ready. Run `/bootstrap` to auto-fill progress.md and configure the project."*

## PRD Quality Checklist

Before the PRD is approved, verify:

- [ ] Every table in Section 4 has exact field names and types (not just descriptions)
- [ ] Every module in Section 5 describes inputs, outputs, and edge cases
- [ ] Every screen in Section 5b has a route and key actions
- [ ] Section 7b has notification channels and delivery service specified
- [ ] Every endpoint in Section 8b has method, path, and auth
- [ ] Section 9 has a full directory tree with file purposes
- [ ] Section 10b has measurable performance targets (not just "fast")
- [ ] Section 13 has checkboxes specific enough for 1-3 day tasks
- [ ] Section 15 has testable success criteria
- [ ] No section says "TBD" or "to be decided" — everything is decided or explicitly marked as a future phase
