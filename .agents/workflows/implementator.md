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
- **Create PR**: Utilize **GitHub MCP tools** or the **`gh` CLI** (e.g., `gh pr create --title "<Title>" --body "<Plan Summary>" --base main`) to create the Pull Request.

### 4. Copilot Review Integration

- **Request Review**: Use the **GitHub MCP tools** or **`gh` CLI** to request a Copilot review (e.g., triggering a comment like `gh pr comment -b "@github-actions copilot review"` or adding the appropriate reviewer/label).
- Wait for and retrieve the review comments (e.g., `gh pr view --comments`).
- **Analysis**: Parse the Copilot feedback for actionable code changes.

### 5. Review Resolution & Final QA

- If changes are required by the review, invoke the **`implementation-export`** skill to apply the fixes exactly as requested.
- Run `make lint` and `make test` again.
- Once green, commit and push the fixes to the `target_branch`.
- Inform the user that the PR is open, reviewed, fixed, and all checks are passing.
