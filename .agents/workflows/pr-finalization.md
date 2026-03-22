---
description: Automated Pull Request Review, Fix, Test, and Finalization Workflow
---

# PR Finalization Workflow

## Trigger

Use this workflow when asked to "Review and finalize PR <number>" or prepare a branch for merging.

## Required Variables

- `PR_NUMBER`: The GitHub Pull Request number to review.

## Execution Steps

1. **Context Gathering**

   - Execute the `github-pr-reviewer` skill to fetch diffs, reviews, and unresolved comments for `PR_NUMBER`.
   - Read all plans outlined in `.github/context/private-notes/plan/*.md`.
   - Identify gaps between the PR state, the comments, and the private notes plan.

2. **Implementation & Fixes**

   - Address missing items from the notes.
   - Address unresolved code review comments left by Copilot, the user, or other developers.

3. **Intelligent Linting & Testing**

   - Execute the `makefile-tester` skill.
   - Ensure all fixes are verified. Do not proceed until tests are fully green and linting passes.

4. **Release Documentation (Conditional)**

   - Check the current branch name.
   - IF the branch name starts with `release/` (e.g., `release/0.0.7`):
     - Update `docs/CHANGELOG.md`.
     - Explicitly detail new features, changed items, breaking changes, and database migrations.

5. **Finalization**

   - Commit all changes with standard conventional commits.
   - Push changes to the remote repository.
   - Generate a "Manual Testing Guide" artifact documenting what was changed and step-by-step instructions on how a human should verify this branch.
