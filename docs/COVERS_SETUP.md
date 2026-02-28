# Cover Generation & Retrieval Setup

iqoqo uses a multi-tier pipeline to ensure every item has a cover image. This guide explains how to configure external providers and local AI models.

## 1. External APIs (Free)

No configuration is required for **OpenLibrary** or **Google Books**. These are enabled by default as Tier 2 sources.

## 2. Cloud AI Generation (Paid)

To enable high-quality AI cover generation, obtain an API key from OpenAI or Google.

### OpenAI (DALL-E 3)

1. Get key from [platform.openai.com](https://platform.openai.com/api-keys).
2. Add to `.env`:

   ```bash
   OPENAI_API_KEY=sk-proj-...
   ```

### Google Gemini (Imagen 3)

1. Get key from Google AI Studio.
2. Add to `.env`:

   ```bash
   GEMINI_API_KEY=AIza...
   ```

*Note: Telemetry for estimated costs is tracked in the `llm_telemetry` database table.*

## 3. Local AI Generation (Free)

To use your own hardware for generation (Tier 4), iqoqo supports **Stable Diffusion** via the Automatic1111 API.

1. Install Stable Diffusion WebUI.
2. Launch with the API flag: `./webui.sh --api`.
3. Add to `.env`:

   ```bash
   LOCAL_SD_URL=http://localhost:7860
   ```

## 4. Batch Processing

To generate covers for existing items in your database:

```bash
python scripts/fetch_covers.py
```

This script is **resumable**. You can stop it with `Ctrl+C` and run it again later; it will skip items that already have covers.

## 5. Troubleshooting

- **Missing Covers:** Check `app/static/covers/` permissions. Ensure Docker volumes are mounted correctly.
- **API Errors:** Check application logs for "Cloud LLM Gen failed" messages.
