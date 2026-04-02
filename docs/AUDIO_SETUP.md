# Audio Setup and Scanning Support

As of `v0.2.0`, iqoqo supports automatic metadata fetching for audio items (CDs, Vinyls, etc.).

## How It Works
The standard `POST /api/scan` endpoint has been upgraded with an auto-fallback feature:

1. When a barcode is scanned, the server first attempts to resolve it as an **ISBN** via OpenLibrary/Google Books.
2. If this fails (common for UPC/EAN barcodes on CDs), it automatically falls back to querying the **MusicBrainz API** and **Discogs API**.
3. It fetches album titles, artist data, and album covers.

## External Services

### MusicBrainz

- **No API key required** by default.
- Uses a standardized User-Agent (`iqoqo/0.2.0 ( dev@kruk.me )`).
- Fetches covers from the Cover Art Archive.

### Discogs

- **Requires an Access Token** for reliable searching.
- Set the `DISCOGS_USER_TOKEN` environment variable in your `.env` file.
- To get a token:

    1. Log in to [Discogs](https://www.discogs.com/settings/developers).
    2. Click "Generate new token".

## Note on Throttling
Both services are free but rely on rate limits. If you self-host a high-traffic instance, consider providing your own MusicBrainz API key (if supported) or ensuring you stay within Discogs' rate limits.
