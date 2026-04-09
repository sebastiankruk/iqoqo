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

import requests

CLIENT_ID = os.getenv("ALLEGRO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ALLEGRO_CLIENT_SECRET")
# Must match what is configured in Allegro developer portal (e.g. http://localhost)
REDIRECT_URI = "http://localhost"

AUTH_URL = "https://allegro.pl/auth/oauth/authorize"
TOKEN_URL = "https://allegro.pl/auth/oauth/token"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", ".allegro_token.json")


def get_authorization_code():
    authorization_redirect_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    print("\n" + "=" * 80)
    print("Zaloguj do Allegro - otwórz poniższy link w przeglądarce, zaloguj się i zaakceptuj:")
    print(f"\n{authorization_redirect_url}\n")
    print("Przeglądarka przekieruje Cię na adres 'http://localhost/?code=...' (lub wyświetli błąd połączenia).")
    print("Skopiuj wartość po 'code=' z paska adresu przeglądarki i wklej poniżej.")
    print("=" * 80 + "\n")
    authorization_code = input("Allegro Code: ").strip()
    return authorization_code


def get_access_token(authorization_code):
    data = {"grant_type": "authorization_code", "code": authorization_code, "redirect_uri": REDIRECT_URI}
    response = requests.post(TOKEN_URL, data=data, auth=(CLIENT_ID, CLIENT_SECRET), timeout=10)
    response.raise_for_status()
    tokens = response.json()

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f)

    print(f"\nSukces! Tokeny zostały zapisane w {TOKEN_FILE}")
    print("Narzędzie iqoqo jest teraz w pełni połączone z Twoim kontem Allegro do przeszukiwania katalogów.")


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Błąd: Brak ALLEGRO_CLIENT_ID lub ALLEGRO_CLIENT_SECRET w pliku .env")
        sys.exit(1)

    code = get_authorization_code()
    if code:
        get_access_token(code)


if __name__ == "__main__":
    main()
