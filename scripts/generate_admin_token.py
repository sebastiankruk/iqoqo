#!/usr/bin/env python3
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
