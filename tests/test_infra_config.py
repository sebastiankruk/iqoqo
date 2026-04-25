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
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestRunScripts(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).parent.parent
        self.run_dev_sh = self.repo_root / "run_dev.sh"
        self.temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.work_dir = Path(self.temp_dir.name)

        # Copy script to temp dir for isolated testing
        self.script_path = self.work_dir / "run_dev.sh"
        self.script_path.write_text(self.run_dev_sh.read_text())
        self.script_path.chmod(0o755)

        # Mock pyproject.toml
        (self.work_dir / "pyproject.toml").write_text('[project]\nversion = "0.4.2"')

        # Create a mock bin directory to prevent actual execution of Docker/Flask
        self.bin_dir = self.work_dir / "bin"
        self.bin_dir.mkdir()
        for cmd in ["docker", "flask", "python3", "python", "pip", "colima", "npm"]:
            (self.bin_dir / cmd).write_text("#!/bin/bash\nexit 0")
            (self.bin_dir / cmd).chmod(0o755)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_script(self, env_content=None):
        if env_content:
            (self.work_dir / ".env").write_text(env_content)

        env = os.environ.copy()
        # Clean environment to ensure script validation triggers
        for var in ["DATABASE_URL", "REDIS_URL", "SECRET_KEY"]:
            if var in env:
                del env[var]
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"

        # We run with a timeout to catch cases where it waits for user input
        # or stays running (which it would if it passed validation)
        try:
            result = subprocess.run(
                ["bash", "./run_dev.sh"],
                cwd=self.work_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result
        except subprocess.TimeoutExpired as e:
            return e

    def test_validation_fails_when_vars_missing(self):
        # Missing REDIS_URL and SECRET_KEY
        result = self.run_script("DATABASE_URL=postgresql://localhost/db")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Missing required environment variables", result.stdout)
        self.assertIn("REDIS_URL", result.stdout)
        self.assertIn("SECRET_KEY", result.stdout)

    def test_validation_passes_when_vars_present(self):
        # All required vars present.
        # The script should proceed past validation and eventually time out
        # or fail on something else since it's a mock environment.
        env_content = "DATABASE_URL=postgresql://localhost/db\nREDIS_URL=redis://localhost:6379/0\nSECRET_KEY=supersecret"
        result = self.run_script(env_content)

        # If it passed validation, it would try to run 'docker compose up'
        # which our mock allows. It would fail later or time out.
        # We check that it DID NOT exit with the specific "Missing" error.
        self.assertNotIn("Missing required environment variables", result.stdout)


if __name__ == "__main__":
    unittest.main()
