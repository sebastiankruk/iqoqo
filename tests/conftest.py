"""Defines pytest fixtures for the test suite."""

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names intentionally

import pytest

from app import create_app
from app.db import db


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # create a temporary file to isolate the database for each test
    app = create_app(
        config_override={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()
