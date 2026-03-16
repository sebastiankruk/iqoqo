# Authentication Setup

## Initializing the Admin Account

Before you can log into your iqoqo instance using email and password, you must create the initial administrator account.

1. Ensure your root `.env` file contains the following variables:

    ```env
    ADMIN_EMAIL=admin@iqoqo.local
    ADMIN_PASSWORD=your_secure_password
    ```

2. Run the initialization script:

    Local environment (venv):

    ```bash
    PYTHONPATH=. .venv/bin/python scripts/init_auth.py
    ```

    Docker environment:

    ```bash
    docker compose exec web python scripts/init_auth.py
    ```

    This script reads your environment variables, creates the user, and securely hashes the password.

## Google OAuth Setup (Local Development)

To enable "Sign in with Google", you must supply your own Google Cloud credentials.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., \`iqoqo-dev\`).
3. Navigate to **APIs & Services > OAuth consent screen**.
   - Choose **External** and fill in the required App Name and Support Email fields.
4. Navigate to **Credentials > + CREATE CREDENTIALS > OAuth client ID**.
   - **Application type:** Web application
   - **Authorized JavaScript origins:** `http://localhost:3000`
   - **Authorized redirect URIs:** `http://localhost:3000/api/auth/callback/google` *(Note: Update this if using a different callback route)*
5. Copy the generated keys and add them to your `frontend/.env.local` file:

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```
