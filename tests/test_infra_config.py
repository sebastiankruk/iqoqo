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
        self.run_sh = self.repo_root / "run.sh"
        self.temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.work_dir = Path(self.temp_dir.name)

        # Copy script to temp dir for isolated testing
        self.script_path = self.work_dir / "run.sh"
        self.script_path.write_text(self.run_sh.read_text())
        self.script_path.chmod(0o755)

        (self.work_dir / "pyproject.toml").write_text('[project]\nversion = "0.5.0"')

        # Create a mock bin directory to prevent actual execution of Docker/Flask
        self.bin_dir = self.work_dir / "bin"
        self.bin_dir.mkdir()
        for cmd in ["docker", "flask", "python3", "python", "pip", "colima", "npm", "psql"]:
            (self.bin_dir / cmd).write_text("#!/bin/bash\nexit 0")
            (self.bin_dir / cmd).chmod(0o755)

        # Mock .venv/bin/activate to prevent exit on source
        venv_bin = self.work_dir / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "activate").write_text("#!/bin/bash")

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_script(self, args=None, env_content=None, mode_env=None):
        if env_content:
            (self.work_dir / ".env").write_text(env_content)
        if mode_env:
            mode = args[0] if args else "dev"
            (self.work_dir / f".env.{mode}").write_text(mode_env)

        env = os.environ.copy()
        # Clean environment to ensure script validation triggers
        for var in ["DATABASE_URL", "REDIS_URL", "SECRET_KEY"]:
            if var in env:
                del env[var]
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"

        cmd = ["bash", "./run.sh"]
        if args:
            cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
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
        result = self.run_script(env_content="DATABASE_URL=postgresql://localhost/db")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Missing required environment variables", result.stdout)
        self.assertIn("REDIS_URL", result.stdout)
        self.assertIn("SECRET_KEY", result.stdout)

    def test_mode_switching_and_env_loading(self):
        # Test that 'prod' mode loads .env.prod
        env_content = "DATABASE_URL=postgresql://localhost/db\nREDIS_URL=redis://localhost:6379/0\nSECRET_KEY=base"
        mode_env = "SECRET_KEY=prod-secret"
        
        result = self.run_script(args=["prod"], env_content=env_content, mode_env=mode_env)
        
        self.assertIn("Entering mode 'prod'", result.stdout)
        self.assertIn("Loading overrides from .env.prod", result.stdout)

    def test_alembic_version_detection_mock(self):
        # Mock docker to return version when psql is called through it
        docker_mock = self.bin_dir / "docker"
        docker_mock.write_text("""#!/bin/bash
if [[ "$*" == *"psql"* ]]; then
    echo "mock-version-123"
else
    exit 0
fi
""")
        # Mock python3 to return a specific version for the Alembic check
        python_mock = self.bin_dir / "python3"
        python_mock.write_text("""#!/bin/bash
if [[ "$*" == *"alembic.script"* ]]; then
    echo "mock-version-123"
else
    echo "0.5.0"
fi
""")

        env_content = "DATABASE_URL=postgresql://localhost/db\nREDIS_URL=redis://localhost:6379/0\nSECRET_KEY=base"
        result = self.run_script(args=["prod"], env_content=env_content)
        
        self.assertIn("Migration state: mock-version-123", result.stdout)

    def test_alembic_mismatch_warning(self):
        # Mock docker to return version when psql is called through it
        docker_mock = self.bin_dir / "docker"
        docker_mock.write_text("""#!/bin/bash
if [[ "$*" == *"psql"* ]]; then
    echo "current-version"
else
    exit 0
fi
""")
        # Mock python3 to return a different version than psql
        python_mock = self.bin_dir / "python3"
        python_mock.write_text("""#!/bin/bash
if [[ "$*" == *"alembic.script"* ]]; then
    echo "expected-version"
else
    echo "0.5.0"
fi
""")
    def test_tunnel_flag(self):
        # Test that --tunnel loads .env.dev even in dev mode (normally .env.dev is optional)
        env_content = "DATABASE_URL=postgresql://localhost/db\nREDIS_URL=redis://localhost:6379/0\nSECRET_KEY=base"
        mode_env = "TUNNEL_VAR=activated"
        
        # We need to mock .env.dev because run.sh check [ "$TUNNEL" = true ] && [ -f ".env.dev" ]
        (self.work_dir / ".env.dev").write_text(mode_env)
        
        result = self.run_script(args=["dev", "--tunnel"], env_content=env_content)
        
        self.assertIn("Loading Tunnel Configuration (.env.dev)", result.stdout)

    def test_clean_flag(self):
        # Test that --clean triggers docker compose down
        docker_mock = self.bin_dir / "docker"
        docker_mock.write_text("""#!/bin/bash
if [[ "$*" == *"compose down"* ]]; then
    echo "DOCKER_DOWN_TRIGGERED"
fi
exit 0
""")
        env_content = "DATABASE_URL=postgresql://localhost/db\nREDIS_URL=redis://localhost:6379/0\nSECRET_KEY=base"
        result = self.run_script(args=["prod", "--clean"], env_content=env_content)
        
        self.assertIn("Cleaning up previous instances", result.stdout)
        self.assertIn("DOCKER_DOWN_TRIGGERED", result.stdout)


if __name__ == "__main__":
    unittest.main()
