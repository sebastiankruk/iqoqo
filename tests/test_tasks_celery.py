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
from unittest.mock import MagicMock, patch

from app.core.tasks import BackupManager, get_task_result, rotate_and_archive_backups, submit_task


def dummy_task(x, y):
    return x + y


def failing_task():
    raise ValueError("Task failed spectacularly")


# Celery eager mode is handled globally in conftest.py


def test_submit_task_returns_id():
    task_id = submit_task(dummy_task, 10, 20)
    assert isinstance(task_id, str)
    assert len(task_id) > 0


def test_get_task_result_success():
    task_id = submit_task(dummy_task, 1, 2)
    result = get_task_result(task_id)
    assert result is not None
    assert result["status"] == "completed"
    assert result["result"] == 3


def test_get_task_result_failure():
    task_id = submit_task(failing_task)
    result = get_task_result(task_id)
    assert result is not None
    assert result["status"] == "failed"
    assert "Task failed spectacularly" in result["error"]


def test_get_task_result_user_isolation():
    task_id = submit_task(dummy_task, 5, 5, user_id="user_a")

    # Poll as user_a -> should work
    result_a = get_task_result(task_id, user_id="user_a")
    assert result_a is not None
    assert result_a["result"] == 10

    # Poll as user_b -> should return None (isolated)
    result_b = get_task_result(task_id, user_id="user_b")
    assert result_b is None


def test_get_task_result_not_found():
    result = get_task_result("non_existent_id")
    # Celery PENDING state for non-existent tasks by default
    assert result["status"] == "pending"


@patch("app.core.tasks.BackupManager")
def test_rotate_and_archive_backups(mock_manager_class):
    mock_manager = MagicMock()
    mock_manager_class.return_value = mock_manager

    # Create 15 mock backups
    mock_manager.list_backups.return_value = [f"backup_{i}.tar.gz" for i in range(15)]
    mock_manager.backup_dir = "/tmp/mock_backups"

    # Mock mtime so backup_0 is newest and backup_14 is oldest
    def mock_getmtime(path):
        filename = path.split("/")[-1]
        i = int(filename.split("_")[1].split(".")[0])
        return 1000.0 - i

    with patch("os.path.getmtime", side_effect=mock_getmtime):
        rotate_and_archive_backups()  # pylint: disable=no-value-for-parameter

    # Expect 15 - 12 = 3 backups to be archived
    assert mock_manager.upload_to_glacier.call_count == 3
    assert mock_manager.delete_backup.call_count == 3

    # Check that the oldest ones were archived
    archived_files = [call[0][0] for call in mock_manager.upload_to_glacier.call_args_list]
    assert "backup_12.tar.gz" in archived_files
    assert "backup_13.tar.gz" in archived_files
    assert "backup_14.tar.gz" in archived_files
