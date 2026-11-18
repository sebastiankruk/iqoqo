# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Tests for validating AI skills and Gemini Gems architecture and harmonization."""

import unittest
from pathlib import Path

import yaml


class TestAISkillsIntegrity(unittest.TestCase):
    """Integrity suite for .agent/skills/ and .gemini/gems/."""

    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parent.parent
        self.skills_dir = self.repo_root / ".agents" / "skills"
        self.gems_dir = self.repo_root / ".gemini" / "gems"

    def test_all_skills_have_valid_yaml_frontmatter(self) -> None:
        """Every SKILL.md must have valid YAML frontmatter with name and description."""
        skill_files = list(self.skills_dir.glob("*/SKILL.md"))
        self.assertGreater(len(skill_files), 10, "Expected at least 10 skills in .agent/skills/")

        for skill_path in skill_files:
            content = skill_path.read_text(encoding="utf-8")
            self.assertTrue(
                content.startswith("---\n"),
                f"{skill_path} must begin with '---' YAML frontmatter delimiter",
            )
            parts = content.split("---\n", 2)
            self.assertGreaterEqual(
                len(parts),
                3,
                f"{skill_path} must have closing '---' frontmatter delimiter",
            )
            frontmatter_raw = parts[1]
            data = yaml.safe_load(frontmatter_raw)
            self.assertIsInstance(
                data,
                dict,
                f"{skill_path} frontmatter must be a YAML dictionary",
            )
            self.assertIn("name", data, f"{skill_path} missing 'name'")
            self.assertIn("description", data, f"{skill_path} missing 'description'")
            self.assertIn("license", data, f"{skill_path} missing 'license'")

            dir_name = skill_path.parent.name
            known_aliases = {
                "iqoqo-devops-sre-expert": "devops-observability-expert",
            }
            expected_dir = known_aliases.get(data["name"], data["name"])
            self.assertTrue(
                expected_dir == dir_name or expected_dir in dir_name or dir_name in expected_dir,
                f"Skill name '{data['name']}' in {skill_path} does not match directory '{dir_name}'",
            )

    def test_mobile_capacitor_expert_present_and_cloud_backup_removed(self) -> None:
        """Verify addition of mobile-capacitor-expert and removal of legacy cloud-backup-setup."""
        mobile_skill = self.skills_dir / "mobile-capacitor-expert" / "SKILL.md"
        self.assertTrue(mobile_skill.is_file(), "mobile-capacitor-expert/SKILL.md must exist")

        legacy_backup = self.skills_dir / "cloud-backup-setup"
        self.assertFalse(legacy_backup.exists(), "cloud-backup-setup must be removed")

    def test_persona_skills_and_gems_harmonized_to_v10x(self) -> None:
        """Persona skills and gems must reflect v1.0.2 shipped baseline and v1.0.3+ roadmap."""
        persona_skills = [
            "mobile-capacitor-expert",
            "implementation-expert",
            "test-craftsman",
            "product-manager",
            "devops-observability-expert",
            "tech-comm-expert",
            "ontologist-expert",
            "growth-strategist",
            "security-auditor",
            "iqoqo-ux-auditor",
            "planning-expert",
        ]

        for skill_name in persona_skills:
            skill_file = self.skills_dir / skill_name / "SKILL.md"
            self.assertTrue(skill_file.is_file(), f"Missing persona skill: {skill_file}")
            text = skill_file.read_text(encoding="utf-8")
            self.assertIn("v1.0.x stream", text, f"{skill_name} missing 'v1.0.x stream' in Current State")
            self.assertIn("v1.0.2", text, f"{skill_name} missing 'v1.0.2' shipped baseline")
            self.assertIn("## Upcoming (v1.0.3 & Beyond)", text, f"{skill_name} missing v1.0.3 Upcoming section")
            self.assertNotIn("v0.9.4, feature-complete", text, f"{skill_name} has stale v0.9.4 reference")
            self.assertNotIn("## Upcoming (v1.0.1 & Beyond)", text, f"{skill_name} has stale v1.0.1 Upcoming section")

        gem_files = [
            "software-engineer.md",
            "quality-assurance.md",
            "product-manager.md",
            "technical-communications.md",
            "site-reliability-engineering.md",
            "security-and-stability.md",
            "launch-and-growth.md",
            "ux-expert.md",
            "information-architect-ontologist.md",
        ]

        for gem_name in gem_files:
            gem_file = self.gems_dir / gem_name
            self.assertTrue(gem_file.is_file(), f"Missing gem: {gem_file}")
            text = gem_file.read_text(encoding="utf-8")
            self.assertIn("v1.0.x stream", text, f"{gem_name} missing 'v1.0.x stream'")
            self.assertIn("v1.0.2", text, f"{gem_name} missing 'v1.0.2' shipped baseline")
            self.assertIn("## Upcoming (v1.0.3 & Beyond)", text, f"{gem_name} missing v1.0.3 Upcoming section")
            self.assertNotIn("v0.9.4, feature-complete", text, f"{gem_name} has stale v0.9.4 reference")
            self.assertNotIn("## Upcoming (v1.0.1 & Beyond)", text, f"{gem_name} has stale v1.0.1 Upcoming section")


if __name__ == "__main__":
    unittest.main()
