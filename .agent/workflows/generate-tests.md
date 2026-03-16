---
description: Generates tests for a specified module following project testing standards.
---

# Generate Tests

## Steps

1. **Understand the Testing Landscape:**
    - Read `.agent/rules/CODEBASE_CONTEXT.md` — check the **Commands** section for the test runner and the **Key Patterns** section for testing conventions.
    - Look at 1-2 existing test files to understand the project's test style: framework, fixture patterns, naming conventions, mock approach.
    - Follow what already exists — don't introduce a different testing pattern.

2. **Analyze Target Module:**
    - Read the target file. Identify functions, classes, external dependencies.
    - Check for existing tests to avoid duplication.
    - Read `CODING_STANDARDS_TESTING.md` (or `CODING_STANDARDS.md` if unsplit) **Test Quality Checklist** and **Edge Case Coverage Guide**.

3. **Draft Tests:**
    - Write tests covering: happy path, edge cases, error handling, integration.
    - Mock ALL external dependencies (APIs, external services).
    - Name tests after business behavior, not technical actions.
    - Use the same test patterns, fixtures, and structure found in step 1.

4. **Coverage Self-Check (before running):**
    Before running, verify the test file covers:
    - [ ] Happy path — does the thing work when given valid input?
    - [ ] At least 2 edge cases — boundary values, empty inputs, unexpected types
    - [ ] Error path — what happens when it fails? Is the error handled correctly?
    - [ ] If any box is unchecked → write the missing tests now. Don't skip.

5. **Run Tests:**
    - Execute the new tests. Verify they pass.
    - Run full regression suite to check for conflicts.

5. **Review:** Present test coverage summary to user — what's now covered that wasn't before.

6. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
