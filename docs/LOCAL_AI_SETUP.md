# Local AI Setup Guide

iqoqo supports generating book covers using a local installation of Stable Diffusion (via Automatic1111 WebUI). This allows for free, private image generation without relying on external cloud APIs.

## Option A: Docker (Recommended for Linux/Windows)

If you are running iqoqo via Docker on a machine with an NVIDIA GPU, this is the easiest method.

### 1. Start the Service

We provide a separate compose file `docker-compose.local-ai.yml` to run Stable Diffusion. Run it alongside your main application:

```bash
docker compose -f docker-compose.yml -f docker-compose.local-ai.yml up -d
```

This will start the `stable-diffusion` service on port `7860`.

### 2. Configure iqoqo

Update your `.env` file to point to the Docker service:

```bash
LOCAL_SD_URL=http://stable-diffusion:3000
```

> **Note:** Docker GPU passthrough requires the NVIDIA Container Toolkit on the host machine. Docker on macOS does not currently support GPU acceleration for this image.

---

## Option B: Manual Installation (Recommended for macOS/Apple Silicon)

For macOS users (M1/M2/M3) or those who prefer running the service natively.

### Prerequisites

- **Python 3.10**: The WebUI requires Python 3.10 specifically.
  - macOS: `brew install python@3.10`
- **Git**: `brew install git`

### Installation Steps

1. **Clone the Repository**
   Navigate to a directory outside of the iqoqo project (e.g., `~/Development`) and clone the WebUI:

   ```bash
   git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
   cd stable-diffusion-webui
   ```

2. **Initial Setup (and Fixes)**
   Recent updates to Python packages have introduced compatibility issues with the WebUI installer. Follow these steps carefully to patch the environment before launching.

   First, attempt to run the script to create the virtual environment (it may fail, which is expected):

   ```bash
   ./webui.sh
   ```

   Now, activate the environment and apply the necessary fixes:

   ```bash
   # 1. Activate the venv created by the script
   source venv/bin/activate

   # 2. Downgrade setuptools (fixes 'pkg_resources' error)
   pip install "setuptools<70.0.0"

   # 3. Install wheel (fixes 'bdist_wheel' error)
   pip install wheel

   # 4. Manually install CLIP without build isolation
   pip install https://github.com/openai/CLIP/archive/d50d76daa670286dd6cacf3bcd80b5e4823fc8e1.zip --no-build-isolation

   # 5. Deactivate to return to your shell
   deactivate
   ```

3. **Configure Environment Variables**
   The original Stability AI repository is currently unavailable, so we must point to a mirror. We also need to enable the API and optimize for Mac.

   Create a `webui-user.sh` file (or edit the existing one) in the `stable-diffusion-webui` directory:

   ```bash
   # webui-user.sh

   # Fix for missing repository
   export STABLE_DIFFUSION_REPO="https://github.com/w-e-w/stablediffusion.git"

   # Arguments: Enable API, skip CUDA check (for Mac), listen on local network
   export COMMANDLINE_ARGS="--api --skip-torch-cuda-test --no-half --use-cpu interrorgate"
   ```

4. **Launch**
   Run the script again. It should now complete the installation and start the server.

   ```bash
   ./webui.sh
   ```

### 3. Configure iqoqo

Once Stable Diffusion is running (usually at `http://127.0.0.1:7860`), update your iqoqo `.env` file:

```bash
# If running iqoqo locally (flask run)
LOCAL_SD_URL=http://127.0.0.1:7860

# If running iqoqo in Docker (connecting to host)
LOCAL_SD_URL=http://host.docker.internal:7860
```
