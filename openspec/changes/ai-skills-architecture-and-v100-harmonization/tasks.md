## 1. Add, Delete & Refactor Skills (`.agent/skills/`)

- [ ] 1.1 Create `.agent/skills/mobile-capacitor-expert/SKILL.md` covering Capacitor 7 monorepo architecture, zero-URL-rewrite static export (`generateStaticParams` + `useResolvedRouteParam`), `@capacitor-community/secure-storage`, HASS Server Selector, Flask-free OAuth deep-link handoff, and Ubuntu Gradle/ADB + GitHub Actions macOS Xcode CI.
- [ ] 1.2 Delete `.agent/skills/cloud-backup-setup/SKILL.md` and merge hybrid `S3_BACKEND=auto|s3|rclone`, `data/federation_keys/server.pem` backup, and `scripts/restore.sh` runbooks into `.agent/skills/devops-observability-expert/SKILL.md`.
- [ ] 1.3 Refactor `.agent/skills/planning-expert/SKILL.md` into an OpenSpec PRD & Release Stream Architect aligned with `openspec-propose` and `implementation-expert`.

## 2. Harmonize All Skills & Gemini Gems to `v1.0.x`

- [ ] 2.1 Update `.agent/skills/ai-tools-harmonizer/SKILL.md` (fix `.agent/skills/*/SKILL.md` path and register `mobile-capacitor-expert`).
- [ ] 2.2 Update `Current State` (`v0.9.4` complete through `C94`) and `Upcoming` (`v1.0.0` Native Mobile Ecosystem `C95`–`C100`, `v1.0.1` LEGO/Maps/New Types `C101`–`C108`, `v1.0.2` Offline Cache & Store Gate `C109`–`C110`) across all Persona Skills (`.agent/skills/*/SKILL.md`) and `.gemini/gems/*.md` (leaving `"Talk like caveman"` intact in `.agent/rules/iqoqo-standards.md`).

## 3. Verification & Tests

- [ ] 3.1 Author `tests/test_ai_skills_integrity.py` verifying valid YAML frontmatter on all `.agent/skills/*/SKILL.md` files, presence of `mobile-capacitor-expert`, removal of `cloud-backup-setup`, and `v1.0.0` / `v0.9.4` context synchronization across skills and gems.
- [ ] 3.2 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.
