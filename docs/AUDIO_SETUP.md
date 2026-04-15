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
- Uses a standardized User-Agent (`iqoqo/0.3.0 ( dev@kruk.me )`).
- Fetches covers from the Cover Art Archive.

### Discogs

Requires authentication for reliable metadata and cover fetching. iqoqo supports two methods, but **OAuth consumer key/secret is preferred**:

#### Option 1: OAuth Consumer Key (Preferred)

Provides better stability and adheres to the latest Discogs API standards.

1. Log in to [Discogs Developer Settings](https://www.discogs.com/settings/developers).
2. Click **"Create an Application"**.
3. Fill in the details:
    - **Application Name**: `iqoqo`
    - **Homepage URL**: Use your instance URL (e.g., `https://iqoqo.cc` or `http://localhost:3000`).
    - **Callback URL**: You can use your instance URL (this is not currently used for interactive auth but required by Discogs).
4. Copy the **Consumer Key** and **Consumer Secret**.
5. Add them to your `.env`:

    ```env
    DISCOGS_CONSUMER_KEY=your_key_here
    DISCOGS_CONSUMER_SECRET=your_secret_here
    ```

#### Option 2: Personal Access Token (Legacy)

1. Log in to [Discogs Developer Settings](https://www.discogs.com/settings/developers).
2. Click **"Generate new token"**.
3. Add it to your `.env`:

    ```env
    DISCOGS_USER_TOKEN=your_token_here
    ```

## Note on Throttling
Both services are free but rely on rate limits. If you self-host a high-traffic instance, consider providing your own MusicBrainz API key (if supported) or ensuring you stay within Discogs' rate limits.
