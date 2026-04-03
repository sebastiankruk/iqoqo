# Setting Up Covers Generation Infrastructure

iqoqo utilizes a multi-tiered fallback system to ensure every item in your distributed catalog has high-quality, normalized cover art. This guide explains how to configure external providers and local AI models.

* [The Pipeline Tiers](#the-pipeline-tiers)
* [Rate Limiting \& Storage](#rate-limiting--storage)
* [Cover Badges](#cover-badges)
* [1. External Metadata APIs](#1-external-metadata-apis)
* [2. Cloud AI Generation (Paid)](#2-cloud-ai-generation-paid)
  * [OpenAI (DALL-E 3)](#openai-dall-e-3)
  * [Google Gemini (Imagen 3)](#google-gemini-imagen-3)
* [2a. Vision-based Metadata Extraction](#2a-vision-based-metadata-extraction)
* [3. Local AI Generation (Free)](#3-local-ai-generation-free)
  * [Step 1: Install Prerequisites](#step-1-install-prerequisites)
  * [Step 2: Clone the Repository](#step-2-clone-the-repository)
  * [Step 3: Enable the API \& Launch](#step-3-enable-the-api--launch)
    * [For Windows](#for-windows)
    * [For Mac / Linux](#for-mac--linux)
  * [Step 4: Connect iqoqo](#step-4-connect-iqoqo)
  * [Filtering Junk / Placeholder Covers](#filtering-junk--placeholder-covers)
* [4. Batch Processing](#4-batch-processing)
* [5. Troubleshooting](#5-troubleshooting)
* [6. Importing Covers to a Remote iqoqo Instance](#6-importing-covers-to-a-remote-iqoqo-instance)

## The Pipeline Tiers

When a new item is added, a background worker (\`app/utils/covers.py\`) processes covers in the following order:

1. **User Photo (\`user_photo\`)**: Direct upload from the user via the frontend UI.
2. **Direct Hotlink Download (\`api_direct_download\`)**: *[New in v0.2]* For Audio (CDs/Vinyl), external APIs like MusicBrainz or Discogs often return direct hotlinks. To bypass rate limits and prevent hotlinking decay, iqoqo intercepts these URLs, streams the image chunks securely, limits file sizes to 5MB, validates the bytes via Pillow, and saves a local copy.
3. **OpenLibrary API (\`api_openlibrary\`)**: Standard ISBN lookup.
4. **Google Books API (\`api_google_books\`)**: Search by ISBN fallback.
5. **Local LLM / Stable Diffusion (\`llm_local_stable_diffusion\`)**: Privacy-first AI generated cover based on metadata.
6. **Cloud LLM (\`llm_gemini\` / \`llm_openai\`)**: Opt-in cloud AI generation.
7. **Pillow Fallback (\`fallback_pil\`)**: A locally rendered flat image with the title/author text.

## Rate Limiting & Storage

Because iqoqo now proactively downloads covers from MusicBrainz/Discogs (Tier 2):

* Images are stored in \`app/static/covers/\`.
* You should mount a persistent volume to \`/app/app/static/covers\` if using Docker.
* Malicious payloads and ZIP bombs are mitigated by a strict \`MAX_COVER_FILE_SIZE\` threshold (5MB) that aborts streaming chunks immediately upon violation.

## Cover Badges

To maintain transparency in the catalog, downloaded or generated images receive a discrete badge in the bottom right corner (e.g., a Teal "C" for Direct Downloads, a Gray "D" for OpenLibrary).

## 1. External Metadata APIs

**OpenLibrary** requires no configuration.

**Google Books** works out of the box, but unauthenticated requests are subject to lower rate limits. To avoid `429 Too Many Requests` errors:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create a project and enable the **Books API**.
3. Create an **API Key** (Credentials -> Create Credentials -> API Key).
4. Add the key to your `.env` file:

   ```bash
   GOOGLE_BOOKS_API_KEY=AIzaSy...
   ```

## 2. Cloud AI Generation (Paid)

To enable high-quality AI cover generation, obtain an API key from OpenAI or Google.

### OpenAI (DALL-E 3)

1. Get key from [platform.openai.com](https://platform.openai.com/api-keys).
2. Add to `.env`:

   ```bash
   OPENAI_API_KEY=sk-proj-...
   ```

### Google Gemini (Imagen 3)

1. Get key from [Google AI Studio](https://aistudio.google.com/api-keys).
2. Add to `.env`:

   ```bash
   GEMINI_API_KEY=AIza...
   ```

*Note: Telemetry for estimated costs is tracked in the `llm_telemetry` database table.*

## 2a. Vision-based Metadata Extraction

iqoqo can extract a book's **Title** and **Authors** directly from a photo of its cover. This powers the **"Snap Cover"** button on the scan page — users can photograph a book and have its metadata filled in automatically.

This feature uses a progressive fallback waterfall to ensure extraction:

1. **Gemini API (Primary)**: High quality extraction.
   * **Required:** The `GEMINI_API_KEY` environment variable. Uses the `gemini-2.0-flash` multimodal model.
2. **Local Vision LLM via Ollama (Free local fallback)**: Used if Gemini is unavailable or fails. The `llava` model is highly recommended.
   * **Required:** An Ollama instance. Set `OLLAMA_URL` (default: `http://localhost:11434`) and `OLLAMA_VISION_MODEL` (default: `llava`).
   * **Setup:** `ollama pull llava`
3. **Tesseract OCR (Basic offline fallback)**: Used when LLMs fail or aren't configured.
   * **Required:** The `tesseract-ocr` host package and `pytesseract` Python dependency.
   * **Setup (macOS):** `brew install tesseract`
   * **Setup (Ubuntu/Docker):** `apt-get install tesseract-ocr` (included in the default Dockerfile)

**API endpoint:** `POST /api/vision/extract` (requires authentication)

| Field   | Type   | Description                                               |
|---------|--------|-----------------------------------------------------------|
| `cover` | `file` | The book cover photo (JPEG, PNG, or WebP, max **10 MB**). |

**Successful response (HTTP 200):**

```json
{
  "success": true,
  "data": {
    "Title": "Dune",
    "Authors": ["Frank Herbert"]
  },
  "error": null
}
```

**Error response when all extraction methods fail (HTTP 503):**

```json
{
  "success": false,
  "data": null,
  "error": "Vision extraction failed. All fallback methods (Gemini, Ollama, Tesseract) were either unconfigured or failed. Please check the server logs."
}
```

> **Note:** The endpoint validates file type and size before contacting the Vision API. Only JPEG, PNG, and WebP uploads ≤ 10 MB are accepted.

## 3. Local AI Generation (Free)

To use your own hardware for generation (Tier 4), iqoqo supports Stable Diffusion via the Automatic1111 WebUI API. This requires a dedicated GPU (Nvidia recommended, Apple Silicon supported) and at least 10GB of disk space.

### Step 1: Install Prerequisites
Before installing the WebUI, you need two tools:

* Python 3.10.6: Note: It must be this specific version or 3.10.x. Newer versions like 3.11 or 3.12 will cause errors. * Download Python 3.10.6 here. Crucial for Windows: Check the box that says "Add Python to PATH" during installation.

* Git: Download and install Git.

### Step 2: Clone the Repository
Open your computer's terminal (or Command Prompt on Windows), navigate to the folder where you want to install it, and run:

```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui
```

### Step 3: Enable the API & Launch
To allow iqoqo to communicate with Stable Diffusion, you must enable its API mode before running it.

#### For Windows

1. Inside the `stable-diffusion-webui` folder, find the file named `webui-user.bat`.
1. Right-click it and select Edit (open it in Notepad).
1. Find the line that says `set COMMANDLINE_ARGS=` and change it to:

    ```batch
    set COMMANDLINE_ARGS=--api
    ```

1. Save the file and double-click `webui-user.bat` to run it. (The first run will take 15-30 minutes as it downloads several gigabytes of models).

#### For Mac / Linux

1. Inside the `stable-diffusion-webui` folder, edit the `webui-user.sh` file.
1. Find the line `export COMMANDLINE_ARGS=""` and change it to:

    ```bash
    export COMMANDLINE_ARGS="--api"
    ```

1. Run the script from your terminal:

    ```bash
    ./webui.sh
    ```

### Step 4: Connect iqoqo
Once the terminal displays Running on local URL: [http://127.0.0.1:7860](http://127.0.0.1:7860), the server is ready.

Add the following to your iqoqo `.env` file:

```bash
LOCAL_SD_URL=http://localhost:7860
```

### Filtering Junk / Placeholder Covers

Some external metadata APIs (like OpenLibrary or Google Books) occasionally return generic "No Image Available" placeholder images instead of an HTTP error. To prevent these from polluting your library, iqoqo uses perceptual hashing (`pHash`) to detect and reject them automatically, allowing the system to fall back to generating a custom LLM cover.

Because different regions and APIs have different placeholder images, you can define a custom blocklist using environment variables.

**How to block a generic cover:**

1. Save the annoying placeholder image to your computer (e.g., `junk_cover.jpg`).
2. Run a quick python script to compute its pHash:

    ```python
    import imagehash
    from PIL import Image
    print(imagehash.phash(Image.open("junk_cover.jpg")))
    ```

3. This will output a hash string like `e1e1e1e1e1e1e1e1`. Add this to your `.env`:

    ```bash
    IQOQO_KNOWN_JUNK_PHASHES="e1e1e1e1e1e1e1e1,ffffffff00000000"
    ```

## 4. Batch Processing

To generate covers for existing items in your database:

```bash
python scripts/fetch_covers.py
# or with limit
python scripts/fetch_covers.py --limit 100
```

This script is **resumable**. You can stop it with `Ctrl+C` and run it again later; it will skip items that already have covers.

## 5. Troubleshooting

* **Missing Covers:** Check `app/static/covers/` permissions. Ensure Docker volumes are mounted correctly.
* **API Errors:** Check application logs for "Cloud LLM Gen failed" messages.

## 6. Importing Covers to a Remote iqoqo Instance

To efficiently transfer and bind generated cover pages from your local machine to a remote Docker instance, follow this automated workflow.

**Package and Transfer (Local Machine):**
Compress your local covers directory and securely copy it to the remote server's `/tmp` directory.

```bash
# Compress the covers directory
tar -czvf covers.tar.gz -C app/static covers

# Securely copy it to the remote server
scp covers.tar.gz user@your-server-ip:/tmp/
```
