# iQoQo Backups & Cloud Storage Guide

iQoQo stores data in a PostgreSQL database and local filesystem volumes (`app/static/covers/`, `app/static/gallery/`, `exports/`).

Starting in **v0.7.14** and extended in **v0.7.16**, iQoQo supports a multi-tier `rclone` cloud topology to handle daily backups, long-term Glacier cold archives, a shared cross-instance AI covers cache, and remote persistence for feedback ticket screenshots.

---

## Two Storage Backends

Since **v0.8.2** iqoqo has two remote-storage backends, and which one is in use
is a single variable:

| Variable | Values | Meaning |
| -------- | ------ | ------- |
| `S3_BACKEND` | `auto` (default), `rclone`, `s3` | Which backend the **containers** use. `auto` prefers rclone when a remote is already configured, so existing installs change nothing. |

**This changed for the containers only.** `app/core/s3_service.py` (boto3) lets
the app reach object storage directly, and the containers **no longer shell out
to rclone or mount `rclone.conf`** — handing a plaintext credential file to the
process that parses untrusted input was the risk. Host-side backup and restore
scripts on your machine still use your existing rclone install, unchanged.

One name is **deprecated** in favour of the `S3_BUCKET_*` variables, and iqoqo
warns by name when set without a replacement:

- `RCLONE_REMOTE_ARCHIVE` → `S3_BUCKET_BACKUP`

Leaving every S3 value blank runs fully local; each role degrades to a no-op
rather than failing. Full variable reference: `.env.example`, and
`docs/INSTALL.md`.

### Remote storage roles

| Role | rclone variable (host scripts) | Native variable (containers) | Recommended storage class |
| ---- | ------------------------------ | ---------------------------- | ------------------------- |
| Daily database dumps & asset backups | `RCLONE_REMOTE_FAST` | `S3_BUCKET_BACKUP` | AWS S3 Standard / Standard-IA / Dropbox |
| Long-term cold storage archive | `RCLONE_REMOTE_ARCHIVE` | `S3_BUCKET_BACKUP` | AWS S3 Glacier Flexible Retrieval / Deep Archive |
| Shared AI cover cache across instances | `RCLONE_COVERS_REMOTE` | `S3_BUCKET_COVERS` | AWS S3 Standard / Backblaze B2 / Cloudflare R2 |

The native backend works against AWS S3, MinIO, Cloudflare R2, Wasabi, Backblaze
B2 and Oracle Cloud Object Storage. Server-side encryption is available via
`S3_SSE` (with `S3_SSE_KMS_KEY_ID` for KMS).

---

## 1. Fast Daily Backups (`RCLONE_REMOTE_FAST`)

The backup script ([`scripts/cloud_backup.sh`](../scripts/cloud_backup.sh)) dumps PostgreSQL (`pg_dumpall`), compresses uploaded asset volumes, and syncs them to your primary cloud remote.

### Resilience, Locking & Retries

Starting in **v0.8.3**, `cloud_backup.sh` includes robust execution safeguards:

- **Kernel-level flock Execution Locking**: Backups acquire an exclusive file lock (`BACKUP_LOCK_FILE`, default `/tmp/iqoqo_backup.lock`) with a bounded wait timeout (`BACKUP_LOCK_TIMEOUT`, default `1800` seconds). The lock timeout is a wait ceiling before exiting with code 2, **not** a stale-lock age. Locks are released automatically by the Linux kernel when the holding process exits or crashes (including `SIGKILL`); the lock file must never be unlinked manually.
- **Database Pre-flight & Retries**: Before executing a multi-gigabyte dump, the script tests database connectivity (`SELECT 1`) and verifies the PostgreSQL user role against `pg_roles` using `${POSTGRES_USER:-iqoqo}`.
  - **Transient errors** (e.g. database container starting up) retry up to `BACKUP_RETRY_ATTEMPTS` times (default `3`) using exponential backoff (`BACKUP_RETRY_DELAY_BASE`, default `5`s: 5s, 10s, 20s).
  - **Permanent errors** (e.g. role missing, authentication failure) fail immediately without retry.
  - **Empty dump protection**: Dumps that produce 0 bytes fail immediately outside the retry loop to prevent corrupting backups.

### Setup Instructions

