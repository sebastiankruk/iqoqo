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
import pytest

from app.core.tasks import get_task_result, submit_task


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
