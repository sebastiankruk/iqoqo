import os
import sys

from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app import create_app
from app.api.auth import generate_internal_jwt
from app.db.models import User, db


def generate_token(email):
    app = create_app()
    with app.app_context():
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if not user:
            print(f"User with email {email} not found.")
            return

        token = generate_internal_jwt(user)
        print(f"TOKEN for {email}:")
        print(token)


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@iqoqo.local"  # Default admin email
    generate_token(email)
