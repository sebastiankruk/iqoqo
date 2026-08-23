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

"""Tests for POSIX ``--`` end-of-options hardening in rclone subprocess calls.

Security context (OpenSpec change ``v0716-security-subprocess-hardening``):
filenames flowing into rclone argv can be attacker-influenced — backup
retention archives (``app/core/tasks.py``), cover uploads
(``app/utils/images.py``), and the LLM cover cache (``app/utils/llm_covers.py``)
all pass database- or user-derived filenames to ``subprocess.run``.  A
filename beginning with dashes (e.g. ``--config=/etc/shadow``) would be
parsed by rclone as a command-line *option* unless a POSIX ``--``
end-of-options delimiter precedes the path arguments.  These tests codify
that defense for every rclone invocation so future refactors cannot
silently regress it.
"""

import ast
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.tasks import BackupManager
from app.utils.images import optimize_and_save_image
from app.utils.llm_covers import fetch_llm_cover

APP_DIR = Path(__file__).resolve().parent.parent / "app"

SUBPROCESS_ENTRYPOINTS = {"run", "Popen", "call", "check_call", "check_output"}


def _assert_delimiter_precedes(argv: list, path_args: list[str]) -> None:
    """Assert ``--`` is present in *argv* and precedes every user-controlled path."""
    assert "--" in argv, f"missing '--' delimiter in argv: {argv}"
    delimiter_index = argv.index("--")
    for path_arg in path_args:
        assert path_arg in argv, f"path argument missing from argv: {path_arg!r}"
        assert argv.index(path_arg) > delimiter_index, f"path argument {path_arg!r} is not positioned after '--' in argv: {argv}"


def _extract_rclone_argv(node: ast.Call) -> ast.List | None:
    """Return the argv ``ast.List`` node when *node* is a ``subprocess.<method>(["rclone", ...])`` call."""
    if not node.args:
        return None
    func = node.func
    if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "subprocess"):
        return None
    if func.attr not in SUBPROCESS_ENTRYPOINTS:
        return None
    first_arg = node.args[0]
    if (
        isinstance(first_arg, ast.List)
        and first_arg.elts
        and isinstance(first_arg.elts[0], ast.Constant)
        and first_arg.elts[0].value == "rclone"
    ):
        return first_arg
    return None


# ---------------------------------------------------------------------------
# app/core/tasks.py — BackupManager.upload_to_glacier (line 189)
# ---------------------------------------------------------------------------


class TestTasksRcloneDelimiter:
    """``--`` delimiter tests for ``BackupManager.upload_to_glacier`` (app/core/tasks.py)."""

    def test_upload_to_glacier_has_delimiter_before_paths(self) -> None:
        """Defense: tasks.py:189 places ``--`` between rclone options and the path arguments.

        Expected argv layout: ``["rclone", "copy", "--s3-no-check-bucket", "--", file_path, target]``.
        """
        manager = BackupManager(backup_dir="/tmp/test_backups", rclone_remote_archive="test-archive")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.upload_to_glacier("daily-backup.tar.gz")

        assert mock_run.called
        argv = mock_run.call_args[0][0]
        assert argv[0:3] == ["rclone", "copy", "--s3-no-check-bucket"]
        _assert_delimiter_precedes(argv, ["/tmp/test_backups/daily-backup.tar.gz", "test-archive:archives"])

    def test_upload_to_glacier_malicious_filename_stays_positional(self) -> None:
        """Scenario: a filename of ``--config=/etc/shadow`` must not be parsed as an option.

        With an empty backup dir the joined path *starts* with dashes — the
        exact shape of an option-injection attack.  The ``--`` delimiter at
        tasks.py:189 forces rclone to treat it as a positional path argument.
        """
        manager = BackupManager(backup_dir="", rclone_remote_archive="test-archive")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.upload_to_glacier("--config=/etc/shadow")

        argv = mock_run.call_args[0][0]
        _assert_delimiter_precedes(argv, ["--config=/etc/shadow"])


# ---------------------------------------------------------------------------
# app/utils/images.py — optimize_and_save_image cover push (line 128)
# ---------------------------------------------------------------------------


