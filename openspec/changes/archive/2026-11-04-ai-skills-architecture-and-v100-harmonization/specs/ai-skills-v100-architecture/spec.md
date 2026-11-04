## Purpose
Modernize the repository's AI skills and Gemini Gems for the `v1.0.x` release stream by adding `mobile-capacitor-expert`, retiring `cloud-backup-setup` into `devops-observability-expert`, aligning `planning-expert` with OpenSpec, and synchronizing project state across all personas.

## ADDED Requirements

### Requirement: Mobile Capacitor Expert Skill & Consolidated DevOps Backup Skill

The repository SHALL provide `.agent/skills/mobile-capacitor-expert/SKILL.md` for Capacitor 7 iOS/Android engineering and SHALL consolidate cloud backup (`S3_BACKEND=auto|s3|rclone` and `restore.sh`) instructions inside `.agent/skills/devops-observability-expert/SKILL.md`, retiring `.agent/skills/cloud-backup-setup/`.

#### Scenario: Auditing repository skill directories
- **GIVEN** the `.agent/skills/` directory
- **WHEN** `tests/test_ai_skills_integrity.py` inspects the installed skills
- **THEN** `mobile-capacitor-expert/SKILL.md` exists with valid frontmatter and `cloud-backup-setup` does not exist.

### Requirement: Synchronized v1.0.x State Across All Persona Skills & Gemini Gems

All Persona Skills in `.agent/skills/*/SKILL.md` and Gemini Gems in `.gemini/gems/*.md` SHALL reflect `v0.9.4` (`C71`–`C94`) as the completed baseline and `v1.0.0`–`v1.0.2` (`C95`–`C110`) as the active `1.0.x` roadmap.

#### Scenario: Verifying skill and gem synchronization
- **GIVEN** any persona skill or Gemini Gem listed in `ai-tools-harmonizer`
- **WHEN** its `Current State` and `Upcoming` sections are inspected
- **THEN** they reference `v0.9.4` completion and the `v1.0.0` Native Mobile Ecosystem (`C95`–`C100`) stream.
