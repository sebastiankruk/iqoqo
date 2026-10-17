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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Helper script to bootstrap and launch a secondary local peer instance for multi-instance E2E federation testing."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch secondary peer backend for multi-instance E2E testing.")
    parser.add_argument("--port", type=int, default=5003, help="Port to bind peer Flask backend (default: 5003)")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL for peer instance (default: http://127.0.0.1:<port>)")
    parser.add_argument(
        "--db-url",
        type=str,
        default="sqlite:////tmp/iqoqo_federation_peer_test.db",
        help="Database URL for peer instance (default: sqlite:////tmp/iqoqo_federation_peer_test.db)",
    )
    parser.add_argument("--peer-username", type=str, default="bob", help="Username for seeded peer actor (default: bob)")
    parser.add_argument("--peer-email", type=str, default="bob@peer.local", help="Email for seeded peer actor")
    parser.add_argument("--peer-password", type=str, default="PeerPass123!", help="Password for seeded peer actor")
    parser.add_argument("--seed-only", action="store_true", help="Only initialize DB and seed peer actor, then exit")
    parser.add_argument("--check-ready", action="store_true", help="Check if peer backend is already running and healthy")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout in seconds for --check-ready")
    return parser.parse_args()


def wait_for_peer(port: int, timeout: int = 15) -> bool:
    """Check if peer backend at 127.0.0.1:<port> is responding to /api/health."""
    url = f"http://127.0.0.1:{port}/api/health"
    start_time = time.time()
    req = Request(url, headers={"User-Agent": "iqoqo-peer-checker"})
    while time.time() - start_time < timeout:
        try:
            with urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except (URLError, TimeoutError, ConnectionError, OSError):
            time.sleep(0.5)
    return False


def seed_peer_database(app, peer_username: str, peer_email: str, peer_password: str, base_url: str) -> None:
    """Create DB tables and ensure peer user exists with federation keys and consent."""
    from sqlalchemy import select

    from app.core import federation_keys
    from app.core.iri import canonical_actor_iri
    from app.db import db
    from app.db.auth import User
    from app.db.federation import FederationConsent

    with app.app_context():
        db.create_all()

        user = db.session.execute(select(User).where(User.public_username == peer_username)).scalars().first()
        if not user:
            user = User(
                email=peer_email,
                public_username=peer_username,
                display_name=f"Peer User {peer_username.capitalize()}",
            )
            user.set_password(peer_password)
            db.session.add(user)
            db.session.commit()

        # Ensure federation keys
        canonical_uri = canonical_actor_iri(user.id, base_url)
        public_key = federation_keys.get_actor_public_key(str(user.id))
        if not public_key:
            _, public_key = federation_keys.generate_actor_keypair(str(user.id))
            user.federation_public_key = public_key
            user.federation_key_id = f"{canonical_uri}#main-key"
            db.session.commit()

        # Ensure federation consent
        consent = db.session.execute(select(FederationConsent).where(FederationConsent.user_id == user.id)).scalars().first()
        if not consent:
            consent = FederationConsent(
                user_id=user.id,
                federated_profile=True,
                federated_collection=True,
            )
            db.session.add(consent)
            db.session.commit()


def main() -> int:
    args = parse_args()
    port = args.port
    base_url = args.base_url or f"http://127.0.0.1:{port}"

    if args.check_ready:
        if wait_for_peer(port, timeout=args.timeout):
            print(f"Peer backend on port {port} is healthy.")
            return 0
        print(f"Peer backend on port {port} is not responding.", file=sys.stderr)
        return 1

    # Configure environment before importing application
    os.environ["DATABASE_URL"] = args.db_url
    os.environ["BASE_URL"] = base_url
    os.environ["FEDERATION_ENABLED"] = "true"
    os.environ["FEDERATION_AUTO_ACCEPT_FOLLOWS"] = "true"
    os.environ["FEDERATION_ALLOW_LOOPBACK"] = "true"
    os.environ["TESTING"] = "true"
    os.environ["RATELIMIT_ENABLED"] = "False"
    os.environ["SECRET_KEY"] = "peer-secret-testing-32-bytes-long!!"
    os.environ["JWT_SECRET_KEY"] = "peer-jwt-secret-testing-32-bytes!"
    os.environ["ADMIN_EMAIL"] = "peer-admin@peer.local"
    os.environ["ADMIN_PASSWORD"] = "PeerAdmin123!"

    # Add project root to sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from app import create_app

    app = create_app()

    seed_peer_database(
        app=app,
        peer_username=args.peer_username,
        peer_email=args.peer_email,
        peer_password=args.peer_password,
        base_url=base_url,
    )
    print(f"Seeded peer database at {args.db_url} with user '{args.peer_username}'")

    if args.seed_only:
        return 0

    def handle_signal(sig, frame):
        print(f"Stopping peer backend on port {port}...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    print(f"Starting federation peer backend on port {port} (BASE_URL={base_url})...")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
