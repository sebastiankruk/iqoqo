import os

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from .config import Config
from .db import db


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

    # Configure CORS for frontend development
    # Allow requests from localhost:3000 (Next.js default dev server)
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True,
            }
        },
    )

    from app.api import api_bp

    app.register_blueprint(api_bp)

    from app.web import web_bp

    app.register_blueprint(web_bp)

    return app
