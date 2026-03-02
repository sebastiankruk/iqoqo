# Local AI Generation Setup

iqoqo supports generating book covers using a local LLM (Stable Diffusion). This allows for free, private image generation but requires capable hardware.

## Option 1: Docker (Recommended for Linux/Windows with NVIDIA GPU)

If you are using Docker Compose, you can enable the local AI service by using the `local-ai` profile.

### 1. Update `docker-compose.yml`

Add the following service to your `docker-compose.yml` (or `docker-compose.prod.yml`):

```yaml
services:
  # ... other services ...

  stable-diffusion:
    image: runpod/stable-diffusion:web-automatic-1111-v1.5
    profiles: ["local-ai"]
    environment:
      - COMMANDLINE_ARGS=--api --listen
    ports:
      - "7860:3000"
    volumes:
      - sd_models:/workspace/stable-diffusion-webui/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  # ... other volumes ...
  sd_models:
```

### 2. Run with Profile

Start the application with the `local-ai` profile enabled:

```bash
docker compose --profile local-ai up -d
```

### 3. Configure iqoqo

Update your `.env` file to point to the Docker service:

```bash
LOCAL_SD_URL=http://stable-diffusion:3000
```

## Option 2: Manual Installation (Mac/Apple Silicon or Custom Setup)

This method is recommended for macOS users (Apple Silicon) or if you prefer running Stable Diffusion natively on your host machine.

### 1. Prerequisites

- **Python 3.10.6**: It is crucial to use this specific version or 3.10.x. Newer versions (3.11+) may cause compatibility issues.
- **Git**: Ensure git is installed.

### 2. Installation Steps

1. **Clone the repository**:

    ```bash
    git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
    cd stable-diffusion-webui
    ```

1. **Configure Launch Arguments**:

    **For Mac (Apple Silicon):**

    Edit `webui-user.sh`:

    ```bash
    # Enable API and skip CUDA checks for Mac
    export COMMANDLINE_ARGS="--api --skip-torch-cuda-test --no-half --use-cpu all"
    # Fix for missing Stability AI repository
    export STABLE_DIFFUSION_REPO="https://github.com/w-e-w/stablediffusion.git"
    ```

    **For Windows/Linux (NVIDIA):**
    Edit `webui-user.sh` (Linux) or `webui-user.bat` (Windows):

    ```bash
    export COMMANDLINE_ARGS="--api"
    export STABLE_DIFFUSION_REPO="https://github.com/w-e-w/stablediffusion.git"
    ```

1. **Run the Installer**:
    Execute the script:

    ```bash
    ./webui.sh  # Mac/Linux
    # or
    ./webui-user.bat # Windows
    ```

### 3. Troubleshooting Common Installation Errors

If the installation fails, follow these specific fixes for common issues encountered during setup.

#### Error: `Repository not found` (Stability AI)
If you see `fatal: repository 'https://github.com/Stability-AI/stablediffusion.git/' not found`, ensure you have set the `STABLE_DIFFUSION_REPO` environment variable as shown in step 2.

#### Error: `ModuleNotFoundError: No module named 'pkg_resources'`
This occurs because newer versions of `setuptools` (v70+) have removed `pkg_resources`, which is required by the CLIP library.

**Fix:**

1. Stop the installation script (Ctrl+C).
1. Activate the virtual environment created by the script:

    ```bash
    source venv/bin/activate
    ```

1. Downgrade `setuptools` and install `wheel`:

    ```bash
    pip install "setuptools<70.0.0" wheel
    ```

1. Manually install CLIP without build isolation:

    ```bash
    pip install https://github.com/openai/CLIP/archive/d50d76daa670286dd6cacf3bcd80b5e4823fc8e1.zip --no-build-isolation
    ```

1. Deactivate the virtual environment:

    ```bash
    deactivate
    ```

1. Run `./webui.sh` again.

### 4. Connect to iqoqo

Once Stable Diffusion is running (you should see `Running on local URL: http://127.0.0.1:7860`), update your iqoqo `.env` file:

```bash
LOCAL_SD_URL=http://127.0.0.1:7860
```
