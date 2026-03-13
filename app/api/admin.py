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
