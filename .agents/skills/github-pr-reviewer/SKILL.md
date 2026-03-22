---
description: "Skill for fetching Pull Request diffs, reviews, and comments using the GitHub CLI efficiently."
---
# GitHub PR Reviewer

## Context
When executing PR reviews, you must pull the actual comments and diffs from GitHub to understand what needs to be fixed. Do not hallucinate or guess `gh` CLI commands. Use ONLY the exact commands specified below to conserve tokens and execution time.

## Instructions

1. **Initial Assessment & Diff:** Check authentication, view the summary, and get the code diff by running exactly:
   `gh auth status && gh pr view <PR_NUMBER> && gh pr diff <PR_NUMBER>`

2. **Fetch Structured Comments:** To get all inline and general PR comments without pagination issues, run exactly:
   `gh pr view <PR_NUMBER> --json title,body,headRefName,state,reviews,comments`

3. **Parse and Plan:** Read the JSON output from step 2 to identify actionable review items requested by reviewers (like Copilot or human developers) and create a precise to-do list before modifying any code.
