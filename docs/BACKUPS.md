# iQoQo Backups & Cloud Storage Guide

iQoQo stores data in a PostgreSQL database and local filesystem volumes (`app/static/covers/`, `app/static/gallery/`, `exports/`).

Starting in **v0.7.14**, iQoQo supports a multi-tier `rclone` cloud topology to handle daily backups, long-term Glacier cold archives, and a shared cross-instance AI covers cache.

---

## Architecture & Remotes

Three separate `rclone` remotes are configured via environment variables in `.env`:

| Environment Variable | Default Remote Name | Purpose | Recommended Storage Class |
| -------------------- | ------------------- | ------- | ------------------------- |
| `RCLONE_REMOTE_FAST` | `iqoqo-backup` | Daily database dumps & asset backups | AWS S3 Standard / S3 Standard-IA / Dropbox |
| `RCLONE_REMOTE_ARCHIVE` | `iqoqo-glacier` | Long-term cold storage archive | AWS S3 Glacier Flexible Retrieval / Deep Archive |
| `RCLONE_COVERS_REMOTE` | `iqoqo-s3-cache` | Shared AI cover cache across instances | AWS S3 Standard / Backblaze B2 / Cloudflare R2 |

---

## 1. Fast Daily Backups (`RCLONE_REMOTE_FAST`)

The backup script (`scripts/cloud_backup.sh`) dumps PostgreSQL (`pg_dumpall`), compresses uploaded asset volumes, and syncs them to your primary cloud remote.

### Setup Instructions

1. Install [rclone](https://rclone.org/install/) on your host machine.
2. Run `rclone config` to set up your primary remote named **`iqoqo-backup`**.
3. Test manually:

   ```bash
   ./scripts/cloud_backup.sh iqoqo-backup
   ```

4. Schedule nightly execution via cron (e.g. 03:00 AM):

   ```bash
   0 3 * * * /path/to/iqoqo/scripts/cloud_backup.sh iqoqo-backup >> /var/log/iqoqo_backup.log 2>&1
   ```

---

## 2. Long-Term Archiving & AWS S3 Glacier (`RCLONE_REMOTE_ARCHIVE`)

For long-term retention and compliance, iQoQo supports pushing cold backups directly to **AWS S3 Glacier**.

### AWS S3 Glacier Setup via Rclone

1. **AWS IAM User Setup**:
   - Create an IAM User in AWS Console with S3 permissions (`s3:PutObject`, `s3:GetObject`, `s3:ListBucket`).
   - Generate an **Access Key ID** and **Secret Access Key**.

2. **Configure Rclone**:
   Run `rclone config` and create a new remote named **`iqoqo-glacier`**:

   ```bash
   rclone config
   # n) New remote -> name: iqoqo-glacier
   # Storage: Amazon S3 Compliant Storage Provider
   # Provider: Amazon Web Services S3
   # env_auth: false
   # access_key_id: <YOUR_AWS_ACCESS_KEY_ID>
   # secret_access_key: <YOUR_AWS_SECRET_ACCESS_KEY>
   # region: us-east-1 (or your preferred region)
   # storage_class: GLACIER (or DEEP_ARCHIVE)
   ```

3. **Run Long-Term Archive Backup**:
   Pass the archive remote explicitly to the backup script:

   ```bash
   ./scripts/cloud_backup.sh iqoqo-glacier
   ```

4. **Schedule Monthly Glacier Sync via Cron**:

   ```bash
   0 4 1 * * /path/to/iqoqo/scripts/cloud_backup.sh iqoqo-glacier >> /var/log/iqoqo_glacier.log 2>&1
   ```

---

## 3. Shared AI Cover Cache (`RCLONE_COVERS_REMOTE`)

Introduced in **v0.7.14**, AI cover generation scripts (`generate_ai_covers.py` and `fetch_llm_cover`) can share generated covers globally across multiple iQoQo instances to eliminate redundant LLM API costs and execution time.

### How it Works

1. When generating an AI cover, iQoQo first checks `RCLONE_COVERS_REMOTE` (e.g., `iqoqo-s3-cache`).
2. If the cover already exists in the S3 cache, it pulls the file directly via `rclone` (**Cache Hit**).
3. If not found locally or in S3, iQoQo generates the image using the configured LLM provider, saves it to the local mounted Docker volume (`app/static/covers/`), and asynchronously pushes a copy to `RCLONE_COVERS_REMOTE`.
4. If `RCLONE_COVERS_REMOTE` is not set or unconfigured, iQoQo outputs a soft warning and falls back seamlessly to local volume storage.

### Cover Cache Setup Instructions

1. Configure an S3 remote named **`iqoqo-s3-cache`** in `rclone config`.
2. Add the variable to your `.env` file:

   ```bash
   RCLONE_COVERS_REMOTE=iqoqo-s3-cache
   ```

3. Test cover lookup or batch processing:

   ```bash
   python scripts/generate_ai_covers.py --limit 5
   ```

---

## 4. Dropbox Setup (Alternative Daily Remote)

If using Dropbox for `RCLONE_REMOTE_FAST`:

1. **Create App**: Go to [Dropbox App Console](https://www.dropbox.com/developers/apps).
   - Choose **Scoped access** -> **App folder** or **Full Dropbox**.
2. **Enable Permissions**:
   - Enable `files.metadata.write`, `files.metadata.read`, `files.content.write`, `files.content.read`.
3. **Configure OAuth**:
   - Add Redirect URI: `http://localhost:53682/`.
   - Copy `client_id` and `client_secret`.
4. **Configure Rclone**:

   ```bash
   rclone config
   # Name: iqoqo-backup -> Storage: dropbox -> Enter client_id & client_secret
   ```

---

## Supported Storage Providers

Via `rclone`, iQoQo supports:

- **AWS S3** (Standard, Standard-IA, Glacier, Deep Archive)
- **Backblaze B2**
- **Cloudflare R2**
- **Dropbox**
- **Google Drive / Google Cloud Storage**
- **WebDAV** (Nextcloud, ownCloud, etc.)
