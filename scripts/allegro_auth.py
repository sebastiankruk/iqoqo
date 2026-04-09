import json
import os
import requests
import sys

# Add the project root to sys.path so we can import app modules if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try to load environment variables
from dotenv import load_dotenv
load_dotenv()

CLIENT_ID = os.getenv("ALLEGRO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ALLEGRO_CLIENT_SECRET")
# Must match what is configured in Allegro developer portal (e.g. http://localhost)
REDIRECT_URI = "http://localhost" 

AUTH_URL = "https://allegro.pl/auth/oauth/authorize"
TOKEN_URL = "https://allegro.pl/auth/oauth/token"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', '.allegro_token.json')


def get_authorization_code():
    authorization_redirect_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    print("\n" + "="*80)
    print("Zaloguj do Allegro - otwórz poniższy link w przeglądarce, zaloguj się i zaakceptuj:")
    print(f"\n{authorization_redirect_url}\n")
    print("Przeglądarka przekieruje Cię na adres 'http://localhost/?code=...' (lub wyświetli błąd połączenia).")
    print("Skopiuj wartość po 'code=' z paska adresu przeglądarki i wklej poniżej.")
    print("="*80 + "\n")
    authorization_code = input('Allegro Code: ').strip()
    return authorization_code


def get_access_token(authorization_code):
    data = {
        'grant_type': 'authorization_code', 
        'code': authorization_code, 
        'redirect_uri': REDIRECT_URI
    }
    response = requests.post(
        TOKEN_URL, 
        data=data, 
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    response.raise_for_status()
    tokens = response.json()
    
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
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
