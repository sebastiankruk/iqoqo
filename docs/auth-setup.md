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
