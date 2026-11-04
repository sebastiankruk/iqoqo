## Context

During our review of `.agent/skills/` and `.gemini/gems/`, we identified four structural improvements needed for the `1.0.x` stream:
1. No skill currently codifies our Capacitor 7 mobile architecture, zero-URL-rewrite static export rules, or Ubuntu/macOS mobile CI commands.
2. `cloud-backup-setup` is a 38-line legacy skill instructing admins to install `rclone` manually, ignoring our `C88` native `boto3` S3 + `rclone` dual-backend (`scripts/cloud_backup.sh` & `scripts/restore.sh`).
3. `planning-expert` predates `@fission-ai/openspec` and instructs agents to output raw code patches (`Add to app/api/admin.py after...`), duplicating `implementation-expert` and conflicting with `product-manager`'s OpenSpec PRD handoff directive.
4. All 9 Persona Skills and 10 Gemini Gems are stuck at `v0.9.2` in their `Current State` and `Upcoming` sections, and `ai-tools-harmonizer` references `.agents/skills/*/SKILL.md` instead of `.agent/skills/*/SKILL.md`.

## Goals / Non-Goals

**Goals:**
- Create `.agent/skills/mobile-capacitor-expert/SKILL.md`.
- Delete `.agent/skills/cloud-backup-setup/` and merge its cloud backup & restore guidance into `.agent/skills/devops-observability-expert/SKILL.md`.
- Refactor `.agent/skills/planning-expert/SKILL.md` for OpenSpec release stream & PRD planning.
- Synchronize `Current State` and `Upcoming` across all Skills and `.gemini/gems/*.md` to `v0.9.4` -> `v1.0.x`.

**Non-Goals:**
- Removing `"Talk like caveman"` from `.agent/rules/iqoqo-standards.md` (explicitly kept per user instruction).

## Decisions

### Consolidating Backup Guidance into `devops-observability-expert`
* **Decision:** Delete `.agent/skills/cloud-backup-setup/` and add a dedicated `Multi-Tier Cloud Backup & Disaster Recovery (S3 & Rclone)` section to `.agent/skills/devops-observability-expert/SKILL.md`.
* **Rationale:** Keeps all SRE/backup/restore operational knowledge in a single authoritative skill aligned with `C88`.
