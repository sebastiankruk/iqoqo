import os

from flask import Flask
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

    db.init_app(app)
    _ = Migrate(app, db)  # Initialize migrations

    from app.api import api_bp

    app.register_blueprint(api_bp)

    from app.web import web_bp

    app.register_blueprint(web_bp)

    return app
