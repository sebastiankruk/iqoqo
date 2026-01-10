from flask import Flask
from .config import Config
from .db import db
from flask_migrate import Migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate = Migrate(app, db)

    from app.api import api_bp
    app.register_blueprint(api_bp)

    from app.web import web_bp
    app.register_blueprint(web_bp)

    return app
