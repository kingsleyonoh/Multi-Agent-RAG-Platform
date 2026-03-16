---
description: Investigates bugs using root-cause analysis with evidence gathering and systematic tracing.
---

# Bug Investigator

## Steps

1. **Gather Evidence:**
    - Get the error message, traceback, or unexpected behavior description.
    - Check logs, terminal output, CI output.

2. **Trace Execution:**
    - Follow the call chain from entry point to failure.
    - Read every file in the path — don't guess.

3. **Hypothesize:**
    - Form 1-3 hypotheses for the root cause.
    - Rank by likelihood.

4. **Verify:**
    - Test the top hypothesis by reading the relevant code.
    - If wrong, move to the next hypothesis.

5. **Fix:**
    - Propose the minimal fix.
    - Write a test that reproduces the bug FIRST.
    - Apply the fix — test must now pass.
    - Run full regression suite.

6. **Suggest Next:** Read `PIPELINE.md` and suggest the appropriate next workflow.
