---
description: Copies the raw PRD to Antigravity artifacts for collaborative discussion. You and the AI refine it together — add comments, fill gaps, challenge assumptions. When done, the final version overwrites the raw PRD in docs/ and is ready for /prepare-prd.
---

# Refine PRD (Collaborative Review)

**Description:** Before formatting the PRD, you want to DISCUSS it. This workflow copies your raw PRD into an Antigravity artifact so you can review it together, add comments, ask questions, and iterate. When you're satisfied, the finalized PRD replaces the raw one in `docs/`.

## When to Use
- You got a PRD from ChatGPT and it's not fully thought through yet
- You want to add your own ideas, challenge assumptions, fill gaps
- You want the AI to ask hard questions about the spec before building

## Steps

1. **Find the Raw PRD:**
    - Scan `docs/` for `.md` files that look like a PRD/spec.
    - Read the entire file.

2. **Write to Artifact for Discussion (NOT raw copy-paste):**
    - Create a NEW artifact file in the brain directory using `write_to_file` with `IsArtifact: true`.
    - **DO NOT simply copy-paste the raw markdown.** Artifacts have formatting rules:
      - Use standard markdown and GitHub Flavored Markdown
      - Use `> [!NOTE]`, `> [!WARNING]`, `> [!IMPORTANT]` alerts for key callouts
      - Use tables for structured data
      - Use fenced code blocks with language identifiers
      - Use mermaid diagrams for architecture/flow visualizations
      - Use file links like `[filename](file:///absolute/path)` for references
      - Keep bullet points concise — avoid long wrapped lines
      - Do NOT use HTML tags in mermaid labels
    - **Rewrite** the raw PRD content into proper artifact format, organizing by sections.
    - Add `> [!IMPORTANT]` callouts for sections that need user input.
    - Tell the user: *"I've loaded your PRD as a reviewable artifact. Let's refine it together."*

3. **Read the PRD Template:**
    - Read `docs/PRD_TEMPLATE.md` to know what 20 sections are needed.

4. **Initial Review — Ask Hard Questions:**
    Present a section-by-section audit:

    For each of the 20 required sections:
    - ✅ **Covered** — the PRD has this, and it's specific enough to code from
    - ⚠️ **Vague** — mentioned but needs more detail (ask specific questions)
    - ❌ **Missing** — not mentioned at all (ask if it's needed)

    Then ask the user targeted questions like:
    - *"Section 4: You mention a 'users' table but don't list the fields. What fields does a user have?"*
    - *"Section 5b: What screens does a user see? Walk me through the flow from landing → signup → dashboard. Any accessibility requirements?"*
    - *"Section 7: You don't mention background jobs. Does this app need any scheduled tasks?"*
    - *"Section 7b: What events trigger notifications? Which channels (email, push, in-app)?"*
    - *"Section 8b: What API endpoints does the frontend call? What does each return?"*
    - *"Section 10b: What's the expected traffic? What's an acceptable page load time? What user events do you need to track?"*
    - *"Section 12: What should we explicitly NOT build? This prevents scope creep."*
    - *"Section 12b: Is this replacing an existing system? If so, what's the migration plan?"*
    - *"Section 13: Your phases are too broad — 'build backend' is a 4-week epic. Can we break it into 1-3 day tasks?"*

5. **Iterate With the User:**
    - User responds with answers, corrections, new ideas.
    - AI updates the artifact with each round of feedback.
    - User can say things like:
      - "Add a caching layer"
      - "Remove the billing module, we'll do that manually"
      - "The schema needs a status field on orders"
      - "Change the tech stack to FastAPI instead of Django"
    - AI incorporates changes and re-presents affected sections.

6. **Challenge Assumptions:**
    Before finalizing, push back on risky decisions:
    - *"You have 15 database tables in Phase 1. That's a lot — should some move to Phase 2?"*
    - *"You're using 4 external APIs. Each one is a failure point. Do we need all of them in MVP?"*
    - *"This module spec is 200 words. The Klevar pricing engine spec was 800 words and we still found gaps. Should we add more detail?"*

7. **Finalize:**
    When the user says they're happy:
    - Copy the final artifact content to `docs/<project_name>_prd.md`, overwriting the raw version.
    - Tell the user: *"PRD finalized and saved to docs/. Run `/prepare-prd` to restructure it into the standard format."*

## The Full PRD Pipeline

```
ChatGPT writes rough PRD
        │
        ▼
Drop raw PRD into docs/
        │
        ▼
/refine-prd  ← YOU ARE HERE: discuss, comment, iterate in artifacts
        │
        ▼
/prepare-prd ← AI restructures into 20-section format
        │
        ▼
/bootstrap   ← AI auto-fills progress.md, coding standards, .env
        │
        ▼
/implement-next ← AI builds with TDD
```
