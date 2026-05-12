# iQoQo Backups

iQoQo stores data in a PostgreSQL database and local file system volumes.
We recommend using the provided backup script combined with `rclone` for off-site cloud backups.

## Automated Cloud Sync

The backup script (`scripts/cloud_backup.sh`) dumps the database and asset directories,
compresses them, and syncs to any provider supported by `rclone`.

### Quick Setup

1. Install [rclone](https://rclone.org/install/) on your host machine.
2. Run `rclone config` to set up your provider. Name the remote **`iqoqo-backup`**.
3. Test manually: `./scripts/cloud_backup.sh iqoqo-backup`
4. Schedule nightly via cron:

   ```bash
   0 3 * * * /path/to/iqoqo/scripts/cloud_backup.sh iqoqo-backup >> /var/log/iqoqo_backup.log 2>&1
   ```

### Dropbox Setup (Recommended)

Using your own Dropbox App prevents rate-limiting issues.

1. **Create App**: Go to [Dropbox App Console](https://www.dropbox.com/developers/apps).
    - Click **Create app**.
    - Choose **Scoped access**.
    - Choose **App folder** (Sandbox) or **Full Dropbox**.
    - Name it (e.g., `iqoqo-backup-yourname`).
2. **Set Permissions (CRITICAL)**:
    - Go to **Permissions** tab.
    - Enable: `files.metadata.write`, `files.metadata.read`, `files.content.write`, `files.content.read`.
    - Click **Submit**.
3. **Configure OAuth**:
    - Go to **Settings** tab.
    - Add Redirect URI: `http://localhost:53682/` (must include trailing slash).
    - Copy **App key** (`client_id`) and **App secret** (`client_secret`).
4. **Run Rclone**:

```bash
rclone config
# Choose 'n' for new remote -> Name: 'iqoqo-backup' -> Storage: 'dropbox'
# Enter your client_id and client_secret
```

> [!IMPORTANT]
> **Sandbox App Restriction**: If you use "App folder" access, you cannot sync to the root (`:/`). The iQoQo backup script automatically handles this by syncing to `iqoqo_backups/` within your app folder.

### Supported Providers (via rclone)

- AWS S3 / Backblaze B2 (recommended for headless servers)
- Dropbox (OAuth flow with custom App Keys recommended)
- Google Drive / OneDrive
- Any WebDAV endpoint (Nextcloud, etc.)

> **Need help?** Ask the AI assistant in your IDE: "Help me set up AWS S3 backups for my iQoQo instance."
