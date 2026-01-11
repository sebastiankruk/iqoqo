from datetime import datetime
from . import db

class Work(db.Model):
    """
    FRBR Group 1: Work
    A distinct intellectual or artistic creation.
    e.g., "The Hobbit" (the story itself, regardless of language).
    """
    __tablename__ = 'works'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    # Flexible metadata (e.g., original_language, first_performance_date)
    meta = db.Column(db.JSON, default={})

    # Relationships
    expressions = db.relationship('Expression', backref='work', lazy=True)

class Expression(db.Model):
    """
    FRBR Group 1: Expression
    The intellectual realization of a work.
    e.g., The English text of The Hobbit, or the German translation.
    """
    __tablename__ = 'expressions'
    id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, db.ForeignKey('works.id'), nullable=False)
    content_type = db.Column(db.String(50)) # e.g., 'text', 'sound', 'notated_music'
    language = db.Column(db.String(10))     # e.g., 'en', 'pl'
    meta = db.Column(db.JSON, default={})

    # Relationships
    manifestations = db.relationship('Manifestation', backref='expression', lazy=True)

class Manifestation(db.Model):
    """
    FRBR Group 1: Manifestation
    The physical or digital embodiment of an expression.
    e.g., The 1937 Allen & Unwin Hardcover edition.
    """
    __tablename__ = 'manifestations'
    id = db.Column(db.Integer, primary_key=True)
    expression_id = db.Column(db.Integer, db.ForeignKey('expressions.id'), nullable=False)

    # Identifiers
    isbn13 = db.Column(db.String(13), index=True, unique=True)
    upc = db.Column(db.String(12), index=True)
    ean = db.Column(db.String(13), index=True)

    publisher = db.Column(db.String(255))
    publication_date = db.Column(db.Date)
    meta = db.Column(db.JSON, default={}) # Stores cover images, page count, dimensions

    # Relationships
    items = db.relationship('Item', backref='manifestation', lazy=True)

class Item(db.Model):
    """
    FRBR Group 1: Item
    A single exemplar of a manifestation.
    e.g., The specific book on your shelf.
    """
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    manifestation_id = db.Column(db.Integer, db.ForeignKey('manifestations.id'), nullable=False)

    # User ownership data
    owner_id = db.Column(db.String(100)) # Could link to a User table later
    status = db.Column(db.String(50), default='available') # available, lent, lost, wish_list
    condition = db.Column(db.String(50))

    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(db.JSON, default={}) # Custom tags, notes, location on shelf
