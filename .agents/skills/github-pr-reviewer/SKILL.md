---
description: "Skill for fetching Pull Request diffs, reviews, and comments using the GitHub CLI efficiently."
---
# GitHub PR Reviewer

## Context

When executing PR reviews, you must pull the actual comments and diffs from GitHub to understand what needs to be fixed. Do not hallucinate or guess `gh` CLI commands. Use ONLY the exact commands specified below to conserve tokens and execution time.

Use this skill to fetch specific, actionable review comments on a Pull Request. Do not use standard `gh pr view` or `gh pr diff` initially, as they produce too much noise.

## Instructions

1. **Initial Assessment & Diff:** Check authentication, view the summary, and get the code diff by running exactly:
`gh auth status && gh pr view <PR_NUMBER> && gh pr diff <PR_NUMBER>`
1. **Fetch Unresolved Threads:** Run the following exact command to get a clean list of unresolved comments, files, and line numbers for the target `PR_NUMBER`:

```bash
gh api graphql -f query='
{
  repository(owner:"sebastiankruk", name:"iqoqo") {
    pullRequest(number: PR_NUMBER) {
      reviewThreads(first: 50) {
        nodes {
          isResolved
          comments(first: 10) {
            nodes { author { login } body path line }
          }
        }
      }
    }
  }
}' 2>&1 | python3 -c "
import json, sys
data = json.load(sys.stdin)
threads = data['data']['repository']['pullRequest']['reviewThreads']['nodes']
for i, thread in enumerate(threads):
    if not thread['isResolved']:
        for c in thread['comments']['nodes']:
            print(f'Path: {c.get(\"path\",\"?\")} Line: {c.get(\"line\",\"?\")}')
            print(f'Body: {c[\"body\"]}')
            print('---')
"
```

1. **Halt and Assess:** Do not write code immediately after fetching these comments. Proceed to cross-reference them with the project plan as mandated by your workflow.
1. **Targeted Diffs:** Only if you need more context around a specific comment's line number, use `sed -n '<start>,<end>p' <file>` to view the local file contents.
1. **Parse and Plan:** Read the JSON output from step 2 to identify actionable review items requested by reviewers (like Copilot or human developers) and create a precise to-do list before modifying any code.
