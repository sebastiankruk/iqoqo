from app import create_app
from app.db import db
from app.core.data_manager import DataManager
from app.db.models import User

app = create_app()
with app.app_context():
    user = User.query.filter(User.email.ilike('%sebastian%')).first()
    if not user:
        user = User.query.first()
    print(f"Testing for user: {user.email} (ID: {user.id})")
    
    stats_items = DataManager.get_faceted_stats(owner_id=user.id, publishers=["Virgin"], view="items")
    print("ITEMS STATS:", stats_items)
