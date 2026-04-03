---
description: Workflow for implementing set of features based on provided source code snippets
---

# Workflow: Implement, Test, and PR

## Description

Automates the integration of a provided implementation plan and code snippets. It strictly applies the code, enforces QA (lint/test), creates a Pull Request via GitHub MCP or `gh` CLI, requests a GitHub Copilot review, and resolves any resulting feedback to ensure a clean, merge-ready state.

## Trigger

User provides an implementation plan (with code or diffs) and requests implementation or PR creation.

## Required Inputs

- `target_branch`: The branch name where changes will be committed.
- `implementation_plan`: The specific code changes, diffs, or instructions provided by the user.

## Pre-Flight Check

- **Branch Verification**: Check if the `target_branch` was provided by the user in the prompt. If it was NOT provided, **HALT** and prompt the human: *"Please provide the target branch name for this implementation before I proceed."*

## Execution Steps

### 1. Strict Implementation

- Ensure you are on the `target_branch` (create and checkout if it does not exist using `git checkout -b <target_branch>`).
- Invoke the **`implementation-export`** skill (or direct file manipulation tools).
- Apply the provided `implementation_plan` exactly as specified using the appropriate file replacement tools.
- **Strict Constraint**: Apply changes without "extra creativity". Do not refactor, clean up, or hallucinate improvements outside of the provided plan.

### 2. Initial Quality Assurance

- Run `make lint` and `make test`.
- If linting fails, use auto-fixers (e.g., `ruff check --fix`, `black`, `eslint --fix`) to resolve styling issues.
- If tests fail, fix the syntax or integration errors strictly related to the applied code without altering the core logic.
- **Gate**: Do not proceed to step 3 until both linting and testing are 100% green.

### 3. Version Control & PR Creation

- Stage all modified files (`git add .`).
- Commit the changes using conventional commit formats describing the implemented feature/fix.
- Push the `target_branch` to the remote repository (`git push -u origin <target_branch>`).
- **DO NOT Create PR yourself**: but provide: title and body=Plan Summary.

### 4. Copilot Review Integration

- **ASK HUMAN to Request Review**
- Wait for Human to tell to  retrieve the review comments from given PR `#NUMBER`
- **Analysis**: Parse the Copilot feedback for actionable code changes.

### 5. Review Resolution & Final QA

- If changes are required by the review - double check their correctness and feasibility - prepare plan to address them
- Run `make lint` and `make test` again.
- Once green, commit and push the fixes to the `target_branch`.
- Inform the user that the PR is open, reviewed, fixed, and all checks are passing.
