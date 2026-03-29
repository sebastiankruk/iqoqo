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
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix

# Import blueprints
from app.api import api_bp
from app.api.auth import auth_bp, init_oauth
from app.api.profile import profile_bp

from .config import Config
from .db import db


def _coerce_bool(value, default=False):
    """Convert config/env-style values to bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _coerce_list(value, default=None):
    """Convert comma-separated string or sequence into a clean list[str]."""
    if value is None:
        return default[:] if default else []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def create_app(config_class=Config, config_override=None):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Trust the proxy headers (Cloudflare -> Next.js -> Flask)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    if config_override:
        app.config.from_mapping(config_override)

    # Initialize database and migrations
    db.init_app(app)
    _ = Migrate(app, db)

    # Configure CORS from config
    cors_enabled = _coerce_bool(app.config.get("CORS_ENABLED"), default=False)
    if cors_enabled:
        cors_origins = _coerce_list(app.config.get("CORS_ORIGINS"))
        if cors_origins:
            CORS(
                app,
                resources={
                    r"/api/*": {
                        "origins": cors_origins,
                        "methods": _coerce_list(
                            app.config.get("CORS_METHODS"),
                            default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                        ),
                        "allow_headers": _coerce_list(
                            app.config.get("CORS_ALLOW_HEADERS"),
                            default=["Content-Type", "Authorization"],
                        ),
                        # Credential forwarding (cookies/Authorization) on cross-origin
                        # requests requires an explicit operator opt-in via the
                        # CORS_SUPPORTS_CREDENTIALS=true environment variable.
                        # OAuth/federation deployments must set this explicitly; the
                        # default remains False to avoid unintended CSRF exposure.
                        "supports_credentials": _coerce_bool(
                            app.config.get("CORS_SUPPORTS_CREDENTIALS"),
                            default=False,
                        ),
                    }
                },
            )

    init_oauth(app)

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)

    return app
