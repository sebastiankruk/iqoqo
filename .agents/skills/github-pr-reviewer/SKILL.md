---
name: github-pr-reviewer
description: "Skill for fetching and managing Pull Request diffs, reviews, and comments exclusively using the GitHub CLI (gh)."
license: AGPL
compatibility:
  - opencode
  - antigravity
metadata:
  audience: developers
---
# GitHub PR Reviewer

## Strict Tooling Mandate

- **MANDATORY:** Always use the GitHub CLI (`gh`) for all PR-related tasks (fetching diffs, reviews, comments, and replying to feedback).
- **CRITICAL:** DO NOT use the browser subagent or any MCP servers for GitHub interactions. This is a project-wide constraint.
- If the `gh` command fails, ask the user for help instead of switching to other tools.

## PR Review Analysis Flow

When executing PR reviews, you must pull the actual comments and diffs from GitHub to understand what needs to be fixed. Use ONLY the exact commands specified below to conserve tokens and execution time.

## Instructions (GitHub CLI)

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
          id
          isResolved
          comments(first: 10) {
            nodes { id author { login } body path line }
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
        print(f'Thread ID: {thread[\"id\"]}')
        for c in thread['comments']['nodes']:
            print(f'  Comment ID: {c[\"id\"]}')
            print(f'  Path: {c.get(\"path\",\"?\")} Line: {c.get(\"line\",\"?\")}')
            print(f'  Body: {c[\"body\"]}')
            print('  ---')
"
```

1. **Reply to Comments:** Use `gh pr comment <PR_NUMBER> --body "Your message"` for general comments, or use the GraphQL API to reply to specific threads if thread IDs are known.
1. **Halt and Assess:** Do not write code immediately after fetching these comments. Proceed to cross-reference them with the project plan as mandated by your workflow.
1. **Targeted Diffs:** Only if you need more context around a specific comment's line number, use `sed -n '<start>,<end>p' <file>` to view the local file contents.
1. **Parse and Plan:** Read the JSON output from step 2 to identify actionable review items requested by reviewers and create a precise to-do list before modifying any code.
