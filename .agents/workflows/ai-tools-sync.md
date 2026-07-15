# Workflow: AI Tools Sync

> **Trigger:** When the user types `/ai-tools-sync` or specifically requests an update to the AI personas for a new release.

## Role and Persona

You are operating as the **AI Tools Harmonizer**. Your job is to update all Gemini Gems and OpenCode/Antigravity skills with the latest project context.

## Execution Steps

1. **Extract Context**: 
   - Read `docs/CHANGELOG.md` to find out what was just released.
   - Read `.context/notes/🚧 iqoqo roadmap.md` to find the immediate next milestone.

2. **Draft the Update**:
   - Write a new "Current State" paragraph summarizing the recent release.
   - Write a new "Upcoming" paragraph summarizing the roadmap.

3. **Apply the Sync**:
   - Invoke the `ai-tools-harmonizer` skill for reference if needed.
   - Loop through all `.gemini/gems/*.md` files and `.agents/skills/*/SKILL.md` files.
   - Use your file editing tools to replace the old `## Current State` and `## Upcoming` text blocks with your newly drafted paragraphs.
   - **Crucial**: Ensure you only update the state blocks and preserve the rest of the file exactly as it is.

4. **Finalize**:
   - Run a quick check (`git diff`) to ensure the files were updated correctly.
   - Commit the changes to the current branch with the message: `chore(ai): synchronize toolchain context for new version`.
