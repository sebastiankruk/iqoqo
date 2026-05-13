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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import subprocess

def test_production_fails_without_secret():
    env = os.environ.copy()
    env["FLASK_ENV"] = "production"
    env["SECRET_KEY"] = ""
    if "JWT_SECRET_KEY" in env:
        del env["JWT_SECRET_KEY"]
    
    # Try to run a simple flask command that loads config
    result = subprocess.run(
        [".venv/bin/flask", "routes"], 
        env=env, 
        capture_output=True, 
        text=True
    )
    
    print(f"Return code: {result.returncode}")
    print(f"Stderr: {result.stderr}")
    
    if "RuntimeError: SECRET_KEY environment variable is missing" in result.stderr:
        print("✅ SUCCESS: Production failed as expected with clear message.")
    else:
        print("❌ FAILURE: Production did not fail as expected.")

if __name__ == "__main__":
    test_production_fails_without_secret()
