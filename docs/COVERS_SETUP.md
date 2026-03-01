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

1. Get key from [Google AI Studio](https://aistudio.google.com/api-keys).
2. Add to `.env`:

   ```bash
   GEMINI_API_KEY=AIza...
   ```

*Note: Telemetry for estimated costs is tracked in the `llm_telemetry` database table.*

## 3. Local AI Generation (Free)

To use your own hardware for generation (Tier 4), iqoqo supports Stable Diffusion via the Automatic1111 WebUI API. This requires a dedicated GPU (Nvidia recommended, Apple Silicon supported) and at least 10GB of disk space.

### Step 1: Install Prerequisites
Before installing the WebUI, you need two tools:

- Python 3.10.6: Note: It must be this specific version or 3.10.x. Newer versions like 3.11 or 3.12 will cause errors. * Download Python 3.10.6 here. Crucial for Windows: Check the box that says "Add Python to PATH" during installation.

- Git: Download and install Git.

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

## 4. Batch Processing

To generate covers for existing items in your database:

```bash
python scripts/fetch_covers.py
# or with limit
python scripts/fetch_covers.py --limit 100
```

This script is **resumable**. You can stop it with `Ctrl+C` and run it again later; it will skip items that already have covers.

## 5. Troubleshooting

- **Missing Covers:** Check `app/static/covers/` permissions. Ensure Docker volumes are mounted correctly.
- **API Errors:** Check application logs for "Cloud LLM Gen failed" messages.
