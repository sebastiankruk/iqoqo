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

### Supported Providers (via rclone)

- AWS S3 / Backblaze B2 (recommended for headless servers)
- Dropbox (OAuth headless flow required)
- Google Drive / OneDrive
- Any WebDAV endpoint (Nextcloud, etc.)

> **Need help?** Ask the AI assistant in your IDE: "Help me set up AWS S3 backups for my iQoQo instance."
