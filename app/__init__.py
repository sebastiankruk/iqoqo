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
import logging

# Suppress highly verbose urllib3 connectionpool logs at DEBUG level (caused by OTel exporter POSTs)
logging.getLogger("urllib3").setLevel(logging.WARNING)

from dotenv import load_dotenv

load_dotenv()
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

# Import blueprints
from app.api import api_bp
from app.api.auth import auth_bp, init_oauth
from app.api.profile import profile_bp
from app.core.scheduler import init_scheduler

from .config import Config
from .db import db

# Protect against decompression bombs globally
Image.MAX_IMAGE_PIXELS = 25_000_000


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
    load_dotenv()

    # Configure logging early
    log_level_name = (
        config_override.get("LOG_LEVEL")
        if config_override and "LOG_LEVEL" in config_override
        else getattr(config_class, "LOG_LEVEL", getattr(Config, "LOG_LEVEL", "INFO"))
    )
    log_level = getattr(logging, str(log_level_name).upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Trust the proxy headers (Cloudflare -> Next.js -> Flask)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    if config_override:
        app.config.from_mapping(config_override)

    # Initialize database and migrations
    db.init_app(app)
    _ = Migrate(app, db)

    # Ensure all model modules are imported so SQLAlchemy's mapper registry
    # is fully populated before db.create_all() or Alembic autogenerate runs.
    from app.db import import_models  # noqa: E402

    import_models()

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

    # Initialize background task scheduler
    if app.config.get("SCHEDULER_AUTOSTART"):
        init_scheduler(app)

    # Initialize Celery
    from app.core.celery_app import init_celery

    init_celery(app)

    # Initialize Limiter and Cache with resilient Redis fallback
    from app.core.cache import cache
    from app.core.limiter import limiter

    redis_url = app.config.get("REDIS_URL")
    if redis_url:
        redis_available = False
        try:
            import redis

            redis_client = redis.Redis.from_url(redis_url, socket_connect_timeout=1)
            redis_client.ping()
            redis_available = True
        except (redis.exceptions.RedisError, OSError, ValueError, RuntimeError) as exc:
            app.logger.warning(
                "Redis connection failed during startup (%s). Falling back to in-memory caching and rate limiting.",
                exc,
            )

        if redis_available:
            app.config.setdefault("RATELIMIT_STORAGE_URI", redis_url)
            app.config.setdefault("CACHE_TYPE", "RedisCache")
            app.config.setdefault("CACHE_REDIS_URL", redis_url)
        else:
            app.config["RATELIMIT_STORAGE_URI"] = "memory://"
            app.config["CACHE_TYPE"] = "SimpleCache"
    else:
        app.config.setdefault("RATELIMIT_STORAGE_URI", "memory://")
        app.config.setdefault("CACHE_TYPE", "SimpleCache")

    limiter.init_app(app)
    cache.init_app(app)

    from app.api.docs import docs_bp
    from app.api.lending import lending_bp
    from app.api.roadmap import roadmap_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(roadmap_bp)
    app.register_blueprint(lending_bp)
    app.register_blueprint(docs_bp, url_prefix="/api/docs")

    from app.core.telemetry import init_telemetry

    init_telemetry(app)

    @app.teardown_appcontext
    def shutdown_session(exception=None):  # pylint: disable=unused-argument
        """Ensure scoped sessions are returned to the pool after each request."""
        db.session.remove()

    with app.app_context():
        try:
            from app.utils.covers import cleanup_stuck_pending_covers

            cleanup_stuck_pending_covers(timeout_minutes=30)
        except (SQLAlchemyError, ValueError, AttributeError, KeyError, RuntimeError) as e:
            app.logger.warning(f"Could not run stuck cover task cleanup at startup: {e}")

    return app
