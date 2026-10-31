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
"""Tests for federation guard decorator and enablement checks."""

from flask import jsonify

from app.api.federation_guard import federation_required, is_federation_enabled
from app.db.settings import InstanceSettings


def test_is_federation_enabled_with_config(app):
    """is_federation_enabled honors Flask app config flags."""
    with app.app_context():
        app.config["FEDERATION_ENABLED"] = True
        assert is_federation_enabled() is True

        app.config["FEDERATION_ENABLED"] = "true"
        assert is_federation_enabled() is True

        app.config["FEDERATION_ENABLED"] = False
        assert is_federation_enabled() is False

        app.config["FEDERATION_ENABLED"] = "0"
        assert is_federation_enabled() is False


def test_is_federation_enabled_testing_fallback(app):
    """When FEDERATION_ENABLED is not set, TESTING mode enables federation."""
    with app.app_context():
        app.config["FEDERATION_ENABLED"] = None
        app.config["TESTING"] = True
        assert is_federation_enabled() is True

        app.config["TESTING"] = False
        # When neither config nor DB is set, fallback checks InstanceSettings/Config
        InstanceSettings.set_value("FEDERATION_ENABLED", True)
        assert is_federation_enabled() is True

        InstanceSettings.set_value("FEDERATION_ENABLED", False)
        assert is_federation_enabled() is False


def test_federation_required_decorator_allows_when_enabled(app, client):
    """Endpoints decorated with @federation_required return 200 when enabled."""
    with app.app_context():
        app.config["FEDERATION_ENABLED"] = True

        @app.route("/test/federation/guarded/open", methods=["GET"])
        @federation_required
        def open_endpoint():
            return jsonify({"status": "federated-ok"}), 200

    resp = client.get("/test/federation/guarded/open")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "federated-ok"}


def test_federation_required_decorator_blocks_when_disabled(app, client):
    """Endpoints decorated with @federation_required return 404 when disabled."""
    with app.app_context():
        app.config["FEDERATION_ENABLED"] = False
        app.config["TESTING"] = False

        @app.route("/test/federation/guarded/closed", methods=["GET"])
        @federation_required
        def closed_endpoint():
            return jsonify({"status": "should-never-reach"}), 200

    resp = client.get("/test/federation/guarded/closed")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == 404
    assert "Federation is disabled" in data["error"]
