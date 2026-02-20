import os

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
    # Set static folder to web blueprint's static folder
    static_folder = os.path.join(os.path.dirname(__file__), "web", "static")
    app = Flask(__name__, static_folder=static_folder, static_url_path="/static")
    app.config.from_object(config_class)

    if config_override:
        app.config.from_mapping(config_override)

    # Add session configuration
    app.config["SESSION_TYPE"] = "filesystem"
    if "SECRET_KEY" not in app.config:
        app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"

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

    from app.web import web_bp

    app.register_blueprint(web_bp)

    return app
