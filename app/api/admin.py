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

from flask import Blueprint, jsonify, request

from app.api.decorators import admin_required
from app.db.models import InstanceSettings, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/v1/admin")


@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    users = User.query.all()
    user_data = [
        {
            "id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "is_active": u.is_active,
            "roles": [r.name for r in u.roles],
        }
        for u in users
    ]
    return jsonify({"success": True, "data": user_data})


@admin_bp.route("/settings", methods=["GET", "PUT"])
@admin_required
def manage_settings():
    if request.method == "GET":
        settings = InstanceSettings.query.all()
        return jsonify({"success": True, "data": {s.key: s.value for s in settings}})

    data = request.json or {}
    for key, value in data.items():
        setting = InstanceSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = InstanceSettings(key=key, value=value)
            db.session.add(setting)

    db.session.commit()
    return jsonify({"success": True, "data": data})
