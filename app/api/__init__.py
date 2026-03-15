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
# 1. Register nested blueprints (like admin, which likely has its own admin_bp)
from . import admin
from .core import api_bp

if hasattr(admin, "admin_bp"):
    api_bp.register_blueprint(admin.admin_bp)

# 2. Import modules that attach routes directly to `api_bp`.
# By simply importing these, Python runs the `@api_bp.route(...)` decorators
# inside them, successfully hooking up the endpoints to the main API blueprint.
from . import auth, items, manifestations, profile, scanner, system
