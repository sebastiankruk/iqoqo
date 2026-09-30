## Approach

Layer-by-layer bottom-up review using the unified `code-reviewer` skill with five lenses: Security 🔒, SRE ⚙️, QA 🧪, Architecture 🏗️, Readability 👁️.

## Review Methodology

1. **Pre-flight**: Query mempalace/graphify for historical context on the chunk's files
2. **Read & Analyze**: Scan each file through all five lenses using the code-reviewer skill
3. **Cross-reference**: Use codegraph for dependency analysis on complex files
4. **Document**: Write chunk review markdown to `.context/notes/review/0.7.18/`
5. **Checkpoint**: Present findings for human discussion
6. **Track**: Mark chunk task complete in this openspec change

## Severity System

- 🔴 **CRITICAL** — must fix before 0.8.0
- 🟡 **MODERATE** — should fix, schedule in 0.8.x
- 🟢 **LOW** — nice to have, backlog

## Output Format

Per-file verdicts with severity-rated findings, collected into chunk markdown files. See `.agents/skills/code-reviewer/SKILL.md` for the full format specification.

## Consolidation

After all 26 chunks complete, findings are consolidated into `99-consolidated-findings.md` and a separate `review-0718-fix-plan` openspec change is created with real specs/design/tasks for implementing the fixes.
