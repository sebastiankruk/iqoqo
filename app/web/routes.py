"""Defines the main routes for the web interface."""
from flask import render_template, request
from . import web_bp
from app.db.models import db, Manifestation, Item
from math import ceil, floor

@web_bp.route('/')
def index():
    """Home page with statistics."""
    # Get counts for different categories
    total_books = db.session.query(Manifestation).count()
    not_added = total_books - db.session.query(Manifestation.id).join(Item, Manifestation.id == Item.manifestation_id, isouter=True).filter(Item.id == None).count()
    incomplete = db.session.query(Manifestation).filter(
        (Manifestation.meta['Title'] == None) | (Manifestation.meta['Authors'] == None)
    ).count()
    
    counts = {
        'books': total_books,
        'not added': not_added,
        'incomplete': incomplete
    }
    
    return render_template('index.html', counts=counts, page='index')

@web_bp.route('/scan')
def scan():
    """Barcode scanner page."""
    return render_template('scan.html', page='scan')

@web_bp.route('/add')
def add():
    """Add new item page."""
    return render_template('add_update.html', page='add')

@web_bp.route('/update')
def update():
    """Update existing item page."""
    return render_template('add_update.html', page='update')

@web_bp.route('/list/query/<query_name>')
def list_query(query_name: str):
    """List books with pagination."""
    offset = int(request.args.get('offset', 0))
    page_size = 10
    
    # Build query based on query_name
    query = db.session.query(Manifestation)
    
    if query_name == 'incomplete':
        query = query.filter(
            (Manifestation.meta['Title'] == None) | (Manifestation.meta['Authors'] == None)
        )
    elif query_name == 'not-added':
        query = query.outerjoin(Item).filter(Item.id == None)
    
    count = query.count()
    books = query.order_by(Manifestation.id).offset(offset).limit(page_size).all()
    
    pages = ceil(count / page_size)
    current_page = floor(offset / page_size)
    
    # Format books for template
    book_list = []
    for book in books:
        book_list.append({
            'id': book.id,
            'isbn': book.isbn13,
            'title': book.meta.get('Title', '') if book.meta else '',
            'authors': ', '.join(book.meta.get('Authors', [])) if book.meta and book.meta.get('Authors') else ''
        })
    
    return render_template('list.html', 
                         books=book_list,
                         count=count,
                         offset=offset,
                         pages=pages,
                         current_page=current_page,
                         page='list')
