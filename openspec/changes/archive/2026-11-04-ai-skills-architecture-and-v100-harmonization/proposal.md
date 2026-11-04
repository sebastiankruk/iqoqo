## Why
As we enter the `v1.0.x` release stream, our AI Skills and Gemini Gems still describe `v0.9.2` as the current version and carry pre-OpenSpec / pre-native-S3 legacy skills: `cloud-backup-setup` only documents pre-v0.8.3 `rclone` backups (superseded by `C88` hybrid `S3_BACKEND=auto|s3|rclone` + `restore.sh`), `planning-expert` still instructs agents to generate raw inline file-patch snippets rather than OpenSpec PRDs, and we lack a dedicated `mobile-capacitor-expert` skill for our new Android/iOS ecosystem.

## What Changes

- **ADD Skill — `mobile-capacitor-expert` (`.agent/skills/mobile-capacitor-expert/SKILL.md`):** Create a dedicated skill for Capacitor 7 hybrid development, zero-URL-rewrite Next.js static export (`generateStaticParams` placeholder shell + `useResolvedRouteParam`), `@capacitor-community/secure-storage` vs `@capacitor/preferences` split, HASS-style Server Selector, Flask-free mobile OAuth deep-link handoff (`iqoqo://`), headless Ubuntu Gradle/ADB workflows, and macOS Xcode unsigned `.ipa` CI builds.
- **DELETE Skill — `cloud-backup-setup` & Merge into `devops-observability-expert`:** Delete `.agent/skills/cloud-backup-setup/SKILL.md` and fold the `C88` hybrid `S3_BACKEND=auto|s3|rclone` backup, `data/federation_keys/server.pem` preservation, and `scripts/restore.sh` disaster recovery workflows into `.agent/skills/devops-observability-expert/SKILL.md`.
- **REFACTOR Skill — `planning-expert`:** Refactor `.agent/skills/planning-expert/SKILL.md` from a legacy raw-code-snippet generator into an OpenSpec PRD & Release Stream Architect (`Explore -> Propose -> Apply -> Archive`) that collaborates cleanly with `product-manager`, `openspec-propose`, and `implementation-expert`.
- **UPDATE `ai-tools-harmonizer`, All 9 Persona Skills & All 10 Gemini Gems:** Fix `.agents/skills` path typo to `.agent/skills` in `ai-tools-harmonizer/SKILL.md`, register `mobile-capacitor-expert`, and synchronize `Current State` (`v0.9.4` complete through `C94`) and `Upcoming` (`v1.0.0` Native Mobile Ecosystem `C95`–`C100`, `v1.0.1` LEGO/Maps/New Types `C101`–`C108`, `v1.0.2` Offline Cache & Store Gate `C109`–`C110`) across `.agent/skills/*/SKILL.md` and `.gemini/gems/*.md` (while preserving `"Talk like caveman"` in `.agent/rules/iqoqo-standards.md`).

## Capabilities

### New Capabilities
- `ai-skills-v100-architecture`: Addition of `mobile-capacitor-expert`, retirement of `cloud-backup-setup` into `devops-observability-expert`, OpenSpec alignment of `planning-expert`, and `v1.0.x` harmonization across all Skills and Gemini Gems.

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

- `.agent/skills/mobile-capacitor-expert/SKILL.md` (New)
- `.agent/skills/cloud-backup-setup/SKILL.md` (Deleted)
- `.agent/skills/planning-expert/SKILL.md`, `.agent/skills/ai-tools-harmonizer/SKILL.md`
- `.agent/skills/{implementation-expert,test-craftsman,product-manager,devops-observability-expert,tech-comm-expert,ontologist-expert,growth-strategist,security-auditor,iqoqo-ux-auditor,code-reviewer}/SKILL.md`
- `.gemini/gems/*.md`
- `tests/test_ai_skills_integrity.py`
