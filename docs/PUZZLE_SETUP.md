# 🧩 Jigsaw Puzzle Metadata Setup

To enable automatic metadata fetching for jigsaw puzzles, iQoQo uses the **UPCitemdb API**. This allows the scanner to resolve standard retail barcodes (UPC/EAN) which are not covered by ISBN (Books) or BGG (Board Games).

## 1. Get an API Key

1. Visit [UPCitemdb](https://www.upcitemdb.com/api-explorer).
2. Register for a free account (Trial allows 100 lookups/day).
3. Retrieve your API Key from the dashboard.

## 2. Configure iQoQo

Add the following to your `.env` file or environment variables:

```bash
UPC_ITEM_DB_KEY=your_api_key_here
```

## 3. How the Lookup Works

When you select **Puzzle** mode in the scanner:

1. The system specifically routes the barcode to `app/utils/upc.py`.
2. It maps the raw retail JSON to iQoQo's FRBR structure:
   - `brand` -> `Manufacturer` (Manifestation)
   - `images[0]` -> `Cover URL`
   - `description` -> `Abstract` (Work)
3. Custom fields like `piece_count` are only populated when explicitly provided by the lookup result.

## 4. Troubleshooting

- **No Results:** Ensure the barcode is entered without spaces.
- **Rate Limiting:** Free keys have strict limits; if you scan frequently, consider the "Magic Scan" (Vision API) fallback.
