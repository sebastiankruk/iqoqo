"""Defines the configuration for the Flask application."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ENABLED = os.environ.get("CORS_ENABLED", "false")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")
    CORS_METHODS = os.environ.get("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
    CORS_ALLOW_HEADERS = os.environ.get("CORS_ALLOW_HEADERS", "Content-Type,Authorization")
    CORS_SUPPORTS_CREDENTIALS = os.environ.get("CORS_SUPPORTS_CREDENTIALS", "false")

    @staticmethod
    def _get_version():
        """Resolve version: Env Var > File + .dev > Default."""
        env_version = os.environ.get("APP_VERSION")
        # If env var is set and not the default 'dev', use it
        if env_version and env_version != "dev":
            return env_version

        import tomllib

        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            pyproject_path = os.path.join(base_dir, "pyproject.toml")
            with open(pyproject_path, "rb") as pyproject_file:
                env_version = tomllib.load(pyproject_file).get("project", {}).get("version")
        except (FileNotFoundError, OSError):
            env_version = None

        if env_version:
            return env_version

        return "dev-local"

    VERSION = _get_version()
