"""Defines the API endpoints for the application."""
from flask import jsonify
from app.db.models import Item
from . import api_bp

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

@api_bp.route('/items', methods=['GET'])
def get_items():
    items = Item.query.all()
    return jsonify([{"id": item.id, "owner_id": item.owner_id} for item in items])
