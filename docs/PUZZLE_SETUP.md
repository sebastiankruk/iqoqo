# 🧩 Jigsaw Puzzle Metadata Setup

To enable automatic metadata fetching for jigsaw puzzles, iQoQo uses the **UPCitemdb API**. This allows the scanner to resolve standard retail barcodes (UPC/EAN) which are not covered by ISBN (Books) or BGG (Board Games).

## 1. Using the Free Tier (No Setup Required)

By default, iQoQo will use UPCitemdb's public trial endpoint if no API key is provided. This allows for 100 lookups per day without any registration.

## 2. Configuring a Paid Key (Optional)

If you need more than 100 lookups per day, you can subscribe to a paid tier on [UPCitemdb](https://www.upcitemdb.com/). Add your API key to your `.env` file:

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
