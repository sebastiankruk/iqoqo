from app.db.models import db, Work, Expression, Manifestation, Item

def create_work(title, meta={}):
    """
    Creates a new Work.
    """
    work = Work(title=title, meta=meta)
    db.session.add(work)
    db.session.commit()
    return work

# Add other functions for creating Expression, Manifestation, and Item
