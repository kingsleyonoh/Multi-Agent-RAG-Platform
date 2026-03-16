---
description: Generates a professional README.md for any spec project. Reads actual source code, config, and git history. Output follows Architect persona voice and brand visual identity.
---

# Generate Professional README

**Description:** Reads the codebase deeply and generates a professional README.md that positions Kingsley Onoh as a Systems Architect. Every claim in the README comes from real code — no placeholders, no hallucinated features.

> **Use this when:** Implementation is complete and the project needs a public-facing README for GitHub.

// turbo-all

## Steps

1. **Read the Codebase:**
    - Read `.agent/rules/CODEBASE_CONTEXT.md` if populated (primary source).
    - If empty or still has `{{PROJECT_NAME}}` placeholders: scan the codebase directly:
      - List all directories and key files.
      - Read config files (`.env.example`, `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, etc.).
      - Read database schemas, migration files, model definitions.
      - Read the 2-3 most complex source files in full.
    - Run `git log --oneline -10` for project timeline.
    - Run `git remote get-url origin` for the GitHub clone URL.
    - **Detect live deployment URL:**
      - Check if `docker-compose.prod.yml` exists in the project root.
      - If found, `grep_search` for `Host(` to find Traefik host labels.
      - Extract the domain (e.g. `Host(`app.example.com`)` becomes `https://app.example.com`).
      - Store as `live_url` for use in the README demo badge.
      - If no `docker-compose.prod.yml` or no Traefik labels: `live_url` is empty.
    - If `CODEBASE_CONTEXT.md` is missing: *"No CODEBASE_CONTEXT.md found. Scanning the full codebase directly. For richer READMEs, run `/deep-study` first."*

2. **Extract Key Decisions:**
    - Scan for evidence of choices in the code:
      - Technology selections visible in config files and dependencies.
      - Rejected alternatives: what ISN'T used (no Docker? No ORM? No cloud?).
      - Tradeoffs visible in code structure, comments, constants, or git history.
      - TODO comments, magic numbers with reasoning, version 2 of functions.
    - Format each as: "I chose X over Y because Z."
    - Minimum 3, maximum 5 decisions.

3. **Generate Mermaid Diagram:**
    - Build from the actual system topology — not a generic template.
    - Use the brand palette theme config:
      ```
      %%{init: {'theme':'base','themeVariables':{'primaryColor':'#3B82F6','primaryTextColor':'#F0F0F5','primaryBorderColor':'#3B82F6','lineColor':'#3B82F6','secondaryColor':'#141418','tertiaryColor':'#0D0D0F','background':'#0D0D0F','mainBkg':'#141418','nodeBorder':'#3B82F6','clusterBkg':'#0D0D0F','clusterBorder':'#33333F','titleColor':'#F0F0F5','edgeLabelBackground':'#141418'}}}%%
      ```
    - Use `graph TB` layout (top-to-bottom).
    - Maximum 12 nodes. Group related components with `subgraph`.
    - Labels reflect actual components ("Pricing Engine", "Rate Limiter"), not file names ("analyzer.py").

4. **Generate the README:**
    Write the following structure exactly. The `<!-- THEATRE_LINK -->` marker must appear on its own line — architect-theatre searches for this exact string.

    ```markdown
    # {Project Name} — {one-line plain English description}

    Built by [Kingsley Onoh](https://kingsleyonoh.com) · Systems Architect

    ## The Problem

    {2-3 sentences on what business problem this solves and why it matters.
     Lead with the problem, not the technology.
     One specific number that anchors the problem in money or time.}

    ## Architecture

    ```mermaid
    %%{init: {brand theme config from Step 3}}%
    graph TB
        {actual system topology from codebase scan}
    ```

    ## Key Decisions

    - I chose {X} over {Y} because {Z}.
    - I chose {X} over {Y} because {Z}.
    - I chose {X} over {Y} because {Z}.
    {3-5 bullets total. Each one names the choice, the rejected alternative, and the reasoning.}

    ## Setup

    ### Prerequisites

    {list exact versions: Node 20+, Python 3.11+, PostgreSQL 16, etc.}

    ### Installation

    ```bash
    git clone {URL from git remote}
    cd {repo name}
    {install command: npm install / pip install -r requirements.txt / etc.}
    ```

    ### Environment

    ```bash
    cp .env.example .env
    ```

    {table of required env vars with descriptions — from .env.example or config}

    ### Run

    ```bash
    {actual dev server command from CODEBASE_CONTEXT or package.json}
    ```

    ## Usage

    {how to run the main commands/pipeline — the 3-5 most important commands}

    ## Tests

    ```bash
    {actual test command}
    ```

    {If live_url was detected in Step 1, add the following demo badge block:

    ---

    > **Live Demo:** [{live_url}]({live_url})
    >
    > This is a live demo with usage limits. For full access or a custom build, [get in touch](https://kingsleyonoh.com).

    If live_url is empty, omit this block entirely.}

    <!-- THEATRE_LINK -->
    ```

    **The Setup section must actually work.** Read the real config files and verify the commands. Do not guess.

5. **Voice Rules (enforce during generation):**

    **Register:** A principal engineer explaining a system over coffee. Not a corporate brochure.

    **Content ordering:** Always say what the system does and what problem it solves BEFORE listing technologies.

    **Technology naming:** Name the technology when it matters. "Built with Go and PostgreSQL" beats "Built on a layered service architecture."

    **Show judgment:** Include at least one rejected alternative or honest tradeoff. Admit what was hard.

    **Banned words:** leverage, utilize, crucial, comprehensive, seamless, robust, passionate, cutting-edge, and any word that could appear on any contractor's website.

    **Banned formatting:**
    - No emoji in headings.
    - No badge walls.
    - No GitHub stats cards.
    - No "currently learning" sections.

    **What NOT to include:**
    - No "Contributing" section (these are solo spec projects).
    - No "Acknowledgments" or "Credits" boilerplate.
    - No table of contents (READMEs should be short enough not to need one).
    - No "Screenshots" section (architecture diagrams replace them).
    - No "Contact" or "Contact Me" section. Socials are on the GitHub profile.
    - No email addresses anywhere in the README.

6. **Write to project root** as `README.md`.

7. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
