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
import json
import os
import sys
import time

import requests

CLIENT_ID = os.getenv("ALLEGRO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ALLEGRO_CLIENT_SECRET")

DEVICE_AUTH_URL = "https://allegro.pl/auth/oauth/device"
TOKEN_URL = "https://allegro.pl/auth/oauth/token"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", ".allegro_token.json")

GRANT_TYPE_DEVICE = "urn:ietf:params:oauth:grant-type:device_code"


def device_code_flow():
    print("Requesting device code from Allegro...")
    response = requests.post(
        DEVICE_AUTH_URL,
        data={"client_id": CLIENT_ID},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=10,
    )
    if not response.ok:
        print(f"Device auth request failed (HTTP {response.status_code}): {response.text}", file=sys.stderr)
        response.raise_for_status()

    data = response.json()
    device_code = data["device_code"]
    verification_uri = data.get("verification_uri_complete") or data.get("verification_uri", "")
    user_code = data.get("user_code", "")
    interval = int(data.get("interval", 5))
    expires_in = int(data.get("expires_in", 600))

    print(f"\nOtworz ten adres w przegladarce:\n  {verification_uri}")
    if user_code:
        print(f"Jesli potrzeba, wpisz kod: {user_code}")
    print(f"Czekam na autoryzacje (wygasa za {expires_in}s)...")

    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)

        token_response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": GRANT_TYPE_DEVICE,
                "device_code": device_code,
                "client_id": CLIENT_ID,
            },
            auth=(CLIENT_ID, CLIENT_SECRET),
            timeout=10,
        )

        if token_response.ok:
            tokens = token_response.json()
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump(tokens, f)
            print(f"\nSukces! Tokeny zapisane w {TOKEN_FILE}")
            print("iqoqo jest teraz polaczone z kontem Allegro do przeszukiwania katalogow.")
            return

        try:
            err = token_response.json().get("error", "")
        except json.JSONDecodeError:
            err = ""

        if err == "authorization_pending":
            print(".", end="", flush=True)
            continue
        elif err == "slow_down":
            interval += 5
            print(f"\nSerwer zada wolniejszego odpytywania, zwiekszam interwal do {interval}s...")
            continue
        elif err == "expired_token":
            print(f"\nKod urzadzenia wygasl. Sprobuj ponownie.", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"\nBlad wymiany tokena (HTTP {token_response.status_code}): {token_response.text}", file=sys.stderr)
            token_response.raise_for_status()

    print("\nKod urzadzenia wygasl. Sprobuj ponownie.", file=sys.stderr)
    sys.exit(1)


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Blad: Brak ALLEGRO_CLIENT_ID lub ALLEGRO_CLIENT_SECRET w pliku .env")
        sys.exit(1)

    device_code_flow()


if __name__ == "__main__":
    main()