class TestImagesRcloneDelimiter:
    """``--`` delimiter tests for the cover-cache push in ``optimize_and_save_image`` (app/utils/images.py)."""

    @staticmethod
    def _run_with_mocked_pil(filepath: str) -> MagicMock:
        """Invoke optimize_and_save_image with PIL and subprocess mocked; return the subprocess mock."""
        with patch.dict(os.environ, {"RCLONE_COVERS_REMOTE": "test-remote"}):
            with patch("subprocess.run") as mock_run:
                with patch("PIL.Image.open") as mock_img_open:
                    mock_img = MagicMock()
                    mock_img_open.return_value.__enter__.return_value = mock_img
                    mock_img.convert.return_value = mock_img

                    optimize_and_save_image(b"fake_image_bytes", filepath)
        return mock_run

    def test_cover_push_has_delimiter_before_paths(self, tmp_path) -> None:
        """Defense: images.py:128 places ``--`` between rclone options and ``[filepath, target]``."""
        test_file = str(tmp_path / "covers" / "cover.jpg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)

        mock_run = self._run_with_mocked_pil(test_file)

        assert mock_run.called
        argv = mock_run.call_args[0][0]
        assert argv[0:3] == ["rclone", "copyto", "--s3-no-check-bucket"]
        _assert_delimiter_precedes(argv, [test_file, "test-remote:covers/cover.jpg"])

    def test_cover_push_malicious_filename_stays_positional(self) -> None:
        """Scenario: a cover basename of ``--config=evil.jpg`` must not be parsed as an option.

        The ``--`` delimiter at images.py:128 keeps a leading-dash basename
        positional in both the source path and the derived rclone target.
        """
        filepath = "/data/covers/--config=evil.jpg"

        mock_run = self._run_with_mocked_pil(filepath)

        assert mock_run.called
        argv = mock_run.call_args[0][0]
        _assert_delimiter_precedes(argv, [filepath, "test-remote:covers/--config=evil.jpg"])


# ---------------------------------------------------------------------------
# app/utils/llm_covers.py — fetch_llm_cover cache check (line 356)
# ---------------------------------------------------------------------------


class TestLlmCoversRcloneDelimiter:
    """``--`` delimiter tests for the global cover-cache pull in ``fetch_llm_cover`` (app/utils/llm_covers.py)."""

    def test_cache_check_has_delimiter_before_paths(self) -> None:
        """Defense: llm_covers.py:356 places ``--`` between rclone options and ``[target, local_file]``.

        The cache miss (returncode=1) path is exercised for every suffix so
        all four ``copyto`` invocations are asserted, not just the first.
        """
        with patch.dict(os.environ, {"RCLONE_COVERS_REMOTE": "test-remote"}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                fetch_llm_cover(identifier="work_123", title="Test Book", author="Test Author", user_id="user_1")

        assert mock_run.call_count == 4
        for call in mock_run.call_args_list:
            argv = call[0][0]
            assert argv[0:3] == ["rclone", "copyto", "--s3-no-check-bucket"]
            _assert_delimiter_precedes(argv, argv[argv.index("--") + 1 :])

    def test_cache_check_malicious_identifier_stays_positional(self) -> None:
        """Scenario: an identifier of ``--config=evil`` must not be parsed as an option.

        The identifier flows into the cache filename
        (``--config=evil_<suffix>.jpg``); the ``--`` delimiter at
        llm_covers.py:356 keeps it positional in both the rclone target and
        the local destination path.
        """
        with patch.dict(os.environ, {"RCLONE_COVERS_REMOTE": "test-remote"}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                fetch_llm_cover(identifier="--config=evil", title="Test Book", author="Test Author", user_id="user_1")

        assert mock_run.call_count == 4
        for call in mock_run.call_args_list:
            argv = call[0][0]
            target, local_file = argv[-2], argv[-1]
            assert "--config=evil" in target
            assert "--config=evil" in local_file
            _assert_delimiter_precedes(argv, [target, local_file])


# ---------------------------------------------------------------------------
# Static audit — every rclone subprocess call in app/ must embed ``--``
# ---------------------------------------------------------------------------


class TestRcloneSubprocessAudit:
    """AST audit guarding against future rclone invocations that forget the delimiter."""

    def test_all_rclone_subprocess_calls_include_delimiter(self) -> None:
        """Defense-in-depth audit: scan every ``app/**/*.py`` for ``subprocess.*(["rclone", ...])``
        calls and require a literal ``"--"`` element in the argv list.

        This codifies spec requirement "All rclone subprocess calls include
        POSIX end-of-options delimiter" and mitigates the design-doc risk of
        future developers adding new rclone calls without the delimiter.
        """
        violations: list[str] = []
        for py_file in sorted(APP_DIR.rglob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                argv_node = _extract_rclone_argv(node)
                if argv_node is None:
                    continue
                if not any(isinstance(elt, ast.Constant) and elt.value == "--" for elt in argv_node.elts):
                    violations.append(f"{py_file.relative_to(APP_DIR.parent)}:{node.lineno}")

        assert not violations, f"rclone subprocess calls missing '--' delimiter: {violations}"
