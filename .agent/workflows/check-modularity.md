---
description: Audits code against modularity rules — file size, function length, code organization.
---

# Check Modularity

## Steps

// turbo-all

1. **Scan File Sizes:**
    - Find all source files > 250 lines. Flag for splitting.

2. **Scan Function Lengths:**
    - Find all functions > 40 lines. Flag for extraction.

3. **Scan Class Sizes:**
    - Find all classes > 180 lines. Flag for decomposition.

4. **Check Import Rules:**
    - Verify no circular imports.
    - Verify dependency hierarchy is respected.

5. **Audit Rules Files:**
    - Count characters in `.agent/rules/CODING_STANDARDS.md`.
    - Count characters in `.agent/rules/CODING_STANDARDS_TESTING.md` (if exists).
    - Count characters in `.agent/rules/CODING_STANDARDS_DOMAIN.md` (if exists).
    - Count characters in `.agent/rules/CODEBASE_CONTEXT.md`.
    - If ANY rules file > 10,000 characters → flag: *"⚠️ [filename] is [N] chars (limit: 10K before platform truncation at 12K). Run /sync-context to split."*
    - If CODEBASE_CONTEXT.md > 10,000 characters → flag: *"⚠️ CODEBASE_CONTEXT.md is [N] chars. Run /sync-context to split."*

6. **Report:** List all violations with file paths and line counts.

7. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
