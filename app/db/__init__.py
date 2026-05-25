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
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.model import Model


class BaseModel(Model):
    """Custom base model to allow unmapped properties for SQLAlchemy 2.0 compatibility."""

    __allow_unmapped__ = True


db = SQLAlchemy(model_class=BaseModel)


def import_models() -> None:
    """Import all model modules so SQLAlchemy's mapper registry is populated.

    Call this once after ``db`` has been bound to the Flask app (i.e. inside
    ``create_app``).  ``db.create_all()`` and Alembic autogenerate both need
    every model class to have been imported before they inspect the metadata.
    """
    # Order matters: auth / settings have no cross-module FKs, so they can be
    # imported first.  core.py references auth (users.id FK on Item), and
    # audio.py references core (works.id / expressions.id FKs).
    from app.db import auth, settings, core, audio, video, games, social  # noqa: F401, I001 # isort: skip
