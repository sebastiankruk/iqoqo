# Video and Board Games API Setup

To fully enable automatic metadata ingestion for Video (BluRays, DVDs) and Board Games, you need to configure API keys for external lookup services.

## 1. TMDB (The Movie Database)

Used for fetching metadata for movies, TV shows, directors, and cast.

1. Create a free account at [The Movie Database (TMDB)](https://www.themoviedb.org/).
2. Go to your Account Settings -> API.
3. Generate a new API Key (v3 auth).
4. Add the key to your `.env` file:

```env
TMDB_API_KEY=your_api_key_here
```

## 2. BGG (BoardGameGeek)

Used for fetching board game metadata, designers, and mechanics.

1. The BGG XML API2 is open and does not strictly require an API key for basic usage.
2. To prevent rate limiting, iqoqo batches requests.
3. No `.env` variable is strictly required unless you are using a specific authenticated BGG proxy, but we reserve `BGG_USERNAME` if user-collection syncing is desired in the future:

```env
BGG_USERNAME=optional_username
```

## 3. Restarting the Application

Once your `.env` file is updated, restart your Docker containers to apply the keys:

```bash
docker compose down
docker compose up -d
```