1. Install [rclone](https://rclone.org/install/) on your host machine.
2. Run `rclone config` to set up your primary remote named **`iqoqo-backup`** (or your preferred S3 / cloud provider).
3. Configure your `.env`:

   ```bash
   RCLONE_REMOTE_FAST=iqoqo-backup
   # Optional: explicitly set path if rclone is configured under a non-root user
   RCLONE_CONFIG=/home/username/.config/rclone/rclone.conf

   # Optional: Execution lock and retry tuning
   # BACKUP_LOCK_FILE=/tmp/iqoqo_backup.lock
   # BACKUP_LOCK_TIMEOUT=1800
   # BACKUP_RETRY_ATTEMPTS=3
   # BACKUP_RETRY_DELAY_BASE=5
   ```

4. Test immediately:

   ```bash
   make backup-run
   # Or with an explicit remote: make backup-run remote=iqoqo-backup
   ```

5. Install daily 03:00 AM cron job:

   ```bash
   make backup-install
   # Or with an explicit remote: make backup-install remote=iqoqo-backup
   ```

   *(Installs to `/etc/cron.d/iqoqo-backup` logging to `/var/log/iqoqo_backup.log`)*

6. Verify backup health:

   ```bash
   make backup-check
   ```

7. To remove the daily cron job:

   ```bash
   make backup-uninstall
   ```

---

## 2. Long-Term Archiving & AWS S3 Glacier (`RCLONE_REMOTE_ARCHIVE`)

For long-term retention and compliance, iQoQo supports pushing cold backups directly to **AWS S3 Glacier** on a monthly schedule.

### AWS S3 Glacier Setup via Rclone

1. **AWS IAM User Setup**:
   - Create an IAM User in AWS Console with S3 permissions (`s3:PutObject`, `s3:GetObject`, `s3:ListBucket`).
   - Generate an **Access Key ID** and **Secret Access Key**.

2. **Configure Rclone Profile**:
   Run `rclone config` and create a new remote named **`iqoqo-glacier`**:

   ```bash
   rclone config
   # n) New remote -> name: iqoqo-glacier
   # Storage: Amazon S3 Compliant Storage Provider
   # Provider: Amazon Web Services S3
   # env_auth: false
   # access_key_id: <YOUR_AWS_ACCESS_KEY_ID>
   # secret_access_key: <YOUR_AWS_SECRET_ACCESS_KEY>
   # region: eu-north-1 (or your preferred AWS region)
   # storage_class: GLACIER_IR (or GLACIER / DEEP_ARCHIVE)
   ```

   > [!TIP]
   > - `GLACIER_IR` (Glacier Instant Retrieval): Fast millisecond retrieval at low cold storage cost (~$0.004/GB/mo).
   > - `GLACIER` (Flexible Retrieval): Cheaper (~$0.0036/GB/mo), but restore takes 3–5 hours before downloading.
   > - `DEEP_ARCHIVE`: Lowest cost (~$0.00099/GB/mo), restore takes 12–48 hours.

3. **Configure `.env`**:

   For S3-based remotes, specify the target using the `<remote_name>:<bucket_name>` syntax:

   - **Production**:

     ```bash
     RCLONE_REMOTE_FAST=iqoqo-s3:iqoqo-backup
     RCLONE_REMOTE_ARCHIVE=iqoqo-glacier:iqoqo-archive
     ```

   - **Preview / Staging**:

     ```bash
     RCLONE_REMOTE_FAST=iqoqo-s3:iqoqo-backup-preview
     RCLONE_REMOTE_ARCHIVE=iqoqo-glacier:iqoqo-archive-preview
     ```

   > [!NOTE]
   > If `RCLONE_REMOTE_ARCHIVE` is unset in `.env`, `archive-run` and `archive-install` default to `iqoqo-glacier:iqoqo-archive`. You can also override the destination at runtime with `remote=...`.

4. **Run Long-Term Archive Immediately**:

   ```bash
   make archive-run
   # Or with explicit remote/bucket: make archive-run remote=iqoqo-glacier:iqoqo-archive
   ```

5. **Install Monthly Cold Archive Cron Job (1st of month at 04:00 AM)**:

   ```bash
   make archive-install
   # Or with explicit remote/bucket: make archive-install remote=iqoqo-glacier:iqoqo-archive
   ```

   *(Installs to `/etc/cron.d/iqoqo-archive` logging to `/var/log/iqoqo_archive.log` without affecting the daily backup)*

6. **Verify Archive Health**:

   ```bash
   make archive-check
   # Or with explicit remote/bucket: make archive-check remote=iqoqo-glacier:iqoqo-archive
   ```

   *(Verifies `/etc/cron.d/iqoqo-archive`, remote reachability, and monthly freshness within 35 days)*

7. **To remove the monthly archive cron job**:

   ```bash
   make archive-uninstall
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

## 4. Feedback Screenshot Storage

Feedback ticket screenshots are stored locally on the host bind mount at `./app/static/gallery/`. No remote object-storage bucket or rclone remote needs to be provisioned for feedback screenshots.

### How Feedback Screenshot Durability Works

1. When a user submits a bug report or feedback ticket with screenshot attachments, the file is saved directly to local storage at `./app/static/gallery/`.
2. The directory is mounted into the `web` and `worker` containers, surviving container restarts and recreations.
3. Off-site disaster-recovery durability is provided by the nightly host backup (`scripts/cloud_backup.sh`), whose asset archive includes `app/static/gallery/`. No runtime cloud upload task or bucket credentials are required.

---

## 5. Pre-Start Container Configuration Check

Starting in **v0.7.16**, the container entrypoint (`deploy/docker-entrypoint.sh`) performs an automated pre-flight check:

```bash
mkdir -p "${HOME}/.config/rclone"
```

This ensures the user configuration directory always exists prior to process execution, preventing silent rclone job failures on fresh container deployments where host bind mounts are not present.

---

## 6. Dropbox Setup (Alternative Daily Remote)

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
