---
description: "Skill for fetching Pull Request diffs, reviews, and comments using the GitHub CLI."
---
# GitHub PR Reviewer

## Context
When executing PR reviews, you must pull the actual comments and diffs from GitHub to understand what needs to be fixed.

## Instructions

1. Check if `gh` CLI is authenticated by running `gh auth status`.
2. Fetch the PR Diff: Run `gh pr diff <PR_NUMBER>`.
3. Fetch PR Comments: Run `gh pr comments <PR_NUMBER>` and `gh pr view <PR_NUMBER> --comments`.
4. Parse the output to create a to-do list of required code changes.
