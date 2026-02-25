from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

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

    if config_override:
        app.config.from_mapping(config_override)

    # Initialize database and migrations
    db.init_app(app)
    _ = Migrate(app, db)  # Initialize migrations

    # Configure CORS from config (disabled by default)
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
                        "supports_credentials": _coerce_bool(
                            app.config.get("CORS_SUPPORTS_CREDENTIALS"),
                            default=False,
                        ),
                    }
                },
            )

    from app.api import api_bp

    app.register_blueprint(api_bp)

    return app
