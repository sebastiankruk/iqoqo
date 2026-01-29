"""Defines the API endpoints for the application."""
from flask import jsonify, request, session
from app.db.models import db, Item, Manifestation, Expression, Work
from . import api_bp
import requests

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

@api_bp.route('/items', methods=['GET'])
def get_items():
    items = Item.query.all()
    return jsonify([{"id": item.id, "owner_id": item.owner_id} for item in items])

@api_bp.route('/isbn/<isbn>', methods=['GET'])
def lookup_isbn(isbn: str):
    """Look up book metadata by ISBN from Open Library or local DB."""
    # First check if we have it locally
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    
    if manifestation and manifestation.meta and manifestation.meta.get('Title'):
        # Return cached data
        return jsonify(**manifestation.meta)
    
    # Try to fetch from Open Library API
    try:
        # Try ISBN 13 first
        response = requests.get(
            f'https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data',
            timeout=10
        )
        data = response.json()
        
        if not data:
            # If not found, return 404
            return jsonify({}), 404
        
        book_data = list(data.values())[0]
        
        # Extract metadata
        metadata = {
            'Title': book_data.get('title', ''),
            'Authors': [author.get('name', '') for author in book_data.get('authors', [])]
        }
        
        # Store in database if not exists
        if not manifestation:
            # We need to create Work -> Expression -> Manifestation
            work = Work(title=metadata['Title'], meta={})
            db.session.add(work)
            db.session.flush()
            
            expression = Expression(work_id=work.id, content_type='text', language='en', meta={})
            db.session.add(expression)
            db.session.flush()
            
            manifestation = Manifestation(
                expression_id=expression.id,
                isbn13=isbn,
                meta=metadata
            )
            db.session.add(manifestation)
            db.session.commit()
        else:
            # Update existing manifestation
            manifestation.meta = metadata
            db.session.commit()
        
        return jsonify(**metadata)
    
    except (requests.RequestException, KeyError, ValueError) as e:
        # If API call fails, return 400
        return jsonify({"error": str(e)}), 400

@api_bp.route('/isbn/<isbn>', methods=['POST'])
def update_manifestation(isbn: str):
    """Update manifestation metadata."""
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    
    if not manifestation:
        return jsonify({"error": "Manifestation not found"}), 404
    
    metadata = request.get_json()
    
    if metadata:
        # Update the manifestation's metadata
        if not manifestation.meta:
            manifestation.meta = {}
        manifestation.meta.update(metadata)
        
        # Also update the work title if provided
        if 'Title' in metadata and manifestation.expression and manifestation.expression.work:
            manifestation.expression.work.title = metadata['Title']
        
        db.session.commit()
        return jsonify({"status": "ok"})
    
    return jsonify({"error": "No metadata provided"}), 400

@api_bp.route('/item/<isbn>', methods=['GET'])
def get_items_by_isbn(isbn: str):
    """Get all items for a given ISBN."""
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    
    if not manifestation:
        return jsonify({"error": "Manifestation not found"}), 404
    
    items = Item.query.filter_by(manifestation_id=manifestation.id).all()
    
    if not items:
        return jsonify({"error": "No items found"}), 404
    
    return jsonify({"ids": [item.id for item in items]})

@api_bp.route('/item/<isbn>', methods=['POST'])
def add_item(isbn: str):
    """Add a new item for a given ISBN."""
    manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    
    if not manifestation:
        # If manifestation doesn't exist, try to fetch it first
        lookup_response = lookup_isbn(isbn)
        if lookup_response[1] != 200:  # Check if lookup failed
            return jsonify({"error": "Manifestation not found"}), 404
        manifestation = Manifestation.query.filter_by(isbn13=isbn).first()
    
    metadata = request.get_json()
    
    # Update manifestation metadata if provided
    if metadata:
        if not manifestation.meta:
            manifestation.meta = {}
        manifestation.meta.update(metadata)
        
        # Also update the work title if provided
        if 'Title' in metadata and manifestation.expression and manifestation.expression.work:
            manifestation.expression.work.title = metadata['Title']
    
    # Get or create client ID (simplified - you may want to use proper authentication)
    client_id = session.get('client_id', 'default_user')
    
    # Create new item
    item = Item(
        manifestation_id=manifestation.id,
        owner_id=client_id,
        status='available',
        meta={}
    )
    
    db.session.add(item)
    db.session.commit()
    
    return jsonify({"item_id": item.id})
