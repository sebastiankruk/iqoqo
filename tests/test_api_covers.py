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
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def setup_celery_eager(app):
    """Ensure Celery runs tasks synchronously for tests."""
    from app.core.celery_app import celery
    celery.conf.broker_url = 'memory://'
    celery.conf.result_backend = 'cache+memory://'
    celery.conf.task_always_eager = True
    celery.conf.task_store_eager_result = True
    yield
    celery.conf.task_always_eager = False
    celery.conf.task_store_eager_result = False

def test_regenerate_cover_returns_task_id(client, admin_headers):
    from app.db.models import Manifestation, Expression, Work, db
    
    with client.application.app_context():
        work = Work(title="Regen Test", meta={"authors": ["Author Regen"]})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="2222222222222")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    with patch("app.api.manifestations.start_cover_processing", return_value="fake-task-id"):
        response = client.post(f"/api/manifestations/{manif_id}/regenerate-cover", headers=admin_headers)
        assert response.status_code == 202
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["task_id"] == "fake-task-id"

def test_get_cover_status_polling(client, normal_user_headers):
    from app.db.models import Manifestation, Expression, Work, db
    
    with client.application.app_context():
        work = Work(title="Status Test")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="3333333333333", cover_url="/static/covers/old.jpg")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    # Test 1: Fallback (no task_id)
    response = client.get(f"/api/manifestations/{manif_id}/cover-status", headers=normal_user_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["data"]["cover_url"] == "/static/covers/old.jpg"

    # Test 2: With task_id PENDING
    with patch("app.core.tasks.get_task_result", return_value={"status": "pending"}):
        response = client.get(f"/api/manifestations/{manif_id}/cover-status?task_id=t1", headers=normal_user_headers)
        assert response.status_code == 202
        assert response.get_json()["data"]["status"] == "pending"

    # Test 3: With task_id COMPLETED
    with patch("app.core.tasks.get_task_result", return_value={"status": "completed"}):
        response = client.get(f"/api/manifestations/{manif_id}/cover-status?task_id=t2", headers=normal_user_headers)
        assert response.status_code == 200
        assert response.get_json()["data"]["status"] == "ready"
