# Installation Guide

This document provides comprehensive instructions for setting up iqoqo for development and production use.

## Prerequisites

### Required Software

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** and **npm** - [Download](https://nodejs.org/)
- **PostgreSQL 15+** - Can be run via Docker (recommended) or installed locally
- **Docker & Docker Compose** - For containerized deployment
- **Git** - For version control

## Docker Installation

Docker is required to run the PostgreSQL database in a container.

- **macOS**: You can install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/), but be aware of its licensing terms. For a free and open-source alternative, we recommend [Colima](https://github.com/abiosoft/colima). You can install it using [Homebrew](https://brew.sh/):

    ```bash
    brew install colima docker docker-compose
    colima start
    ```

- **Ubuntu**: Follow the instructions to install [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) and the [Docker Compose plugin](https://docs.docker.com/compose/install/linux/).

After installation, make sure the Docker daemon is running.

## Setup

1. **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/iqoqo.git
    cd iqoqo
    ```

2. **Create and activate a virtual environment:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

    This installs both runtime dependencies and development tools (black, ruff, isort, mypy, pytest).

4. **Install JavaScript/CSS quality tools:**

    ```bash
    npm install
    ```

    This installs ESLint, Prettier, stylelint, and markdownlint for code quality checks.

5. **Set up environment variables:**

    Create a `.env` file by copying the example file:

    ```bash
    cp .env.example .env
    ```

    You can edit the `.env` file to match your local configuration, for example, your database credentials.

    > **Note for VS Code users:** To have the environment variables from the `.env` file automatically loaded in the integrated terminal, you need to enable the `python.terminal.useEnvFile` setting. You can do this by opening your VS Code settings (JSON) and adding `"python.terminal.useEnvFile": true`.

## Database Setup

This project uses PostgreSQL as its database. The easiest way to get a PostgreSQL database running is by using Docker Compose.

1. **Start the database service:**

    ```bash
    docker-compose up -d db
    ```

   This is necessary for the `flask db` commands, which run on the host, to connect to the database. The default credentials are set in the `docker-compose.yml` file and should match the ones in your `.env` file.

2. **Initialize the database:**

    Once the application is set up, you can initialize the database schema using Flask-Migrate:

    ```bash
    flask db init
    flask db migrate -m "Initial migration."
    flask db upgrade
    ```

### Troubleshooting

- **`FATAL: role "user" does not exist`**: This error usually means your application is connecting to a different PostgreSQL instance than the one running in Docker.
  - Make sure you have started the Docker container with `docker-compose up -d db`.
  - Check if you have another PostgreSQL server running on your machine on port `5432`. If so, stop it and try again. Here are some common ways to do that:
    - **To check what's using the port:** `sudo lsof -i :5432`
    - **On macOS with Homebrew:** `brew services stop postgresql`
    - **On Ubuntu/Debian with systemd:** `sudo systemctl stop postgresql`
  - Verify that your `.env` file contains the correct `DATABASE_URL` that points to the Dockerized database (`postgresql://user:password@localhost:5432/iqoqo`).

## Running the Application

### Development Mode

To run the Flask development server:

```bash
./run_dev.sh
```

Or manually:

```bash
flask run
```

The application will be available at `http://localhost:5000`.

### Production Mode with Docker

To run the full stack (app + database) in production mode:

```bash
docker-compose up
```

This starts both the PostgreSQL database and the Flask application behind Nginx.

## Code Quality Checks

Before committing code, ensure quality standards are met:

```bash
# Run all linters
make lint

# Auto-format code
make format

# Run tests
make test
```

### Individual Quality Checks

```bash
# Python
make lint-python    # Ruff + mypy
make format-python  # Black + isort

# JavaScript/CSS
make lint-js        # ESLint
make lint-css       # stylelint

# Markdown
make lint-markdown  # markdownlint
```

## Next Steps

- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
- Read the [API documentation](../README.md#api-documentation) for API usage
- Check [docs/ontology/iqoqo.ttl](ontology/iqoqo.ttl) for the FRBR ontology structure

The application will be available at `http://127.0.0.1:5000`.

## Running Tests

To run the tests, use `pytest`:

```bash
pytest
```

This will discover and run all the tests in the `tests/` directory. The tests are configured to run with an in-memory SQLite database, so you don't need to have PostgreSQL running for the tests.
